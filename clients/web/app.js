const API_URL_STORAGE_KEY = "codesage.apiUrl";

const normalizeApiUrl = (value) => (value || "").trim().replace(/\/$/, "");

const detectDefaultApiUrl = () => {
  const fromWindow = normalizeApiUrl(window.CODESAGE_API_URL);
  if (fromWindow) {
    return fromWindow;
  }

  const fromQuery = normalizeApiUrl(new URLSearchParams(window.location.search).get("api"));
  if (fromQuery) {
    return fromQuery;
  }

  const fromStorage = normalizeApiUrl(window.localStorage.getItem(API_URL_STORAGE_KEY));
  if (fromStorage) {
    return fromStorage;
  }

  if (window.location.hostname.includes("onrender.com")) {
    return `${window.location.protocol}//${window.location.hostname.replace(/-web(?=\.)/, "-api")}`;
  }

  return "http://localhost:8000";
};

let apiUrl = detectDefaultApiUrl();

const form = document.getElementById("analyze-form");
const output = document.getElementById("output");
const apiUrlInput = document.getElementById("api-url");
const saveApiUrlButton = document.getElementById("save-api-url");
const apiStatus = document.getElementById("api-status");

const setApiStatus = (message) => {
  apiStatus.textContent = message;
};

const setApiUrl = (nextApiUrl, persist = false) => {
  const normalized = normalizeApiUrl(nextApiUrl);
  if (!normalized) {
    setApiStatus("API URL cannot be empty.");
    return false;
  }

  apiUrl = normalized;
  apiUrlInput.value = apiUrl;

  if (persist) {
    window.localStorage.setItem(API_URL_STORAGE_KEY, apiUrl);
  }

  setApiStatus(`Using API: ${apiUrl}`);
  return true;
};

setApiUrl(apiUrl);

saveApiUrlButton.addEventListener("click", () => {
  const didSet = setApiUrl(apiUrlInput.value, true);
  if (didSet) {
    output.textContent = "Saved API URL. Submit the form to run analysis.";
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const didSet = setApiUrl(apiUrlInput.value, true);
  if (!didSet) {
    return;
  }

  const url = document.getElementById("repo-url").value;
  const branch = document.getElementById("branch").value;

  output.textContent = "Creating repository and submitting analysis request...";

  try {
    const createRepoRes = await fetch(`${apiUrl}/api/v1/repositories`, {
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

    const analyzeRes = await fetch(`${apiUrl}/api/v1/repositories/${createRepoPayload.id}/analyze`, {
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
    output.textContent = `Unable to reach API at ${apiUrl}.\n\n${error}`;
  }
});
