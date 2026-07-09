const $ = (id) => document.getElementById(id);

// -------------------- ELEMENTS --------------------
const video = $("camera");
const canvas = $("canvas");
const preview = $("preview");
const emptyPreview = $("emptyPreview");
const loading = $("loading");
const message = $("message");
const uploadInput = $("imageUpload");
const captureBtn = $("captureBtn");
const analyzeBtn = $("analyzeBtn");
const cameraStatus = $("cameraStatus");
const output = $("output");

let selectedBlob = null;
let previewURL = null;

// -------------------- INIT --------------------
document.addEventListener("DOMContentLoaded", () => {
    startCamera();

    captureBtn.addEventListener("click", captureImage);
    analyzeBtn.addEventListener("click", analyzeImage);
    uploadInput.addEventListener("change", handleUpload);
});

// -------------------- CAMERA --------------------
async function startCamera() {

    if (!navigator.mediaDevices) {
        setStatus("Camera not supported", "error");
        return;
    }

    try {

        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: {
                    ideal: "environment"
                }
            }
        });

        video.srcObject = stream;

        await video.play();

        setStatus("Camera Ready", "ready");

    } catch (err) {

        console.error(err);

        setStatus("Upload Image Instead", "error");

        showMessage(
            "Unable to access camera. Please upload an image.",
            "error"
        );
    }
}

// -------------------- CAPTURE --------------------
function captureImage() {

    if (!video.videoWidth) {
        return showMessage("Camera not ready", "error");
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");

    ctx.drawImage(video, 0, 0);

    canvas.toBlob(blob => {

        selectedBlob = blob;

        showPreview(blob);

        showMessage("Image captured successfully.");

    }, "image/png");
}

// -------------------- IMAGE UPLOAD --------------------
function handleUpload(event) {

    const file = event.target.files[0];

    if (!file) return;

    selectedBlob = file;

    showPreview(file);

    showMessage("Image uploaded successfully.");
}

// -------------------- ANALYZE --------------------
async function analyzeImage() {

    if (!selectedBlob) {
        return showMessage(
            "Please capture or upload an image first.",
            "error"
        );
    }

    setLoading(true);

    output.innerHTML = "";

    try {

        const formData = new FormData();

        formData.append(
            "image",
            selectedBlob,
            "scan.png"
        );

        const response = await fetch("/analyze", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error("Server Error");
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(
                data.error || "Analysis failed"
            );
        }

        renderResult(data);

        showMessage("Analysis completed.");

    } catch (err) {

        console.error(err);

        showMessage(
            err.message,
            "error"
        );

    } finally {

        setLoading(false);
    }
}

// -------------------- RESULT --------------------
function renderResult(data) {

    const facts = data.nutrition_facts || {};

    const confidence =
        Number(data.confidence_percent || 0).toFixed(2);

    output.innerHTML = `

<div class="result-card">

<h2>🧠 AI Nutrition Analysis</h2>

<div class="result-grid">

<div class="result-item">
<span>🍱 Food</span>
<strong>${data.food_item || "Unknown"}</strong>
</div>

<div class="result-item">
<span>🤖 ML Prediction</span>
<strong>${data.ml_label}</strong>
</div>

<div class="result-item">
<span>📊 Final Verdict</span>
<strong>${data.final_label}</strong>
</div>

<div class="result-item">
<span>🎯 Confidence</span>
<strong>${confidence}%</strong>
</div>

<div class="result-item">
<span>🔥 Calories</span>
<strong>${data.calories ?? "Unknown"}</strong>
</div>

</div>

<h3>Nutrition Facts</h3>

<ul class="reason-list">

<li>Calories : ${facts.calories ?? "Unknown"}</li>

<li>Sugar : ${facts.sugar_g ?? "Unknown"} g</li>

<li>Sodium : ${facts.sodium_mg ?? "Unknown"} mg</li>

<li>Fat : ${facts.fat_g ?? "Unknown"} g</li>

<li>Fiber : ${facts.fiber_g ?? "Unknown"} g</li>

</ul>

<h3>AI Explanation</h3>

<ul class="reason-list">

${
(data.reasons || [])
.map(reason => `<li>${reason}</li>`)
.join("")
}

</ul>

<h3>OCR Text</h3>

<p class="ocr-box">

${data.ocr_text || "No text detected"}

</p>

</div>

`;
}

// -------------------- PREVIEW --------------------
function showPreview(file) {

    if (previewURL) {
        URL.revokeObjectURL(previewURL);
    }

    previewURL = URL.createObjectURL(file);

    preview.src = previewURL;

    preview.hidden = false;

    emptyPreview.style.display = "none";
}

// -------------------- LOADING --------------------
function setLoading(state) {

    loading.classList.toggle(
        "hidden",
        !state
    );

    captureBtn.disabled = state;

    analyzeBtn.disabled = state;

    uploadInput.disabled = state;
}

// -------------------- STATUS --------------------
function setStatus(text, type) {

    cameraStatus.textContent = text;

    cameraStatus.className =
        `status-pill ${type}`;
}

// -------------------- MESSAGE --------------------
function showMessage(text, type = "") {

    message.textContent = text;

    message.className =
        `form-message ${type}`;
}