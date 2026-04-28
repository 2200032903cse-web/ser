const authScreen = document.getElementById("authScreen");
const appShell = document.getElementById("appShell");
const loginTab = document.getElementById("loginTab");
const signupTab = document.getElementById("signupTab");
const loginForm = document.getElementById("loginForm");
const signupForm = document.getElementById("signupForm");
const authMessage = document.getElementById("authMessage");
const logoutBtn = document.getElementById("logoutBtn");
const signedInUser = document.getElementById("signedInUser");

const pages = {
  predict: document.getElementById("predictPage"),
  history: document.getElementById("historyPage"),
  metrics: document.getElementById("metricsPage"),
  about: document.getElementById("aboutPage"),
};

const pageTitle = document.getElementById("pageTitle");
const navLinks = document.querySelectorAll(".nav-link");
const mobileNav = document.getElementById("mobileNav");
const batchName = document.getElementById("batchName");
const memberCount = document.getElementById("memberCount");
const teamList = document.getElementById("teamList");
const apiStatus = document.getElementById("apiStatus");

const dropZone = document.getElementById("dropZone");
const audioInput = document.getElementById("audioInput");
const chooseFileBtn = document.getElementById("chooseFileBtn");
const recordBtn = document.getElementById("recordBtn");
const stopRecordBtn = document.getElementById("stopRecordBtn");
const recordingDot = document.getElementById("recordingDot");
const recordingStatus = document.getElementById("recordingStatus");
const predictBtn = document.getElementById("predictBtn");
const buttonText = document.getElementById("buttonText");
const loadingSpinner = document.getElementById("loadingSpinner");
const fileName = document.getElementById("fileName");
const message = document.getElementById("message");

const resultEmpty = document.getElementById("resultEmpty");
const resultCard = document.getElementById("resultCard");
const emotionEmoji = document.getElementById("emotionEmoji");
const emotionLabel = document.getElementById("emotionLabel");
const confidenceText = document.getElementById("confidenceText");
const confidenceBar = document.getElementById("confidenceBar");

const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
const clearHistoryBtn = document.getElementById("clearHistoryBtn");
const historySort = document.getElementById("historySort");
const historyBody = document.getElementById("historyBody");

const TOKEN_KEY = "ser_auth_token";
const USERNAME_KEY = "ser_username";

let selectedFile = null;
let authToken = localStorage.getItem(TOKEN_KEY);
let currentUsername = localStorage.getItem(USERNAME_KEY);
let mediaRecorder = null;
let mediaStream = null;
let recordedChunks = [];
let recordingMimeType = "";

const emojiMap = {
  happy: "\uD83D\uDE04",
  happiness: "\uD83D\uDE04",
  sad: "\uD83D\uDE22",
  sadness: "\uD83D\uDE22",
  angry: "\uD83D\uDE21",
  anger: "\uD83D\uDE21",
  neutral: "\uD83D\uDE10",
  fear: "\uD83D\uDE28",
  fearful: "\uD83D\uDE28",
  disgust: "\uD83E\uDD22",
  surprise: "\uD83D\uDE2E",
  surprised: "\uD83D\uDE2E",
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setAuthMessage(text, tone = "muted") {
  authMessage.textContent = text;
  authMessage.className = "mt-4 min-h-6 text-sm";
  const colors = {
    muted: "text-zinc-400",
    success: "text-teal-300",
    error: "text-rose-300",
  };
  authMessage.classList.add(colors[tone]);
}

function setAuthMode(mode) {
  const isLogin = mode === "login";
  loginForm.classList.toggle("hidden", !isLogin);
  signupForm.classList.toggle("hidden", isLogin);
  loginTab.classList.toggle("active", isLogin);
  signupTab.classList.toggle("active", !isLogin);
  setAuthMessage("");
}

function saveSession(token, username) {
  authToken = token;
  currentUsername = username;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USERNAME_KEY, username);
}

function clearSession() {
  authToken = null;
  currentUsername = null;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USERNAME_KEY);
}

async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (authToken) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }

  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) {
    clearSession();
    showAuth();
    throw new Error("Please login again.");
  }
  return response;
}

async function submitAuth(mode, form) {
  const username = form.querySelector("input[id$='Username']").value.trim();
  const password = form.querySelector("input[id$='Password']").value;

  if (!username || !password) {
    setAuthMessage("Enter username and password.", "error");
    return;
  }

  setAuthMessage(mode === "login" ? "Logging in..." : "Creating account...");

  try {
    const response = await fetch(`/${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Authentication failed.");
    }

    saveSession(data.token, data.username);
    form.reset();
    showDashboard();
  } catch (error) {
    setAuthMessage(error.message, "error");
  }
}

function showAuth() {
  authScreen.classList.remove("hidden");
  appShell.classList.add("hidden");
  appShell.classList.remove("flex");
  setAuthMode("login");
}

function showDashboard() {
  authScreen.classList.add("hidden");
  appShell.classList.remove("hidden");
  appShell.classList.add("flex");
  signedInUser.textContent = currentUsername || "User";
  loadTeam();
  showPage("predict");
}

function showPage(page) {
  Object.entries(pages).forEach(([key, element]) => {
    element.classList.toggle("hidden", key !== page);
  });

  navLinks.forEach((link) => {
    link.classList.toggle("active", link.dataset.page === page);
  });

  mobileNav.value = page;
  pageTitle.textContent = page.charAt(0).toUpperCase() + page.slice(1);

  if (page === "history") {
    loadHistory();
  }
}

function setLoading(isLoading) {
  predictBtn.disabled = isLoading || !selectedFile;
  buttonText.textContent = isLoading ? "Analyzing" : "Predict Emotion";
  loadingSpinner.classList.toggle("hidden", !isLoading);
}

function setMessage(text, tone = "muted") {
  message.textContent = text;
  message.className = "min-h-6 text-sm";
  const colors = {
    muted: "text-zinc-400",
    success: "text-teal-300",
    error: "text-rose-300",
  };
  message.classList.add(colors[tone]);
}

function setFile(file) {
  selectedFile = file;
  fileName.textContent = file ? file.name : "Drop a WAV file here or choose from your device.";
  predictBtn.disabled = !file;
  setMessage(file ? "Ready to predict." : "");
}

function showResult(data) {
  const emotion = data.emotion || "neutral";
  const confidence = Math.round(Number(data.confidence || 0) * 100);

  resultEmpty.classList.add("hidden");
  resultCard.classList.remove("hidden");
  emotionEmoji.textContent = emojiMap[emotion.toLowerCase()] || "\uD83C\uDFA7";
  emotionLabel.textContent = emotion;
  confidenceText.textContent = `${confidence}%`;
  confidenceBar.style.width = `${Math.min(confidence, 100)}%`;
}

async function predictEmotion() {
  if (!selectedFile) {
    setMessage("Choose or record an audio file first.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", selectedFile);

  setLoading(true);
  setMessage("Running pretrained wav2vec2 inference...");

  try {
    const response = await apiFetch("/predict", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Prediction failed.");
    }

    showResult(data);
    setMessage("Prediction complete.", "success");
    if (!pages.history.classList.contains("hidden")) {
      loadHistory();
    }
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    setLoading(false);
  }
}

async function loadTeam() {
  try {
    const response = await apiFetch("/team");
    const team = await response.json();
    batchName.textContent = team.batch;
    memberCount.textContent = `${team.members.length} members`;
    teamList.innerHTML = team.members.map((name) => `<li>${escapeHtml(name)}</li>`).join("");
    apiStatus.textContent = "Online";
    apiStatus.classList.remove("offline");
    apiStatus.classList.add("online");
  } catch {
    apiStatus.textContent = "Offline";
    apiStatus.classList.remove("online");
    apiStatus.classList.add("offline");
  }
}

async function loadHistory() {
  const sort = historySort.value || "desc";
  historyBody.innerHTML = `<tr><td class="py-4 text-zinc-500" colspan="4">Loading...</td></tr>`;

  try {
    const response = await apiFetch(`/history?sort=${encodeURIComponent(sort)}`);
    const history = await response.json();

    if (!response.ok) {
      throw new Error(history.detail || "Could not load history.");
    }

    if (!history.length) {
      historyBody.innerHTML = `<tr><td class="py-4 text-zinc-500" colspan="4">No predictions logged yet.</td></tr>`;
      return;
    }

    historyBody.innerHTML = history
      .map((row) => {
        const confidence = Math.round(Number(row.confidence || 0) * 100);
        return `
          <tr>
            <td class="py-3 pr-4">${escapeHtml(row.timestamp)}</td>
            <td class="py-3 pr-4">${escapeHtml(row.filename)}</td>
            <td class="py-3 pr-4 capitalize">${escapeHtml(row.emotion)}</td>
            <td class="py-3 pr-4 text-teal-300">${confidence}%</td>
          </tr>
        `;
      })
      .join("");
  } catch (error) {
    historyBody.innerHTML = `<tr><td class="py-4 text-rose-300" colspan="4">${escapeHtml(error.message)}</td></tr>`;
  }
}

async function clearHistory() {
  const confirmed = window.confirm("Clear your prediction history?");
  if (!confirmed) {
    return;
  }

  try {
    const response = await apiFetch("/history", { method: "DELETE" });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "Could not clear history.");
    }
    loadHistory();
  } catch (error) {
    historyBody.innerHTML = `<tr><td class="py-4 text-rose-300" colspan="4">${escapeHtml(error.message)}</td></tr>`;
  }
}

function getRecorderMimeType() {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];

  return types.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function extensionFromMimeType(type) {
  if (type.includes("ogg")) return "ogg";
  if (type.includes("mp4")) return "mp4";
  if (type.includes("wav")) return "wav";
  return "webm";
}

function setRecordingState(isRecording) {
  recordBtn.disabled = isRecording;
  stopRecordBtn.disabled = !isRecording;
  recordingDot.classList.toggle("hidden", !isRecording);
  recordingStatus.textContent = isRecording ? "Recording..." : "Microphone ready";
}

function stopMediaTracks() {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }
}

async function startRecording() {
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    setMessage("Audio recording is not supported in this browser.", "error");
    return;
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordingMimeType = getRecorderMimeType();
    recordedChunks = [];

    const options = recordingMimeType ? { mimeType: recordingMimeType } : undefined;
    mediaRecorder = new MediaRecorder(mediaStream, options);

    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        recordedChunks.push(event.data);
      }
    });

    mediaRecorder.addEventListener("stop", () => {
      const type = recordingMimeType || "audio/webm";
      const blob = new Blob(recordedChunks, { type });
      const extension = extensionFromMimeType(type);
      const recordingFile = new File([blob], `recording-${Date.now()}.${extension}`, { type });
      setFile(recordingFile);
      stopMediaTracks();
      setRecordingState(false);
      setMessage("Recording ready to predict.", "success");
    });

    mediaRecorder.start();
    setRecordingState(true);
    setMessage("Recording speech audio...");
  } catch (error) {
    stopMediaTracks();
    setRecordingState(false);
    setMessage(error.message || "Microphone permission was denied.", "error");
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

async function logout() {
  try {
    if (authToken) {
      await apiFetch("/logout", { method: "POST" });
    }
  } catch {
    // Logging out should still clear the local session.
  } finally {
    clearSession();
    setFile(null);
    showAuth();
  }
}

loginTab.addEventListener("click", () => setAuthMode("login"));
signupTab.addEventListener("click", () => setAuthMode("signup"));
loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitAuth("login", loginForm);
});
signupForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitAuth("signup", signupForm);
});
logoutBtn.addEventListener("click", logout);

navLinks.forEach((link) => {
  link.addEventListener("click", () => showPage(link.dataset.page));
});

mobileNav.addEventListener("change", (event) => showPage(event.target.value));
chooseFileBtn.addEventListener("click", () => audioInput.click());
audioInput.addEventListener("change", (event) => setFile(event.target.files[0]));
predictBtn.addEventListener("click", predictEmotion);
recordBtn.addEventListener("click", startRecording);
stopRecordBtn.addEventListener("click", stopRecording);
refreshHistoryBtn.addEventListener("click", loadHistory);
clearHistoryBtn.addEventListener("click", clearHistory);
historySort.addEventListener("change", loadHistory);

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragover");
  setFile(event.dataTransfer.files[0]);
});

setInterval(() => {
  if (authToken && !pages.history.classList.contains("hidden")) {
    loadHistory();
  }
}, 15000);

if (authToken && currentUsername) {
  showDashboard();
} else {
  showAuth();
}
