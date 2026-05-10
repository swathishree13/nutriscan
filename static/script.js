const video = document.getElementById("camera");

if (video) {

    navigator.mediaDevices.getUserMedia({
        video: true
    })

    .then(stream => {
        video.srcObject = stream;
    })

    .catch(error => {
        alert("Camera access denied");
        console.log(error);
    });
}

function capture() {

    const canvas = document.getElementById("canvas");

    const ctx = canvas.getContext("2d");

    canvas.width = video.videoWidth;

    canvas.height = video.videoHeight;

    ctx.drawImage(video, 0, 0);

    alert("Image Captured Successfully ✅");
}

function analyze() {

    const canvas = document.getElementById("canvas");

    canvas.toBlob(blob => {

        const formData = new FormData();

        formData.append(
            "image",
            blob,
            "scan.png"
        );

        document.getElementById("output").innerHTML =
            "<h3>Analyzing...</h3>";

        fetch("/analyze", {
            method: "POST",
            body: formData
        })

        .then(response => response.json())

        .then(data => {

            document.getElementById("output").innerHTML = `

            <div class="result-card">

                <h2>${data.final_label}</h2>

                <p><strong>ML Prediction:</strong> ${data.ml_label}</p>

                <p><strong>Confidence:</strong> ${data.confidence}%</p>

                <p><strong>Health Score:</strong> ${data.score}</p>

                <p><strong>Calories:</strong> ${data.calories}</p>

                <h3>Detected Text</h3>

                <div class="ocr-box">
                    ${data.ocr_text}
                </div>

                <h3>AI Analysis</h3>

                <ul>
                    ${data.reasons.map(
                        reason => `<li>${reason}</li>`
                    ).join("")}
                </ul>

            </div>
            `;
        })

        .catch(error => {

            console.log(error);

            document.getElementById("output").innerHTML =
                "<h3>Error analyzing image</h3>";
        });

    }, "image/png");
}