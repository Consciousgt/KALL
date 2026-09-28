/**
 * kall-app.js
 * Main Controller for KALL Classified Millimeter-Wave Defense Portal.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Initialize Components
  const audio = window.tacticalAudio;
  const viewer3d = new window.HolographicVolumeViewer("canvas-3d");
  const radarViewer = new window.RadarHeatmapViewer("canvas-mip");
  const rangePlotter = new window.RangeProfilePlotter("canvas-range-profile");

  // State
  let currentScenario = "alpha";
  let currentMode = "fast";
  let lastScanData = null;
  let isScanning = false;

  // DOM Elements
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

  const zuluClock = document.getElementById("zulu-clock");
  const localClock = document.getElementById("local-clock");
  const defconBadge = document.getElementById("defcon-badge");

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

  // 1. Clock Updates
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

  // 2. Scenario Button Selection
  const scenarioButtons = document.querySelectorAll(".scenario-btn");
  scenarioButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      scenarioButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentScenario = btn.dataset.scenario;
      audio.playClick();
      // Auto initiate scan when changing scenario
      executeScan();
    });
  });

  // 3. Scan Mode Selector (Fast vs Precision)
  const modeRadios = document.querySelectorAll("input[name='scan-mode']");
  modeRadios.forEach((r) => {
    r.addEventListener("change", (e) => {
      currentMode = e.target.value;
      audio.playClick();
    });
  });

  // 4. Trigger Scan Execution
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

      if (!response.ok) throw new Error("Scan request failed");
      const data = await response.json();
      lastScanData = data;
      renderScanResults(data);

      // Play audio verdict
      if (data.threat_assessment.is_threat) {
        audio.playThreatAlarm();
      } else {
        audio.playClearChirp();
      }
    } catch (err) {
      console.error("Scan error:", err);
    } finally {
      isScanning = false;
      btnScan.disabled = false;
      btnScan.innerHTML = `<span>INITIATE ACTIVE HOLOGRAPHIC SCAN</span>`;
    }
  }

  function renderScanResults(data) {
    // 1. Telemetry Displays
    scanIdDisplay.textContent = data.scan_id;
    sigHashDisplay.textContent = data.signature_hash;

    const coords = data.physics_metrics.peak_location_cm;
    telemCoords.textContent = `[X: ${coords.x.toFixed(1)}, Y: ${coords.y.toFixed(1)}, Z: ${coords.z.toFixed(1)} cm]`;
    telemRcs.textContent = `${data.physics_metrics.peak_rcs_db} dBsm`;
    telemDz.textContent = `${data.physics_metrics.measured_fwhm_cm.toFixed(2)} cm (δz: ${data.physics_metrics.theoretical_dz_cm} cm)`;
    telemTiming.textContent = `Recon: ${data.timing_s.recon_wideband}s | AI: ${(data.timing_s.ai_inference * 1000).toFixed(1)}ms`;

    // 2. AI Threat Assessment
    const threat = data.threat_assessment;
    gaugePercent.textContent = `${threat.threat_percentage}%`;
    gaugeFill.style.width = `${threat.threat_percentage}%`;

    if (threat.is_threat) {
      verdictBox.className = "threat-verdict-box threat-active";
      verdictBadge.className = "verdict-status-badge verdict-threat-badge";
      verdictBadge.textContent = "CRITICAL THREAT DETECTED";
      verdictCategory.textContent = threat.threat_category;
      gaugeFill.className = "gauge-fill fill-red";
      defconBadge.textContent = "DEFCON 1";
      defconBadge.style.background = "#ff2a4b";
      defconBadge.style.color = "#ffffff";
    } else {
      verdictBox.className = "threat-verdict-box threat-clear";
      verdictBadge.className = "verdict-status-badge verdict-clear-badge";
      verdictBadge.textContent = "STATUS: ALL CLEAR / AUTHORIZED";
      verdictCategory.textContent = threat.threat_category;
      gaugeFill.className = "gauge-fill fill-green";
      defconBadge.textContent = "DEFCON 4";
      defconBadge.style.background = "#00ff88";
      defconBadge.style.color = "#000000";
    }

    // 3. 3-D Holographic Volume Viewer
    const peakObj = threat.is_threat ? { x: coords.x, y: coords.y, z: coords.z } : null;
    viewer3d.setData(data.voxels_3d, peakObj);
    viewer3d.setSliceDepth(coords.z || 50.0);
    sliderSlice.value = coords.z || 50.0;
    labelSliceZ.textContent = `${(coords.z || 50.0).toFixed(1)} cm`;

    // 4. 2-D Radar Heatmap Viewer
    radarViewer.setData(
      data.mip_wideband,
      data.x_axis_cm,
      data.y_axis_cm,
      threat.is_threat ? { x: coords.x, y: coords.y } : null,
      data.mip_single_freq
    );

    // 5. Depth Range Profile Plotter
    rangePlotter.setData(
      data.range_profile.z_cm,
      data.range_profile.profile_norm,
      data.physics_metrics.measured_fwhm_cm,
      data.physics_metrics.theoretical_dz_cm
    );

    // 6. Refresh Audit Log Table
    fetchAuditLog();
  }

  // 5. Audit Log Table Fetcher
  async function fetchAuditLog() {
    try {
      const resp = await fetch("/api/audit-log");
      if (!resp.ok) return;
      const res = await resp.json();
      const tbody = document.getElementById("audit-table-body");
      if (!tbody) return;

      tbody.innerHTML = "";
      res.audit_log.slice(0, 10).forEach((entry) => {
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
    } catch (e) {
      console.warn("Audit log fetch error:", e);
    }
  }

  // 6. Sliders & Interactive Controls
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

  btnScanlines.addEventListener("click", () => {
    audio.playClick();
    document.body.classList.toggle("no-scanlines");
    btnScanlines.classList.toggle("active", !document.body.classList.contains("no-scanlines"));
  });

  // 7. Dossier Modal
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

  // Initial automatic scan execution to populate UI
  executeScan();
  fetchAuditLog();
});
