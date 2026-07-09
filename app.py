import os
import re
import uuid
import cv2
import pickle
import requests
import numpy as np
from datetime import datetime, timedelta
from PIL import Image
from flask import Flask, render_template, request, jsonify, redirect, flash, session, url_for
import pytesseract
from dotenv import load_dotenv
import easyocr
import reportlab.platypus
from models import db, User, ScanHistory, Feedback, UserPreference
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)
from flask_bcrypt import Bcrypt
from auth_utils import (
    sanitize_text,
    validate_email,
    validate_password,
    get_password_strength,
    build_google_oauth_url,
    send_email,
)



# ---------------------------
# INIT
# ---------------------------
load_dotenv()

app = Flask(__name__)

app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "nutriscan_secret"),
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///nutriscan.db"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_DURATION=timedelta(days=30),
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)

db.init_app(app)

bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "error"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.before_request
def refresh_user_session():
    if current_user.is_authenticated:
        user = User.query.get(current_user.id)
        if user:
            if not user.session_token:
                user.session_token = str(uuid.uuid4())
            if not user.session_token_expiry or user.session_token_expiry <= datetime.utcnow():
                user.session_token_expiry = datetime.utcnow() + timedelta(days=7)
                user.session_token = str(uuid.uuid4())
            session["session_token"] = user.session_token
            user.last_login = user.last_login or datetime.utcnow()
            db.session.add(user)
            db.session.commit()

reader = None
try:
    reader = easyocr.Reader(['en'])
except Exception as exc:
    print("Warning: could not initialize EasyOCR:", exc)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------------------
# CONFIG (ENV SAFE)
# ---------------------------
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")

APP_ID = os.getenv("EDAMAM_APP_ID")
APP_KEY = os.getenv("EDAMAM_APP_KEY")

# ---------------------------
# LOAD MODEL
# ---------------------------
model = None
vectorizer = None
try:
    model = pickle.load(open("model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
except Exception as e:
    print("Warning: could not load model or vectorizer:", e)

# ---------------------------
# SAVE FILE SAFELY
# ---------------------------
def save_file(file):
    filename = f"{uuid.uuid4().hex}.png"
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)
    return path

# ---------------------------
# IMAGE PREPROCESSING
# ---------------------------
def preprocess_image(path):
    img = cv2.imread(path)

    if img is None:
        return None

    # Optional crop (disabled for now)
    # h, w = img.shape[:2]
    # img = img[
    #     int(h * 0.15):int(h * 0.85),
    #     int(w * 0.10):int(w * 0.90)
    # ]

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Enlarge image
    gray = cv2.resize(
        gray,
        None,
        fx=3,
        fy=3,
        interpolation=cv2.INTER_CUBIC
    )

    # Remove noise
    gray = cv2.bilateralFilter(
        gray,
        11,
        17,
        17
    )

    # Improve contrast
    clahe = cv2.createCLAHE(
        clipLimit=3.0,
        tileGridSize=(8, 8)
    )

    gray = clahe.apply(gray)

    # Sharpen
    kernel = np.array([
        [-1, -1, -1],
        [-1,  9, -1],
        [-1, -1, -1]
    ])

    gray = cv2.filter2D(
        gray,
        -1,
        kernel
    )

    # Threshold
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        2
    )

    # Morphological cleanup
    kernel = np.ones((2, 2), np.uint8)

    thresh = cv2.morphologyEx(
        thresh,
        cv2.MORPH_CLOSE,
        kernel
    )

    # Final denoise and save a uniquely-named processed image
    thresh = cv2.medianBlur(thresh, 3)

    processed_path = os.path.join(
        UPLOAD_FOLDER,
        f"processed_{uuid.uuid4().hex}.png"
    )

    try:
        cv2.imwrite(processed_path, thresh)
        return processed_path
    except Exception as e:
        print("Could not write processed image:", e)
        return None
# ---------------------------
# OCR EXTRACTION
# ---------------------------
def extract_text(path):
    processed = preprocess_image(path)

    if not processed:
        return ""

    # First try Tesseract
    config = r'''
        --oem 3
        --psm 6
        -c preserve_interword_spaces=1
    '''

    # Try a couple of tesseract modes and also try original image
    candidates = []

    try:
        t1 = pytesseract.image_to_string(
            Image.open(processed),
            config=config
        )
        candidates.append(t1)
    except Exception as e:
        print("Tesseract on processed failed:", e)

    # Also try a more general page segmentation on original
    try:
        config2 = r"--oem 3 --psm 3"
        t2 = pytesseract.image_to_string(
            Image.open(path),
            config=config2
        )
        candidates.append(t2)
    except Exception:
        pass

    text = "\n".join([c for c in candidates if c]).lower()

    # Use EasyOCR if Tesseract result is poor
    keywords = [
        "nutrition",
        "ingredients",
        "energy",
        "fat",
        "sugar",
        "calories"
    ]

    # If tesseract output is poor, try EasyOCR which sometimes performs better
    tokens = text.split()
    if (
        len(tokens) < 40 or
        not any(word in text for word in keywords)
    ):
        try:
            result = reader.readtext(
                processed,
                paragraph=True
            )

            easy_text = " ".join([item[1] for item in result]).lower()

            # prefer longer, more keyword-rich text
            if len(easy_text) > len(text) or any(k in easy_text for k in keywords):
                text = easy_text
        except Exception as e:
            print("EasyOCR failed:", e)

    text = re.sub(
        r'[^a-zA-Z0-9.%\s]',
        ' ',
        text
    )

    text = re.sub(
        r'\s+',
        ' ',
        text
    ).strip()

    return text

def extract_nutrition_facts(text):
    facts = {}

    calories = re.search(r'calories?\s*(\d+)', text)
    sugar = re.search(r'sugar\s*(\d+)', text)
    sodium = re.search(r'sodium\s*(\d+)', text)
    fat = re.search(r'fat\s*(\d+)', text)
    fiber = re.search(r'fiber\s*(\d+)', text)

    facts["calories"] = int(calories.group(1)) if calories else None
    facts["sugar_g"] = int(sugar.group(1)) if sugar else None
    facts["sodium_mg"] = int(sodium.group(1)) if sodium else None
    facts["fat_g"] = int(fat.group(1)) if fat else None
    facts["fiber_g"] = int(fiber.group(1)) if fiber else None

    return facts

# ---------------------------
# FOOD DETECTION (IMPROVED)
# ---------------------------
def extract_food(text):
    text = text.lower()

    categories = {
        "Cookies": ["cookie", "cookies", "biscuit", "biscuits"],
        "Chips": ["chips", "crisps"],
        "Chocolate": ["chocolate", "cocoa"],
        "Noodles": ["noodles", "instant noodles"],
        "Cereal": ["cereal", "corn flakes"],
        "Pizza": ["pizza"],
        "Burger": ["burger"],
        "Juice": ["juice"],
        "Milk": ["milk"],
        "Yogurt": ["yogurt", "curd"],
        "Snack": ["snack", "namkeen"],
        "Cake": ["cake"],
        "Bread": ["bread"]
    }

    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in text:
                return category

    if any(word in text for word in [
        "nutrition",
        "ingredients",
        "serving size",
        "energy",
        "calories",
        "fat",
        "sugar",
        "sodium"
    ]):
        return "Packaged Food"

    return "Unknown Food"

    
# ---------------------------
# NUTRITION API
# ---------------------------
def nutrition_api(food):
    url = "https://api.edamam.com/api/nutrition-data"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "ingr": food
    }

    try:
        r = requests.get(url, params=params, timeout=5)
        return r.json()
    except:
        return {}

# ---------------------------
# ML PREDICTION
# ---------------------------
def predict_health(text):
    try:
        if model is None or vectorizer is None:
            return "Unknown", 0.0

        vec = vectorizer.transform([text])

        pred = model.predict(vec)[0]
        # Some models may not implement predict_proba
        prob = None
        try:
            prob = model.predict_proba(vec)[0]
        except Exception:
            prob = None

        confidence = (
            round(float(np.max(prob)) * 100, 2)
            if prob is not None else 0.0
        )

        label = "Healthy ⭐⭐⭐⭐⭐" if pred == 1 else "Unhealthy ❌"

        return label, confidence
    except Exception as e:
        print("Prediction error:", e)
        return "Unknown", 0.0

# ---------------------------
# EXPLAINABLE AI
# ---------------------------
def explain_health(text, nutrition):
    score = 0
    reasons = []

    bad_words = ["sugar","fried","oil","cola","syrup","fat","preservatives","junk"]
    good_words = ["protein","fiber","natural","vitamin","fresh","organic","whole grain"]

    for w in bad_words:
        if w in text:
            score -= 2
            reasons.append(f"Contains {w}")

    for w in good_words:
        if w in text:
            score += 2
            reasons.append(f"Rich in {w}")

    calories = nutrition.get("calories")

    if calories:
        if calories > 350:
            score -= 2
            reasons.append("High calorie food")
        elif calories < 150:
            score += 1
            reasons.append("Low calorie food")
    else:
        calories = "Not Available"

    if score >= 3:
        final_label = "Healthy ⭐⭐⭐⭐⭐"
    elif score >= 0:
        final_label = "Moderate ⚖️"
    else:
        final_label = "Unhealthy ❌"

    return final_label, score, reasons, calories

# ---------------------------
# ROUTES
# ---------------------------
@app.route("/history")
@login_required
def history():
    return render_template("history.html")

@app.route("/dashboard")
@login_required
def dashboard():

    scans = ScanHistory.query.filter_by(
        user_id=current_user.id
    ).all()

    total = len(scans)

    healthy = len([
        s for s in scans
        if "Healthy" in s.prediction
    ])

    unhealthy = total - healthy

    return render_template(
        "dashboard.html",
        total=total,
        healthy=healthy,
        unhealthy=unhealthy
    )

@app.route("/get_dashboard_data")
@login_required
def get_dashboard_data():

    scans = ScanHistory.query.filter_by(
        user_id=current_user.id
     ).order_by(
        ScanHistory.scan_date.desc()
     ).all()

    total_scans = len(scans)

    healthy_count = len([
        s for s in scans
        if "Healthy" in s.prediction
    ])

    unhealthy_count = len([
        s for s in scans
        if "Unhealthy" in s.prediction
    ])

    history = []

    for scan in scans:

        history.append({
            "product": scan.product,
            "prediction": scan.prediction,
            "confidence": round(scan.confidence, 2),
            "calories": scan.calories,
            "date": scan.scan_date.strftime("%d-%m-%Y %I:%M %p")
        })

    return jsonify({
        "total_scans": total_scans,
        "healthy_count": healthy_count,
        "unhealthy_count": unhealthy_count,
        "history": history
    })

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = sanitize_text(request.form.get("full_name") or request.form.get("username") or "").strip()
        email = sanitize_text(request.form.get("email", "")).lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        terms = request.form.get("terms")
        privacy = request.form.get("privacy")

        if not full_name:
            flash("Full name is required.", "error")
            return render_template("register.html")

        email_error = validate_email(email)
        if email_error:
            flash(email_error, "error")
            return render_template("register.html")

        password_error = validate_password(password)
        if password_error:
            flash(password_error, "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        if not terms or not privacy:
            flash("Please accept the terms and privacy policy.", "error")
            return render_template("register.html")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        hashed = bcrypt.generate_password_hash(password).decode("utf-8")
        verify_required = bool(os.getenv("MAIL_SERVER"))
        user = User(
            full_name=full_name,
            email=email,
            password=hashed,
            is_verified=not verify_required,
            theme="dark",
            language="en",
            notifications_enabled=True,
        )
        db.session.add(user)
        db.session.commit()

        preference = UserPreference(user_id=user.id)
        db.session.add(preference)
        db.session.commit()

        verification_token = str(uuid.uuid4())
        user.reset_token = verification_token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=24)
        db.session.add(user)
        db.session.commit()

        verification_link = url_for("verify_email", token=verification_token, _external=True)
        send_email(
            email,
            "Verify your NutriScan AI account",
            f"Hello {full_name},\n\nPlease verify your account by visiting: {verification_link}\n",
        )

        flash("Account created successfully. Please verify your email to continue.", "success")
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = sanitize_text(request.form.get("email", "")).lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            if not user.is_verified:
                flash("Please verify your email before logging in.", "error")
                return redirect("/login")

            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            user.session_token = str(uuid.uuid4())
            user.session_token_expiry = datetime.utcnow() + timedelta(days=7)
            db.session.add(user)
            db.session.commit()
            session["session_token"] = user.session_token
            flash("Welcome back to NutriScan AI.", "success")
            return redirect("/dashboard")

        flash("Invalid email or password.", "error")
        return redirect("/login")

    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = sanitize_text(request.form.get("email", "")).lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = str(uuid.uuid4())
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=24)
            db.session.add(user)
            db.session.commit()
            reset_link = url_for("reset_password", token=token, _external=True)
            send_email(
                email,
                "Reset your NutriScan AI password",
                f"Use this link to reset your password: {reset_link}",
            )
        flash("If the email exists, a reset link has been sent.", "success")
        return redirect("/login")

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        flash("This reset link is invalid or expired.", "error")
        return redirect("/login")

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("reset_password.html", token=token)

        password_error = validate_password(password)
        if password_error:
            flash(password_error, "error")
            return render_template("reset_password.html", token=token)

        user.password = bcrypt.generate_password_hash(password).decode("utf-8")
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.add(user)
        db.session.commit()
        flash("Your password has been reset successfully.", "success")
        return redirect("/login")

    return render_template("reset_password.html", token=token)


@app.route("/verify-email/<token>")
def verify_email(token):
    user = User.query.filter_by(reset_token=token).first()
    if user and user.reset_token_expiry and user.reset_token_expiry >= datetime.utcnow():
        user.is_verified = True
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.add(user)
        db.session.commit()
        flash("Email verified successfully. You can now sign in.", "success")
    else:
        flash("The verification link is invalid or expired.", "error")
    return redirect("/login")


@app.route("/auth/google")
def google_login():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/google/callback")
    if not client_id:
        flash("Google login is not configured yet.", "error")
        return redirect("/login")
    state = str(uuid.uuid4())
    session["oauth_state"] = state
    return redirect(build_google_oauth_url(request.host_url.rstrip("/"), client_id, redirect_uri, state))


@app.route("/auth/google/callback")
def google_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or state != session.pop("oauth_state", None):
        flash("Google sign-in was cancelled or failed.", "error")
        return redirect("/login")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/google/callback"),
        "grant_type": "authorization_code",
    }
    token_response = requests.post(token_url, data=data, timeout=10)
    if token_response.status_code != 200:
        flash("Google sign-in failed.", "error")
        return redirect("/login")

    access_token = token_response.json().get("access_token")
    user_info_response = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if user_info_response.status_code != 200:
        flash("Google sign-in failed.", "error")
        return redirect("/login")

    profile = user_info_response.json()
    email = profile.get("email")
    full_name = profile.get("name") or email.split("@", 1)[0]
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            full_name=full_name,
            email=email,
            password=bcrypt.generate_password_hash(str(uuid.uuid4())).decode("utf-8"),
            is_verified=True,
            theme="dark",
            language="en",
            notifications_enabled=True,
            profile_picture=profile.get("picture"),
        )
        db.session.add(user)
        db.session.commit()
        preference = UserPreference(user_id=user.id)
        db.session.add(preference)
        db.session.commit()

    login_user(user, remember=True)
    user.last_login = datetime.utcnow()
    user.session_token = str(uuid.uuid4())
    user.session_token_expiry = datetime.utcnow() + timedelta(days=7)
    db.session.add(user)
    db.session.commit()
    session["session_token"] = user.session_token
    flash("Signed in with Google.", "success")
    return redirect("/dashboard")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "success")
    return redirect("/")


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/scanner")
def scanner():
    return render_template("scanner.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = User.query.get(current_user.id)
    if request.method == "POST":
        if request.form.get("delete_account"):
            db.session.delete(user)
            db.session.commit()
            logout_user()
            session.clear()
            flash("Your account has been deleted.", "success")
            return redirect("/")

        user.full_name = sanitize_text(request.form.get("full_name", user.full_name))
        user.profile_picture = sanitize_text(request.form.get("profile_picture", user.profile_picture or "")) or None
        user.theme = request.form.get("theme", user.theme)
        user.language = request.form.get("language", user.language)
        user.notifications_enabled = bool(request.form.get("notifications_enabled"))
        db.session.add(user)
        db.session.commit()
        flash("Your profile has been updated.", "success")
        return redirect("/profile")

    return render_template("profile.html", user=user)


@app.route("/favorites")
@login_required
def favorites():
    return render_template("favorites.html")


@app.route("/health-profiles")
@login_required
def health_profiles():
    return render_template("health_profiles.html")


@app.route("/ai-chat")
@login_required
def ai_chat():
    return render_template("ai_chat.html")


@app.route("/grocery-cart")
@login_required
def grocery_cart():
    return render_template("grocery_cart.html")


@app.route("/analytics")
@login_required
def analytics():
    return render_template("analytics.html")

# ---------------------------
# ANALYZE API
# ---------------------------

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        # Check if image exists
        if "image" not in request.files:
            return jsonify({
                "success": False,
                "error": "No image uploaded"
            }), 400

        file = request.files["image"]

        # Check if filename is empty
        if file.filename == "":
            return jsonify({
                "success": False,
                "error": "Please select an image"
            }), 400

        # Save uploaded file
        path = save_file(file)

        # OCR
        text = extract_text(path)

        ocr_facts = extract_nutrition_facts(text)

        # ML Prediction
        ml_label, confidence = predict_health(text)

        # Food Detection
        food_item = extract_food(text)

        # Nutrition API
        nutrition = nutrition_api(food_item)

        # Make sure nutrition is always a dictionary
        if not isinstance(nutrition, dict):
            nutrition = {}

        # Explainable AI
        final_label, score, reasons, calories = explain_health(
            text,
            nutrition
        )
         # Save scan history if user is logged in
        if current_user.is_authenticated:

             scan = ScanHistory(
                 user_id=current_user.id,
                 product=food_item,
                 prediction=final_label,
                 confidence=confidence,
                 calories=str(
                     ocr_facts["calories"]
                     if ocr_facts["calories"]
                     else calories
                     )
                     )

             db.session.add(scan)
             db.session.commit()

        # Send response to frontend
        return jsonify({
            "success": True,

            "ocr_text": text,
            "food_item": food_item,

            "ml_label": ml_label,
            "confidence_percent": confidence,

            "final_label": final_label,
            "score_percent": score,

            "calories": (
                 ocr_facts["calories"]
                 if ocr_facts["calories"]
                 else calories
           ),
            "nutrition_facts": {
                 "calories": ocr_facts["calories"],
                 "sugar_g": ocr_facts["sugar_g"],
                 "sodium_mg": ocr_facts["sodium_mg"],
                 "fat_g": ocr_facts["fat_g"],
                 "fiber_g": ocr_facts["fiber_g"]
            },
            "reasons": reasons,

            "data_quality": (
                "Good" if len(text) > 20 else "Low"
            ),

            "risk_level": final_label.replace(
                "⭐⭐⭐⭐⭐", ""
            ).replace(
                "⚖️", ""
            ).replace(
                "❌", ""
            ).strip()
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    with app.app_context():
         db.create_all()

    app.run(debug=True)






