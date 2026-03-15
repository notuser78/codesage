const API_URL = window.CODESAGE_API_URL || "http://localhost:8000";

const form = document.getElementById("analyze-form");
const output = document.getElementById("output");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const url = document.getElementById("repo-url").value;
  const branch = document.getElementById("branch").value;

  output.textContent = "Creating repository and submitting analysis request...";

  try {
    // Step 1: Register repository
    const createRepoRes = await fetch(`${API_URL}/api/v1/repositories`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url,
        branch,
      }),
    });

    const createRepoPayload = await createRepoRes.json();

    if (!createRepoRes.ok) {
      output.textContent = `Create repo failed (${createRepoRes.status}): ${JSON.stringify(createRepoPayload, null, 2)}`;
      return;
    }

    // Step 2: Trigger analysis for the new repository
    const analyzeRes = await fetch(`${API_URL}/api/v1/repositories/${createRepoPayload.id}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        analysis_types: ["security", "performance", "quality"],
      }),
    });

    const analyzePayload = await analyzeRes.json();

    if (!analyzeRes.ok) {
      output.textContent = `Analysis request failed (${analyzeRes.status}): ${JSON.stringify(analyzePayload, null, 2)}`;
      return;
    }

    output.textContent = JSON.stringify({ repository: createRepoPayload, analysis: analyzePayload }, null, 2);
  } catch (error) {
    output.textContent = `Unable to reach API at ${API_URL}.\n\n${error}`;
  }
});
