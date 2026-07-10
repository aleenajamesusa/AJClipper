const tabs = document.querySelectorAll(".tab");
const tabFile = document.getElementById("tab-file");
const tabUrl = document.getElementById("tab-url");
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("video_file");
const dzFileName = document.getElementById("dz-file-name");
const urlInput = document.getElementById("video_url");
const apiKeyInput = document.getElementById("api_key");
const modelSelect = document.getElementById("model_size");
const runBtn = document.getElementById("run-btn");
const errorMsg = document.getElementById("error-msg");

const inputPanel = document.getElementById("input-panel");
const statusPanel = document.getElementById("status-panel");
const resultsPanel = document.getElementById("results-panel");
const statusLabel = document.getElementById("status-label");
const statusDetail = document.getElementById("status-detail");
const progressFill = document.getElementById("progress-fill");
const clipList = document.getElementById("clip-list");
const resetBtn = document.getElementById("reset-btn");

let activeTab = "file";

tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    tabs.forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    activeTab = tab.dataset.tab;
    tabFile.classList.toggle("hidden", activeTab !== "file");
    tabUrl.classList.toggle("hidden", activeTab !== "url");
  });
});

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", e => { e.preventDefault(); dropzone.classList.add("drag"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", e => {
  e.preventDefault();
  dropzone.classList.remove("drag");
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    dzFileName.textContent = fileInput.files[0].name;
  }
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) dzFileName.textContent = fileInput.files[0].name;
});

const STATUS_COPY = {
  queued: "Queued",
  preparing: "Preparing video",
  downloading: "Downloading video",
  transcribing: "Transcribing audio",
  analyzing: "Finding the best moments",
  clipping: "Cutting clips",
  done: "Done",
  error: "Something went wrong",
};

const STATUS_PROGRESS = {
  queued: 5, preparing: 10, downloading: 20, transcribing: 45,
  analyzing: 65, clipping: 80, done: 100, error: 100,
};

runBtn.addEventListener("click", async () => {
  errorMsg.textContent = "";
  const apiKey = apiKeyInput.value.trim();
  if (!apiKey) { errorMsg.textContent = "Enter your Anthropic API key."; return; }

  const formData = new FormData();
  formData.append("api_key", apiKey);
  formData.append("model_size", modelSelect.value);

  if (activeTab === "file") {
    if (!fileInput.files.length) { errorMsg.textContent = "Choose a video file first."; return; }
    formData.append("video_file", fileInput.files[0]);
  } else {
    const url = urlInput.value.trim();
    if (!url) { errorMsg.textContent = "Paste a video link first."; return; }
    formData.append("video_url", url);
  }

  runBtn.disabled = true;
  runBtn.textContent = "Working…";

  try {
    const res = await fetch("/api/process", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed.");
    inputPanel.classList.add("hidden");
    statusPanel.classList.remove("hidden");
    pollStatus(data.job_id);
  } catch (err) {
    errorMsg.textContent = err.message;
    runBtn.disabled = false;
    runBtn.textContent = "Find the clips";
  }
});

async function pollStatus(jobId) {
  try {
    const res = await fetch(`/api/status/${jobId}`);
    const job = await res.json();

    statusLabel.textContent = STATUS_COPY[job.status] || job.status;
    statusDetail.textContent = job.detail || "";
    progressFill.style.width = `${STATUS_PROGRESS[job.status] || 10}%`;

    if (job.status === "done") {
      showResults(jobId, job.results);
      return;
    }
    if (job.status === "error") {
      statusPanel.classList.add("hidden");
      inputPanel.classList.remove("hidden");
      errorMsg.textContent = job.detail || "Something went wrong.";
      runBtn.disabled = false;
      runBtn.textContent = "Find the clips";
      return;
    }
    setTimeout(() => pollStatus(jobId), 1500);
  } catch (err) {
    setTimeout(() => pollStatus(jobId), 2500);
  }
}

function showResults(jobId, results) {
  statusPanel.classList.add("hidden");
  resultsPanel.classList.remove("hidden");
  clipList.innerHTML = "";

  results.forEach(clip => {
    const card = document.createElement("div");
    card.className = "clip-card";
    const mm1 = Math.floor(clip.start / 60), ss1 = Math.floor(clip.start % 60);
    const mm2 = Math.floor(clip.end / 60), ss2 = Math.floor(clip.end % 60);
    const timeStr = `${mm1}:${String(ss1).padStart(2,"0")} – ${mm2}:${String(ss2).padStart(2,"0")} (${clip.duration}s)`;
    const fileUrl = `/clips/${jobId}/${clip.file}`;

    card.innerHTML = `
      <div class="clip-score">${clip.virality_score ?? "–"}</div>
      <div class="clip-body">
        <p class="clip-title">${escapeHtml(clip.title)}</p>
        <p class="clip-reason">${escapeHtml(clip.hook_reason)}</p>
        <p class="clip-meta">${timeStr}</p>
        <div class="clip-actions">
          <a href="${fileUrl}" target="_blank">Preview</a>
          <a href="${fileUrl}" download>Download</a>
        </div>
      </div>
    `;
    clipList.appendChild(card);
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

resetBtn.addEventListener("click", () => {
  resultsPanel.classList.add("hidden");
  inputPanel.classList.remove("hidden");
  runBtn.disabled = false;
  runBtn.textContent = "Find the clips";
  fileInput.value = "";
  urlInput.value = "";
  dzFileName.textContent = "";
  progressFill.style.width = "8%";
});
