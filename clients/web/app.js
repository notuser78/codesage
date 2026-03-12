const API_URL = window.CODESAGE_API_URL || "http://localhost:8000";

const form = document.getElementById("analyze-form");
const output = document.getElementById("output");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const url = document.getElementById("repo-url").value;
  const branch = document.getElementById("branch").value;

  output.textContent = "Submitting analysis request...";

  try {
    const response = await fetch(`${API_URL}/api/v1/repositories/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url,
        branch,
        analysis_types: ["security", "performance", "quality"],
      }),
    });

    const payload = await response.json();

    if (!response.ok) {
      output.textContent = `Request failed (${response.status}): ${JSON.stringify(payload, null, 2)}`;
      return;
    }

    output.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    output.textContent = `Unable to reach API at ${API_URL}.\n\n${error}`;
  }
});
