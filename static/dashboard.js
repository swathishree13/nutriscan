document.addEventListener("DOMContentLoaded", () => {
    loadDashboard();
});

async function loadDashboard() {

    const totalScans = document.getElementById("totalScans");
    const healthyCount = document.getElementById("healthyCount");
    const unhealthyCount = document.getElementById("unhealthyCount");
    const historyDiv = document.getElementById("scanHistory");

    try {

        const response = await fetch("/get_dashboard_data");

        if (!response.ok) {
            throw new Error("Unable to fetch dashboard data.");
        }

        const data = await response.json();

        totalScans.textContent = data.total_scans || 0;
        healthyCount.textContent = data.healthy_count || 0;
        unhealthyCount.textContent = data.unhealthy_count || 0;

        historyDiv.innerHTML = "";

        if (!data.history || data.history.length === 0) {

            historyDiv.innerHTML = `
                <div class="history-card">
                    <h3>No Scan History</h3>
                    <p>You haven't scanned any food products yet.</p>
                </div>
            `;
            return;
        }

        data.history.forEach(item => {

            const confidence =
                Number(item.confidence || 0).toFixed(2);

            historyDiv.innerHTML += `
                <div class="history-card">

                    <h3>${item.product}</h3>

                    <p>
                        <strong>Prediction:</strong>
                        ${item.prediction}
                    </p>

                    <p>
                        <strong>Confidence:</strong>
                        ${confidence}%
                    </p>

                    <p>
                        <strong>Calories:</strong>
                        ${item.calories || "Unknown"}
                    </p>

                </div>
            `;
        });

    } catch (error) {

        console.error(error);

        historyDiv.innerHTML = `
            <div class="history-card">
                <h3>Error</h3>
                <p>Unable to load dashboard data.</p>
            </div>
        `;
    }
}