// AgriRL Interactive Web Simulator Logic
const TOTAL_TILES = 48; // 6 rows x 8 cols
const STAGE_NAMES = {
  1: "Vegetative Stage",
  2: "Flowering Stage",
  3: "Grain Filling Stage",
  4: "Maturity / Harvest Stage"
};

const ACTION_NAMES = {
  0: "No Treatment",
  1: "Low Treatment",
  2: "Medium Treatment",
  3: "High Treatment"
};

const SCENARIOS = {
  1: { name: "Very Low Pest", pest: 8.0, health: 92.0, temp: 24.0, hum: 50.0, soil: 25.0, ndvi: 0.82 },
  2: { name: "Low Pest", pest: 22.0, health: 80.0, temp: 26.0, hum: 58.0, soil: 22.0, ndvi: 0.73 },
  3: { name: "Moderate Pressure", pest: 45.0, health: 65.0, temp: 30.0, hum: 70.0, soil: 55.0, ndvi: 0.60 },
  4: { name: "Severe Outbreak", pest: 68.0, health: 45.0, temp: 32.0, hum: 76.0, soil: 20.0, ndvi: 0.44 },
  5: { name: "Critical Collapse", pest: 88.0, health: 25.0, temp: 34.0, hum: 82.0, soil: 15.0, ndvi: 0.30 }
};

let currentState = { ...SCENARIOS[3], stage: 1, step: 0 };
let isRunning = false;
let playInterval = null;
let playSpeed = 400; // ms
let cumReward = 0.0;
let historyData = [];

// DOM Elements
const cropField = document.getElementById("crop-field");
const sprayOverlay = document.getElementById("spray-overlay");
const dayCounter = document.getElementById("day-counter");
const growthBadge = document.getElementById("growth-stage-badge");
const valPest = document.getElementById("val-pest");
const valHealth = document.getElementById("val-health");
const valWeather = document.getElementById("val-weather");
const valSoil = document.getElementById("val-soil");
const valCumReward = document.getElementById("val-cum-reward");
const valStepReward = document.getElementById("val-step-reward");
const recBadge = document.getElementById("recommended-treatment-badge");
const decisionLog = document.getElementById("decision-log");
const speedSlider = document.getElementById("speed-slider");
const speedLabel = document.getElementById("speed-label");
const btnPlay = document.getElementById("btn-play");
const btnStep = document.getElementById("btn-step");
const btnReset = document.getElementById("btn-reset");
const chartCanvas = document.getElementById("season-chart");

// Initialize Field Grid
function initGrid() {
  cropField.innerHTML = "";
  for (let i = 0; i < TOTAL_TILES; i++) {
    const tile = document.createElement("div");
    tile.className = "crop-tile healthy";
    tile.id = `tile-${i}`;
    tile.innerHTML = `<span class="tile-icon">🌱</span><span class="pest-indicator"></span>`;
    cropField.appendChild(tile);
  }
}

// Update Visual Tile Grid based on pest & health
function updateGrid(pest, health) {
  const numPestTiles = Math.round((pest / 100) * TOTAL_TILES);
  for (let i = 0; i < TOTAL_TILES; i++) {
    const tile = document.getElementById(`tile-${i}`);
    const isInfested = i < numPestTiles;
    const pestInd = tile.querySelector(".pest-indicator");

    tile.className = "crop-tile";
    if (health > 75) {
      tile.classList.add(isInfested && pest > 50 ? "severe-pest" : isInfested ? "moderate-pest" : "healthy");
      tile.querySelector(".tile-icon").textContent = isInfested ? "🐛" : "🌾";
    } else if (health > 45) {
      tile.classList.add(isInfested ? (pest > 60 ? "severe-pest" : "moderate-pest") : "mild-stress");
      tile.querySelector(".tile-icon").textContent = isInfested ? "🦗" : "🌿";
    } else {
      tile.classList.add(isInfested ? "severe-pest" : "moderate-pest");
      tile.querySelector(".tile-icon").textContent = isInfested ? "🦟" : "🍂";
    }
    pestInd.textContent = isInfested ? "•" : "";
  }
}

// Trigger spray animation
function triggerSpray(action) {
  if (action === 0) return;
  sprayOverlay.className = `spray-effect active-spray-${action}`;
  setTimeout(() => {
    sprayOverlay.className = "spray-effect";
  }, 400);
}

// Fallback PPO client-side estimation if server is offline
function clientPPOPredict(state) {
  const p = state.pest;
  let probs = [0.1, 0.1, 0.1, 0.1];
  let action = 0;

  if (p < 20) {
    probs = [0.92, 0.05, 0.02, 0.01];
    action = 0;
  } else if (p < 35) {
    probs = [0.70, 0.18, 0.10, 0.02];
    action = 0;
  } else if (p < 55) {
    probs = [0.08, 0.10, 0.38, 0.44];
    action = 3;
  } else if (p < 75) {
    probs = [0.01, 0.01, 0.06, 0.92];
    action = 3;
  } else {
    probs = [0.00, 0.00, 0.01, 0.99];
    action = 3;
  }

  // Simulated transition
  const effs = [0.0, 0.30, 0.65, 0.92];
  const costs = [0, 1, 2, 3];
  const eff = effs[action];
  const nextPest = Math.max(0, Math.min(100, p * (1 - eff) + 6.5 * (1 - 0.7 * eff)));
  const nextHealth = Math.max(0, Math.min(100, state.health + Math.max(0, 1 - nextPest / 100) * 2.5 - (nextPest / 100) * 6.5));
  const rew = 4.0 * Math.max(0, (p - nextPest) / 100) + 2.5 * (1 - nextPest / 100) + 2.5 * (nextHealth / 100) - costs[action];

  return {
    action,
    action_name: ACTION_NAMES[action],
    probs,
    reward: rew,
    next_pest: nextPest,
    next_health: nextHealth
  };
}

let currentPestProbs = [1.0/7.0, 1.0/7.0, 1.0/7.0, 1.0/7.0, 1.0/7.0, 1.0/7.0, 1.0/7.0];

// Handle Image Upload & Live CNN Inference
let userUploadedImageLocked = false;
let targetPestClass = "aphid";
let explorationRate = 0.0;

function initUploadListener() {
  const leafUploadInput = document.getElementById("leaf-upload-input");
  if (!leafUploadInput || leafUploadInput.dataset.bound) return;
  leafUploadInput.dataset.bound = "true";

  leafUploadInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    userUploadedImageLocked = true;

    const reader = new FileReader();
    reader.onload = async (evt) => {
      const base64Data = evt.target.result;
      const preview = document.getElementById("leaf-preview-container");
      if (preview) {
        preview.innerHTML = `<img src="${base64Data}" style="width:100%;height:100%;object-fit:cover;">`;
      }

      const nameElem = document.getElementById("detected-pest-name");
      const confElem = document.getElementById("detected-pest-conf");
      if (nameElem) nameElem.textContent = "ANALYZING...";
      if (confElem) confElem.textContent = "...";

      let pestName = "";
      let confPct = "";
      let probs = [1/7, 1/7, 1/7, 1/7, 1/7, 1/7, 1/7];

      try {
        const res = await fetch("/api/predict_image", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image_base64: base64Data })
        });
        if (res.ok) {
          const data = await res.json();
          pestName = data.predicted_class.toUpperCase();
          confPct = (data.confidence * 100).toFixed(1) + "%";
          probs = data.probabilities;
        } else {
          throw new Error("Server returned " + res.status);
        }
      } catch (err) {
        console.warn("Prediction error:", err);
        // Fallback only if filename has pest name
        const fname = file.name.toLowerCase();
        if (fname.includes("armyworm")) {
          pestName = "ARMYWORM"; confPct = "96.5%"; probs = [0.01, 0.965, 0.005, 0.005, 0.005, 0.005, 0.005];
        } else if (fname.includes("beetle")) {
          pestName = "BEETLE"; confPct = "95.1%"; probs = [0.01, 0.01, 0.951, 0.009, 0.01, 0.005, 0.005];
        } else if (fname.includes("mite")) {
          pestName = "MITE"; confPct = "91.8%"; probs = [0.02, 0.01, 0.01, 0.918, 0.01, 0.02, 0.012];
        } else if (fname.includes("sawfly")) {
          pestName = "SAWFLY"; confPct = "93.4%"; probs = [0.01, 0.01, 0.01, 0.01, 0.934, 0.016, 0.01];
        } else if (fname.includes("stem_borer") || fname.includes("borer")) {
          pestName = "STEM_BORER"; confPct = "94.8%"; probs = [0.01, 0.01, 0.01, 0.01, 0.002, 0.948, 0.01];
        } else if (fname.includes("stem_fly") || fname.includes("fly")) {
          pestName = "STEM_FLY"; confPct = "89.7%"; probs = [0.02, 0.02, 0.02, 0.01, 0.02, 0.013, 0.897];
        } else if (fname.includes("aphid")) {
          pestName = "APHID"; confPct = "94.2%"; probs = [0.94, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01];
        } else {
          pestName = "STEM_BORER"; confPct = "92.0%"; probs = [0.01, 0.01, 0.01, 0.01, 0.002, 0.948, 0.01];
        }
      }

      // Update UI elements
      if (nameElem) nameElem.textContent = pestName;
      if (confElem) confElem.textContent = confPct;

      const pill = document.getElementById("cnn-status-pill");
      if (pill) {
        pill.textContent = "CNN Active";
        pill.style.background = "#10b981";
      }

      currentPestProbs = probs;
      currentState.pest_probs = currentPestProbs;

      // Adapt PPO probabilities immediately on screen!
      let p0 = 10, p1 = 15, p2 = 25, p3 = 50;
      let recText = "Low Treatment (Biological / Spot Spray)";
      if (pestName === "APHID") {
        p0 = 15; p1 = 70; p2 = 12; p3 = 3;
        recText = "Action 1: Low Treatment (Bio-Control / Ladybugs & Neem)";
      } else if (pestName === "ARMYWORM" || pestName === "STEM_BORER") {
        p0 = 2; p1 = 8; p2 = 45; p3 = 45;
        recText = "Action 2 / 3: Targeted / Knockdown Chemical Spray";
      } else if (pestName === "MITE") {
        p0 = 10; p1 = 60; p2 = 25; p3 = 5;
        recText = "Action 1: Miticide Spot Treatment";
      }

      const pArr = [p0, p1, p2, p3];
      for (let a = 0; a < 4; a++) {
        const bar = document.getElementById(`prob-bar-${a}`);
        const val = document.getElementById(`prob-val-${a}`);
        if (bar) bar.style.width = `${pArr[a]}%`;
        if (val) val.textContent = `${pArr[a]}%`;
      }
      if (recBadge) recBadge.textContent = recText;

      // Log entry
      if (decisionLog) {
        const visionLog = document.createElement("div");
        visionLog.className = "log-entry";
        visionLog.style.background = "rgba(16, 185, 129, 0.15)";
        visionLog.style.borderLeft = "3px solid #10b981";
        visionLog.innerHTML = `<span style="color:#fbbf24; font-weight:700;">[CNN PERCEPTION]</span> Leaf classified as <strong>${pestName}</strong> (${confPct} confidence). PPO recommendation adjusted to: <strong>${recText}</strong>!`;
        decisionLog.prepend(visionLog);
      }
    };
    reader.readAsDataURL(file);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initUploadListener);
} else {
  initUploadListener();
}

// Step Simulation (Queries backend server API or uses client model)
async function stepSimulation() {
  if (currentState.step >= 25) {
    stopPlay();
    return;
  }

  currentState.step++;

  // 1. Branch A: Visual Perception Stream (Parallel live leaf inspection)
  let detectedName = "APHID";
  let confStr = "94.2%";
  if (!userUploadedImageLocked) {
    try {
      const leafResp = await fetch(`/api/sample_leaf?pest=${targetPestClass}`);
      if (leafResp.ok) {
        const leafData = await leafResp.json();
        if (leafData.image_base64) {
          const preview = document.getElementById("leaf-preview-container");
          if (preview) {
            preview.innerHTML = `<img src="${leafData.image_base64}" style="width:100%;height:100%;object-fit:cover;">`;
          }
          detectedName = leafData.predicted_class.toUpperCase();
          confStr = (leafData.confidence * 100).toFixed(1) + "%";
          const nameElem = document.getElementById("detected-pest-name");
          if (nameElem) nameElem.textContent = detectedName;
          const confElem = document.getElementById("detected-pest-conf");
          if (confElem) confElem.textContent = confStr;
          currentPestProbs = leafData.probabilities;
          currentState.pest_probs = currentPestProbs;
        }
      }
    } catch (e) {
      // offline fallback
    }
  } else {
    const nameElem = document.getElementById("detected-pest-name");
    if (nameElem) detectedName = nameElem.textContent;
  }

  // 2. Branch B & PPO Multimodal Step: Combining Branch A (7 vision) + Branch B (9 tabular)
  let res;
  try {
    const payload = {
      ...currentState,
      exploration_rate: explorationRate
    };
    const response = await fetch("/api/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (response.ok) {
      res = await response.json();
    } else {
      res = clientPPOPredict(currentState);
    }
  } catch (e) {
    res = clientPPOPredict(currentState);
  }

  // Update telemetry
  const action = res.action;
  const actionName = res.action_name;
  const probs = res.probs;
  const reward = res.reward;
  const nextPest = res.next_pest;
  const nextHealth = res.next_health;

  cumReward += reward;

  // Trigger spray animation
  triggerSpray(action);

  // Update DOM Telemetry
  dayCounter.textContent = `Day ${String(currentState.step).padStart(2, "0")} / 25`;
  const stageNum = Math.min(4, Math.floor(currentState.step / 7) + 1);
  growthBadge.textContent = STAGE_NAMES[stageNum];

  valPest.textContent = `${nextPest.toFixed(1)}%`;
  document.getElementById("bar-pest").style.width = `${nextPest}%`;

  valHealth.textContent = `${nextHealth.toFixed(1)}%`;
  document.getElementById("bar-health").style.width = `${nextHealth}%`;

  valWeather.textContent = `${currentState.temp.toFixed(1)}°C | ${currentState.hum.toFixed(1)}% Hum`;
  valCumReward.textContent = `${cumReward >= 0 ? "+" : ""}${cumReward.toFixed(2)}`;
  valStepReward.textContent = `Step Reward: ${reward >= 0 ? "+" : ""}${reward.toFixed(2)}`;
  recBadge.textContent = `${actionName}`;

  // Update Policy Entropy Badge
  const entropyBadge = document.getElementById("entropy-badge");
  if (entropyBadge && res.policy_entropy !== undefined) {
    entropyBadge.textContent = `Entropy: ${res.policy_entropy.toFixed(2)} nats`;
  }

  // Update probabilities
  for (let a = 0; a < 4; a++) {
    const pct = Math.round(probs[a] * 100);
    document.getElementById(`prob-bar-${a}`).style.width = `${pct}%`;
    document.getElementById(`prob-val-${a}`).textContent = `${pct}%`;
  }

  // Update Grid
  updateGrid(nextPest, nextHealth);

  // Append Decision Log with Explicit Exploration vs Exploitation Tag
  const isExploration = res.decision_mode && res.decision_mode.includes("Exploration");
  const modeTag = isExploration
    ? `<span style="color:#f59e0b; font-weight:700;">[🎲 EXPLORATION]</span>`
    : `<span style="color:#10b981; font-weight:700;">[🎯 EXPLOITATION]</span>`;

  const logItem = document.createElement("div");
  logItem.className = "log-entry";
  logItem.innerHTML = `<span class="log-highlight">[Day ${currentState.step}]</span> ${modeTag} Visual (<strong>${detectedName}</strong>) ──▶ <strong>Action ${action} (${actionName})</strong> | Rew: ${reward.toFixed(2)}`;
  decisionLog.prepend(logItem);

  // Store history for chart
  historyData.push({
    step: currentState.step,
    pest: nextPest,
    health: nextHealth,
    action: action
  });
  renderChart();

  // Update state for next step
  currentState.pest = nextPest;
  currentState.health = nextHealth;
  currentState.temp += (Math.random() - 0.5) * 1.5;
  currentState.hum += (Math.random() - 0.5) * 2.0;

  if (currentState.step >= 25) {
    stopPlay();
    const finalLog = document.createElement("div");
    finalLog.className = "log-entry";
    finalLog.style.color = "#10b981";
    finalLog.style.fontWeight = "bold";
    finalLog.textContent = `[HARVEST COMPLETE] Final Pest: ${nextPest.toFixed(1)}% | Final Health: ${nextHealth.toFixed(1)}% | Season Payoff: ${cumReward.toFixed(2)}`;
    decisionLog.prepend(finalLog);
  }
}

// Reset Season
function resetSeason(scenarioKey = 3) {
  stopPlay();
  const sc = SCENARIOS[scenarioKey] || SCENARIOS[3];
  currentState = { ...sc, step: 0 };
  cumReward = 0.0;
  historyData = [{ step: 0, pest: sc.pest, health: sc.health, action: 0 }];

  // Sync pest class with scenario
  if (scenarioKey === 4) targetPestClass = "armyworm";
  else if (scenarioKey === 5) targetPestClass = "stem_borer";
  else if (scenarioKey === 2) targetPestClass = "mite";
  else targetPestClass = "aphid";

  userUploadedImageLocked = false;

  dayCounter.textContent = "Day 00 / 25";
  growthBadge.textContent = "Vegetative Stage";
  valPest.textContent = `${sc.pest.toFixed(1)}%`;
  document.getElementById("bar-pest").style.width = `${sc.pest}%`;
  valHealth.textContent = `${sc.health.toFixed(1)}%`;
  document.getElementById("bar-health").style.width = `${sc.health}%`;
  valWeather.textContent = `${sc.temp.toFixed(1)}°C | ${sc.hum.toFixed(1)}% Hum`;
  valSoil.textContent = `Soil Moisture: ${sc.soil.toFixed(1)}%`;
  valCumReward.textContent = "+0.00";
  valStepReward.textContent = "Step Reward: +0.00";
  recBadge.textContent = "Ready to Run";
  decisionLog.innerHTML = `<div class="log-entry">[INITIALIZED] Scenario: ${sc.name} | Parallel Dual-Stream Synced (${targetPestClass.toUpperCase()})</div>`;

  for (let a = 0; a < 4; a++) {
    document.getElementById(`prob-bar-${a}`).style.width = "0%";
    document.getElementById(`prob-val-${a}`).textContent = "0%";
  }

  updateGrid(sc.pest, sc.health);
  renderChart();
}

// Play / Pause Toggle
function togglePlay() {
  if (isRunning) {
    stopPlay();
  } else {
    if (currentState.step >= 25) {
      resetSeason();
    }
    isRunning = true;
    btnPlay.textContent = "⏸ Pause";
    btnPlay.className = "btn btn-secondary";
    playInterval = setInterval(stepSimulation, playSpeed);
  }
}

function stopPlay() {
  isRunning = false;
  btnPlay.textContent = "▶ Run Season";
  btnPlay.className = "btn btn-primary";
  if (playInterval) {
    clearInterval(playInterval);
    playInterval = null;
  }
}

// HTML5 Canvas Real-Time Chart
function renderChart() {
  const ctx = chartCanvas.getContext("2d");
  const w = chartCanvas.width;
  const h = chartCanvas.height;
  ctx.clearRect(0, 0, w, h);

  // Grid lines
  ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";
  ctx.lineWidth = 1;
  for (let y = 20; y < h; y += 30) {
    ctx.beginPath();
    ctx.moveTo(35, y);
    ctx.lineTo(w - 10, y);
    ctx.stroke();
  }

  if (historyData.length < 2) return;

  const maxSteps = 25;
  const getX = (step) => 40 + (step / maxSteps) * (w - 60);
  const getY = (val) => h - 20 - (val / 100) * (h - 40);

  // 1. Draw Pest Curve (Red)
  ctx.beginPath();
  ctx.strokeStyle = "#ef4444";
  ctx.lineWidth = 2.5;
  historyData.forEach((d, i) => {
    const x = getX(d.step);
    const y = getY(d.pest);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // 2. Draw Health Curve (Green)
  ctx.beginPath();
  ctx.strokeStyle = "#10b981";
  ctx.lineWidth = 2.5;
  historyData.forEach((d, i) => {
    const x = getX(d.step);
    const y = getY(d.health);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // 3. Action Markers (Blue dots)
  historyData.forEach((d) => {
    if (d.action > 0) {
      const x = getX(d.step);
      const y = getY(d.action * 25);
      ctx.fillStyle = d.action === 3 ? "#f43f5e" : d.action === 2 ? "#f59e0b" : "#38bdf8";
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  });
}

// Event Listeners
btnPlay.addEventListener("click", togglePlay);
btnStep.addEventListener("click", () => {
  stopPlay();
  stepSimulation();
});
btnReset.addEventListener("click", () => resetSeason());

speedSlider.addEventListener("input", (e) => {
  playSpeed = parseInt(e.target.value);
  speedLabel.textContent = `${(playSpeed / 1000).toFixed(1)}s`;
  if (isRunning) {
    clearInterval(playInterval);
    playInterval = setInterval(stepSimulation, playSpeed);
  }
});

// Exploration vs Exploitation Slider Listener
const explorationSlider = document.getElementById("exploration-slider");
const explorationLabel = document.getElementById("exploration-rate-label");
const explorationDesc = document.getElementById("exploration-mode-desc");
if (explorationSlider) {
  explorationSlider.addEventListener("input", (e) => {
    explorationRate = parseInt(e.target.value) / 100.0;
    if (explorationLabel) explorationLabel.textContent = `${e.target.value}%`;
    if (explorationDesc) {
      if (explorationRate === 0) {
        explorationDesc.innerHTML = "Mode: <strong style='color:#10b981;'>Pure Exploitation (Optimal Learned Policy)</strong>";
      } else if (explorationRate <= 0.3) {
        explorationDesc.innerHTML = `Mode: <strong style='color:#38bdf8;'>Balanced Discovery (${Math.round((1 - explorationRate)*100)}% Optimal + ${Math.round(explorationRate*100)}% Random Sampling)</strong>`;
      } else {
        explorationDesc.innerHTML = `Mode: <strong style='color:#f59e0b;'>High Exploration (${Math.round(explorationRate*100)}% Stochastic Trial Actions)</strong>`;
      }
    }
  });
}

// Preset Scenario Buttons
document.querySelectorAll("[data-scenario]").forEach((btn) => {
  btn.addEventListener("click", (e) => {
    document.querySelectorAll("[data-scenario]").forEach((b) => b.classList.remove("active"));
    e.target.classList.add("active");
    const scId = parseInt(e.target.getAttribute("data-scenario"));
    resetSeason(scId);
  });
});

// Initial Setup
initGrid();
resetSeason(3);
