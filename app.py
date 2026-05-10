from flask import Flask, render_template, request, jsonify
import pytesseract
from PIL import Image
import pickle
import requests
import os
import re
import cv2

# TESSERACT PATH
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)

# UPLOAD FOLDER
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# LOAD MODEL
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# API
APP_ID = "207b082b"
APP_KEY = "d43d95b70d64ef01df512a55f93dbf7b"

# -----------------------------------
# IMAGE PREPROCESSING
# -----------------------------------
def preprocess_image(path):

    img = cv2.imread(path)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    thresh = cv2.threshold(
        blur,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    processed_path = "uploads/processed.png"

    cv2.imwrite(processed_path, thresh)

    return processed_path

# -----------------------------------
# OCR
# -----------------------------------
def extract_text(path):

    processed = preprocess_image(path)

    custom_config = r'--oem 3 --psm 6'

    text = pytesseract.image_to_string(
        Image.open(processed),
        config=custom_config
    )

    text = text.lower()

    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)

    return text

# -----------------------------------
# FOOD DETECTION
# -----------------------------------
def extract_food(text):

    foods = [
        "milk",
        "bread",
        "rice",
        "juice",
        "chips",
        "cake",
        "pizza",
        "burger",
        "oats",
        "banana",
        "apple",
        "coffee",
        "tea",
        "salad",
        "chocolate"
    ]

    for food in foods:
        if food in text:
            return food

    return "healthy food"

# -----------------------------------
# NUTRITION API
# -----------------------------------
def nutrition_api(food):

    url = f"https://api.edamam.com/api/nutrition-data?app_id={APP_ID}&app_key={APP_KEY}&ingr={food}"

    try:
        response = requests.get(url)

        return response.json()

    except:
        return {}

# -----------------------------------
# MACHINE LEARNING
# -----------------------------------
def predict_health(text):

    vec = vectorizer.transform([text])

    prediction = model.predict(vec)[0]

    probability = model.predict_proba(vec)[0]

    confidence = round(float(max(probability)) * 100, 2)

    if prediction == 1:
        label = "Healthy ⭐⭐⭐⭐⭐"

    else:
        label = "Unhealthy ❌"

    return label, confidence

# -----------------------------------
# EXPLAINABLE AI
# -----------------------------------
def explain_health(text, nutrition):

    score = 0

    reasons = []

    unhealthy_words = [
        "sugar",
        "fried",
        "oil",
        "cola",
        "syrup",
        "fat",
        "preservatives",
        "junk"
    ]

    healthy_words = [
        "protein",
        "fiber",
        "natural",
        "vitamin",
        "fresh",
        "organic",
        "whole grain"
    ]

    for word in unhealthy_words:

        if word in text:
            score -= 2
            reasons.append(f"Contains {word}")

    for word in healthy_words:

        if word in text:
            score += 2
            reasons.append(f"Rich in {word}")

    calories = nutrition.get("calories", 0)

    if calories > 350:
        score -= 2
        reasons.append("High calorie food")

    elif calories < 150:
        score += 1
        reasons.append("Low calorie food")

    # FINAL LABEL
    if score >= 3:
        final_label = "Healthy ⭐⭐⭐⭐⭐"

    elif score >= 0:
        final_label = "Moderate ⚖️"

    else:
        final_label = "Unhealthy ❌"

    return final_label, score, reasons, calories

# -----------------------------------
# ROUTES
# -----------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/scanner")
def scanner():
    return render_template("scanner.html")

@app.route("/about")
def about():
    return render_template("about.html")

# -----------------------------------
# ANALYZE
# -----------------------------------
@app.route("/analyze", methods=["POST"])
def analyze():

    file = request.files["image"]

    path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(path)

    # OCR
    text = extract_text(path)

    # ML
    ml_label, confidence = predict_health(text)

    # FOOD
    food_item = extract_food(text)

    # API
    nutrition = nutrition_api(food_item)

    # EXPLAINABLE AI
    final_label, score, reasons, calories = explain_health(
        text,
        nutrition
    )

    return jsonify({
        "ocr_text": text,
        "ml_label": ml_label,
        "final_label": final_label,
        "confidence": confidence,
        "score": score,
        "calories": calories,
        "reasons": reasons
    })

# -----------------------------------
# MAIN
# -----------------------------------
if __name__ == "__main__":

    os.makedirs("uploads", exist_ok=True)

    app.run(host="0.0.0.0", port=5000, debug=True)