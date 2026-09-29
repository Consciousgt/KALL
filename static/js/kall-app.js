/**
 * kall-app.js
 * Unified Controller for KALL Classified Security Portal.
 * Connects all areas: 3D Portal Scanner, Mobile & CCTV AR Fusion, Standoff Radar, and Physics Inversion.
 * Automatically adapts between GitHub Pages (standalone client-side) and Local Python Backend.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Initialize Core Subsystems
  const audio = window.tacticalAudio;
  const viewer3d = new window.HolographicVolumeViewer("canvas-3d");
  const radarViewer = new window.RadarHeatmapViewer("canvas-mip");
  const rangePlotter = new window.RangeProfilePlotter("canvas-range-profile");

  // Initialize New Modules: AR Camera & Standoff CCTV Tracker
  const arCamera = new window.TacticalCameraAR("ar-video-feed", "ar-canvas-overlay");
  arCamera.render(); // Start overlay render loop

  const cctvTracker = new window.StandoffPerimeterTracker("canvas-cctv-tracker");

  // State
  let currentScenario = "alpha";
  let currentMode = "fast";
  let lastScanData = null;
  let isScanning = false;
  let backendAvailable = false;

  // DOM Elements - Navigation Tabs
  const navTabs = document.querySelectorAll(".nav-tab-btn");
  const tabViews = document.querySelectorAll(".tab-content-view");

  // DOM Elements - General HUD
  const zuluClock = document.getElementById("zulu-clock");
  const localClock = document.getElementById("local-clock");
  const defconBadge = document.getElementById("defcon-badge");
  const backendStatusText = document.getElementById("backend-status-text");

  // DOM Elements - Portal Scanner
  const btnScan = document.getElementById("btn-scan-trigger");
  const btnMute = document.getElementById("btn-mute-toggle");
  const btnScanlines = document.getElementById("btn-scanlines-toggle");
  const btnAutoRotate = document.getElementById("btn-auto-rotate");
  const btnResetView = document.getElementById("btn-reset-view");
  const btnCompareToggle = document.getElementById("btn-compare-toggle");
  const btnExportDossier = document.getElementById("btn-export-dossier");
  const btnCloseDossier = document.getElementById("btn-close-dossier");
  const btnPrintDossier = document.getElementById("btn-print-dossier");
  const modalDossier = document.getElementById("modal-dossier");

  const sliderSlice = document.getElementById("slider-slice-z");
  const labelSliceZ = document.getElementById("label-slice-z");
  const sliderThresh = document.getElementById("slider-thresh");
  const labelThresh = document.getElementById("label-thresh");
  const selectColormap = document.getElementById("select-colormap");

  // Telemetry DOM
  const verdictBox = document.getElementById("verdict-box");
  const verdictBadge = document.getElementById("verdict-status-badge");
  const verdictCategory = document.getElementById("verdict-category");
  const gaugeFill = document.getElementById("gauge-threat-fill");
  const gaugePercent = document.getElementById("gauge-threat-percent");
  const telemCoords = document.getElementById("telem-coords");
  const telemRcs = document.getElementById("telem-rcs");
  const telemDz = document.getElementById("telem-dz");
  const telemTiming = document.getElementById("telem-timing");
  const scanIdDisplay = document.getElementById("scan-id-display");
  const sigHashDisplay = document.getElementById("sig-hash-display");

  // DOM Elements - AR Camera
  const btnToggleCam = document.getElementById("btn-toggle-cam");
  const btnFlipCam = document.getElementById("btn-flip-cam");
  const btnToggleThreatSim = document.getElementById("btn-toggle-threat-sim");
  const btnCamSnapshot = document.getElementById("btn-cam-snapshot");

  // DOM Elements - CCTV Tracker
  const btnCctvPause = document.getElementById("btn-cctv-pause");
  const btnCctvWeapon = document.getElementById("btn-cctv-weapon");
  const btnCctvReset = document.getElementById("btn-cctv-reset");
  const cctvAlarmText = document.getElementById("cctv-alarm-text");

  // In-memory client audit ledger for GitHub Pages
  let clientAuditLog = [
    {
      scan_id: "KALL-INIT-001",
      timestamp: new Date().toISOString().replace("T", " ").substring(0, 19) + " UTC",
      threat_detected: false,
      threat_category: "PERMITTED CLEARANCE",
      peak_coords_cm: [0.0, 0.0, 50.0],
      peak_rcs_db: -28.4,
      signature_hash: "00B4C83F992147E1",
    }
  ];

  // 1. Navigation Tab Switching
  navTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      navTabs.forEach((t) => t.classList.remove("active"));
      tabViews.forEach((v) => v.classList.remove("active"));

      tab.classList.add("active");
      const targetId = `view-${tab.dataset.tab}`;
      const targetView = document.getElementById(targetId);
      if (targetView) targetView.classList.add("active");

      audio.playClick();

      // Trigger resize for newly active views
      if (tab.dataset.tab === "portal") {
        viewer3d.resize();
        radarViewer.render();
        rangePlotter.render();
      } else if (tab.dataset.tab === "camera") {
        arCamera.resize();
      } else if (tab.dataset.tab === "cctv") {
        cctvTracker.resize();
      }
    });
  });

  // 2. Clock Updates
  function updateClocks() {
    const now = new Date();
    const utcHours = String(now.getUTCHours()).padStart(2, "0");
    const utcMins = String(now.getUTCMinutes()).padStart(2, "0");
    const utcSecs = String(now.getUTCSeconds()).padStart(2, "0");
    zuluClock.textContent = `${utcHours}:${utcMins}:${utcSecs} ZULU`;

    const locHours = String(now.getHours()).padStart(2, "0");
    const locMins = String(now.getMinutes()).padStart(2, "0");
    const locSecs = String(now.getSeconds()).padStart(2, "0");
    localClock.textContent = `${locHours}:${locMins}:${locSecs} LOC`;
  }
  setInterval(updateClocks, 1000);
  updateClocks();

  // 3. Backend Detection Probe (GitHub Pages vs Local Server)
  async function probeBackend() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1200);
      const resp = await fetch("/api/status", { cache: "no-store", signal: controller.signal });
      clearTimeout(timeoutId);
      if (resp.ok) {
        backendAvailable = true;
        backendStatusText.textContent = "LIVE PHYSICS ENGINE [CONNECTED]";
        backendStatusText.style.color = "var(--color-green)";
        const modeBadge = document.getElementById("engine-mode-badge");
        if (modeBadge) {
          modeBadge.textContent = "LIVE 3-D IFFT & PYTORCH ENGINE";
          modeBadge.className = "engine-badge live";
        }
        return;
      }
    } catch (e) {
      // Backend not running (GitHub Pages static host)
    }
    backendAvailable = false;
    backendStatusText.textContent = "ILLUSTRATIVE DEMO MODE [CALIBRATED DATASTORE]";
    backendStatusText.style.color = "var(--color-cyan)";
    const modeBadge = document.getElementById("engine-mode-badge");
    if (modeBadge) {
      modeBadge.textContent = "ILLUSTRATIVE DEMO MODE (OFFLINE CALIBRATED DATASTORE)";
      modeBadge.className = "engine-badge demo";
    }
  }

  // 4. Scenario Selector Buttons
  const scenarioButtons = document.querySelectorAll(".scenario-btn");
  scenarioButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      scenarioButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentScenario = btn.dataset.scenario;
      audio.playClick();
      executeScan();
    });
  });

  // 5. Scan Mode Selector
  const modeRadios = document.querySelectorAll("input[name='scan-mode']");
  modeRadios.forEach((r) => {
    r.addEventListener("change", (e) => {
      currentMode = e.target.value;
      audio.playClick();
    });
  });

  // 6. Scan Execution (Hybrid: Backend API or Client-Side Physics)
  btnScan.addEventListener("click", () => {
    audio.playClick();
    executeScan();
  });

  async function executeScan() {
    if (isScanning) return;
    isScanning = true;
    btnScan.disabled = true;
    btnScan.innerHTML = `<span class="banner-pulse"></span> PROCESSING HOLOGRAPHIC INVERSION...`;
    audio.playScannerHum(0.7);

    let data = null;

    if (backendAvailable) {
      try {
        const response = await fetch("/api/scan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            scenario: currentScenario,
            mode: currentMode,
            focus_depth: 0.25,
            noise_level: 0.01,
          }),
        });
        if (response.ok) {
          data = await response.json();
        }
      } catch (err) {
        console.warn("Backend scan failed, using client engine:", err);
      }
    }

    // Fallback to standalone client-side physics datastore
    if (!data && window.KALL_STANDALONE_DATA) {
      // Simulate sub-second calculation
      await new Promise(r => setTimeout(r, currentMode === "fast" ? 320 : 650));
      data = window.KALL_STANDALONE_DATA.runClientScan(currentScenario);
    }

    if (data) {
      lastScanData = data;
      renderScanResults(data);

      // Play audio verdict
      if (data.threat_assessment.is_threat) {
        audio.playThreatAlarm();
      } else {
        audio.playClearChirp();
      }
    }

    isScanning = false;
    btnScan.disabled = false;
    btnScan.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg><span>START RADAR SCAN</span>`;
  }

  function renderScanResults(data) {
    scanIdDisplay.textContent = data.scan_id;
    sigHashDisplay.textContent = data.signature_hash;

    const coords = data.physics_metrics.peak_location_cm;
    telemCoords.textContent = `[X: ${coords.x.toFixed(1)}, Y: ${coords.y.toFixed(1)}, Z: ${coords.z.toFixed(1)} cm]`;
    telemRcs.textContent = `${data.physics_metrics.peak_rcs_db} dBsm`;
    telemDz.textContent = `${data.physics_metrics.measured_fwhm_cm.toFixed(2)} cm (δz: ${data.physics_metrics.theoretical_dz_cm} cm)`;
    telemTiming.textContent = `Recon: ${data.timing_s.recon_wideband}s | AI: ${(data.timing_s.ai_inference * 1000).toFixed(1)}ms`;

    const threat = data.threat_assessment;
    gaugePercent.textContent = `${threat.threat_percentage}%`;
    gaugeFill.style.width = `${threat.threat_percentage}%`;

    if (threat.is_threat) {
      verdictBox.className = "threat-verdict-box threat-active";
      verdictBadge.className = "verdict-status-badge verdict-threat-badge";
      verdictBadge.textContent = "THREAT DETECTED";
      verdictCategory.textContent = threat.threat_category;
      gaugeFill.className = "gauge-fill fill-red";
      defconBadge.textContent = "ALERT";
      defconBadge.style.background = "rgba(255, 42, 75, 0.2)";
      defconBadge.style.borderColor = "var(--color-red)";
      defconBadge.style.color = "var(--color-red)";
    } else {
      verdictBox.className = "threat-verdict-box threat-clear";
      verdictBadge.className = "verdict-status-badge verdict-clear-badge";
      verdictBadge.textContent = "ALL CLEAR / AUTHORIZED";
      verdictCategory.textContent = threat.threat_category;
      gaugeFill.className = "gauge-fill fill-green";
      defconBadge.textContent = "CLEAR";
      defconBadge.style.background = "rgba(0, 255, 136, 0.15)";
      defconBadge.style.borderColor = "var(--color-green)";
      defconBadge.style.color = "var(--color-green)";
    }

    // 3-D Holographic Viewer with Signature Volumetric Reveal
    const peakObj = threat.is_threat ? { x: coords.x, y: coords.y, z: coords.z } : null;
    viewer3d.triggerScanReveal(data.voxels_3d, peakObj);
    viewer3d.setSliceDepth(coords.z || 50.0);
    sliderSlice.value = coords.z || 50.0;
    labelSliceZ.textContent = `${(coords.z || 50.0).toFixed(1)} cm`;

    // 2-D Radar Heatmap
    radarViewer.setData(
      data.mip_wideband,
      data.x_axis_cm,
      data.y_axis_cm,
      threat.is_threat ? { x: coords.x, y: coords.y } : null,
      data.mip_single_freq
    );

    // Range Profile
    rangePlotter.setData(
      data.range_profile.z_cm,
      data.range_profile.profile_norm,
      data.physics_metrics.measured_fwhm_cm,
      data.physics_metrics.theoretical_dz_cm
    );

    // Sync AR camera threat state
    arCamera.setThreatStatus(threat.is_threat, { x: 0.52, y: 0.58 });

    // Append to audit log
    recordAuditEntry({
      scan_id: data.scan_id,
      timestamp: data.timestamp,
      threat_detected: threat.is_threat,
      threat_category: threat.threat_category,
      peak_coords_cm: [coords.x, coords.y, coords.z],
      peak_rcs_db: data.physics_metrics.peak_rcs_db,
      signature_hash: data.signature_hash,
    });
  }

  // 7. Audit Log Management
  async function recordAuditEntry(entry) {
    clientAuditLog.unshift(entry);
    if (clientAuditLog.length > 50) clientAuditLog.pop();
    renderAuditTable(clientAuditLog);

    if (backendAvailable) {
      try {
        await fetch("/api/audit-log", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(entry),
        });
      } catch (e) {}
    }
  }

  function renderAuditTable(list) {
    const tbody = document.getElementById("audit-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    list.slice(0, 10).forEach((entry) => {
      const tr = document.createElement("tr");
      const threatBadge = entry.threat_detected
        ? `<span class="scenario-tag tag-critical">THREAT</span>`
        : `<span class="scenario-tag tag-clear">CLEARED</span>`;

      tr.innerHTML = `
        <td><strong>${entry.scan_id}</strong></td>
        <td>${entry.timestamp}</td>
        <td>${threatBadge}</td>
        <td>${entry.threat_category}</td>
        <td>${entry.peak_coords_cm ? `[${entry.peak_coords_cm.join(", ")} cm]` : "N/A"}</td>
        <td>${entry.peak_rcs_db} dB</td>
        <td><code style="color:var(--color-cyan);">${entry.signature_hash || "SEC-VERIFIED"}</code></td>
      `;
      tbody.appendChild(tr);
    });
  }

  // 8. Interactive Sliders & View Controls
  sliderSlice.addEventListener("input", (e) => {
    const val = parseFloat(e.target.value);
    labelSliceZ.textContent = `${val.toFixed(1)} cm`;
    viewer3d.setSliceDepth(val);
  });

  sliderThresh.addEventListener("input", (e) => {
    const val = parseFloat(e.target.value);
    labelThresh.textContent = `${(val * 100).toFixed(0)}%`;
    viewer3d.setThreshold(val);
  });

  selectColormap.addEventListener("change", (e) => {
    radarViewer.setColormap(e.target.value);
    audio.playClick();
  });

  btnCompareToggle.addEventListener("click", () => {
    audio.playClick();
    radarViewer.showComparison = !radarViewer.showComparison;
    btnCompareToggle.classList.toggle("active", radarViewer.showComparison);
    btnCompareToggle.textContent = radarViewer.showComparison
      ? "MODE: SINGLE-FREQ (BLURRED)"
      : "MODE: WIDEBAND 3-D (SHARP)";
    radarViewer.render();
  });

  btnAutoRotate.addEventListener("click", () => {
    audio.playClick();
    const active = viewer3d.toggleAutoRotate();
    btnAutoRotate.classList.toggle("active", active);
  });

  btnResetView.addEventListener("click", () => {
    audio.playClick();
    viewer3d.resetView();
  });

  btnMute.addEventListener("click", () => {
    const isMuted = audio.toggleMute();
    btnMute.classList.toggle("active", isMuted);
    btnMute.textContent = isMuted ? "AUDIO: OFF" : "AUDIO: ACTIVE";
    if (!isMuted) audio.playRadarPing();
  });

  if (btnScanlines) {
    btnScanlines.addEventListener("click", () => {
      audio.playClick();
      const hasScanlines = document.body.classList.toggle("with-scanlines");
      btnScanlines.classList.toggle("active", hasScanlines);
      btnScanlines.textContent = hasScanlines ? "SCANLINES: ON" : "SCANLINES: OFF";
    });
  }

  // 9. Mobile & CCTV AR Camera Controls
  btnToggleCam.addEventListener("click", async () => {
    audio.playClick();
    const active = await arCamera.startCamera();
    btnToggleCam.classList.toggle("active", active);
    btnToggleCam.textContent = active ? "CAMERA STREAM: ACTIVE" : "CAMERA: SIMULATED FEED";
  });

  btnFlipCam.addEventListener("click", () => {
    audio.playClick();
    arCamera.switchCamera();
  });

  btnToggleThreatSim.addEventListener("click", () => {
    audio.playClick();
    const newThreat = !arCamera.threatDetected;
    arCamera.setThreatStatus(newThreat);
    btnToggleThreatSim.classList.toggle("active", newThreat);
    if (newThreat) audio.playThreatAlarm();
    else audio.playClearChirp();
  });

  btnCamSnapshot.addEventListener("click", () => {
    audio.playRadarPing();
    const snap = arCamera.captureSnapshot();
    recordAuditEntry({
      scan_id: `KALL-AR-${Math.floor(Math.random() * 90000 + 10000)}`,
      timestamp: new Date().toISOString().replace("T", " ").substring(0, 19) + " UTC",
      threat_detected: arCamera.threatDetected,
      threat_category: arCamera.threatDetected ? "CLASS-I: OPTICAL-RADAR FUSION WEAPON" : "PERMITTED VIP (CLEAN)",
      peak_coords_cm: [5.2, -1.8, 48.0],
      peak_rcs_db: arCamera.threatDetected ? -11.8 : -32.0,
      signature_hash: "AR-SNAP-AUTH",
    });
    alert("Tactical Snapshot captured and added to Classified Dossier Ledger.");
  });

  // 10. CCTV Perimeter Tracker Controls
  btnCctvPause.addEventListener("click", () => {
    audio.playClick();
    const playing = cctvTracker.togglePlay();
    btnCctvPause.classList.toggle("active", !playing);
    btnCctvPause.textContent = playing ? "PAUSE SIMULATION" : "RESUME SIMULATION";
  });

  btnCctvWeapon.addEventListener("click", () => {
    audio.playClick();
    const newWpn = !cctvTracker.hasWeapon;
    cctvTracker.setWeapon(newWpn);
    btnCctvWeapon.classList.toggle("active", newWpn);
    cctvAlarmText.textContent = newWpn ? "ARMED SUBJECT TRACKED" : "CLEARED SUBJECT TRACKED";
    cctvAlarmText.style.color = newWpn ? "var(--color-red)" : "var(--color-green)";
  });

  btnCctvReset.addEventListener("click", () => {
    audio.playClick();
    cctvTracker.reset();
  });

  // 11. Dossier Modal
  btnExportDossier.addEventListener("click", () => {
    audio.playRadarPing();
    if (!lastScanData) {
      alert("Please execute a radar scan first.");
      return;
    }
    populateDossier(lastScanData);
    modalDossier.classList.add("open");
  });

  btnCloseDossier.addEventListener("click", () => {
    audio.playClick();
    modalDossier.classList.remove("open");
  });

  btnPrintDossier.addEventListener("click", () => {
    window.print();
  });

  function populateDossier(data) {
    document.getElementById("dossier-scan-id").textContent = data.scan_id;
    document.getElementById("dossier-timestamp").textContent = data.timestamp;
    document.getElementById("dossier-scenario").textContent = data.scenario_name;
    document.getElementById("dossier-hash").textContent = data.signature_hash;

    const threat = data.threat_assessment;
    const badge = document.getElementById("dossier-verdict-badge");
    badge.textContent = threat.is_threat ? "CRITICAL THREAT DETECTED" : "SECURITY CLEARANCE VERIFIED";
    badge.className = threat.is_threat ? "scenario-tag tag-critical" : "scenario-tag tag-clear";

    document.getElementById("dossier-category").textContent = threat.threat_category;
    document.getElementById("dossier-prob").textContent = `${threat.threat_percentage}%`;
    document.getElementById("dossier-coords").textContent = `X: ${data.physics_metrics.peak_location_cm.x} cm, Y: ${data.physics_metrics.peak_location_cm.y} cm, Z: ${data.physics_metrics.peak_location_cm.z} cm`;
    document.getElementById("dossier-rcs").textContent = `${data.physics_metrics.peak_rcs_db} dBsm`;
    document.getElementById("dossier-fwhm").textContent = `${data.physics_metrics.measured_fwhm_cm} cm (Rayleigh Theory: ${data.physics_metrics.theoretical_dz_cm} cm)`;
  }

  // Initial Boot Sequence
  probeBackend().then(() => {
    executeScan();
    renderAuditTable(clientAuditLog);
  });
});
