const video = document.getElementById("camera");
const loading = document.getElementById("loading");

if (video) {

    navigator.mediaDevices.getUserMedia({
        video: {
            facingMode: "environment"
        }
    })
    .then(stream => {
        video.srcObject = stream;
    })
    .catch(error => {
        console.log(error);
        alert("Camera access denied or unavailable");
    });
}

function capture() {

    const canvas = document.getElementById("canvas");

    if (!canvas || !video) {
        return;
    }

    const ctx = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.drawImage(video, 0, 0);

    alert("Image Captured Successfully");
}

function analyze() {

    const canvas = document.getElementById("canvas");

    if (!canvas) {
        return;
    }

    loading.classList.remove("hidden");

    canvas.toBlob(blob => {

        const formData = new FormData();
        formData.append("image", blob, "scan.png");

        fetch("/analyze", {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {

            loading.classList.add("hidden");

            document.getElementById("output").innerHTML = `

                <div class="result-card">

                    <h2>${data.final_label}</h2>

                    <div class="result-grid">

                        <div class="result-item">
                            <span>ML Prediction</span>
                            <strong>${data.ml_label}</strong>
                        </div>

                        <div class="result-item">
                            <span>Confidence</span>
                            <strong>${(data.confidence * 100).toFixed(2)}%</strong>
                        </div>

                        <div class="result-item">
                            <span>Health Score</span>
                            <strong>${data.score}</strong>
                        </div>

                        <div class="result-item">
                            <span>Calories</span>
                            <strong>${data.calories}</strong>
                        </div>

                    </div>

                    <ul class="reason-list">
                        ${data.reasons.map(reason => `<li>${reason}</li>`).join("")}
                    </ul>

                </div>
            `;
        })
        .catch(error => {
            loading.classList.add("hidden");
            console.log(error);
            alert("Analysis Failed");
        });

    }, "image/png");
}