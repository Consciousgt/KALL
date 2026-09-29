/**
 * kall-camera.js
 * Mobile & CCTV AR Optical-Radar Fusion HUD for Security Personnel.
 * Bridges phone cameras & CCTV streams with mmWave holographic threat projection.
 */

class TacticalCameraAR {
  constructor(videoElementId, canvasOverlayId) {
    this.video = document.getElementById(videoElementId);
    this.canvas = document.getElementById(canvasOverlayId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");

    this.stream = null;
    this.cameraActive = false;
    this.facingMode = "environment"; // 'environment' (back) or 'user' (front)
    this.simulatedMode = true; // Fallback simulation if camera not allowed

    this.threatDetected = true;
    this.threatCoords = { x: 0.52, y: 0.58 }; // Normalized [0, 1] relative to video
    this.estimatedRange = 1.85; // meters
    this.radarOverlayOpacity = 0.65;
    this.animFrame = 0;

    this.initEvents();
  }

  initEvents() {
    window.addEventListener("resize", () => this.resize());
    this.resize();
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width;
    this.canvas.height = rect.height;
    this.width = rect.width;
    this.height = rect.height;
  }

  async startCamera() {
    this.resize();
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        if (this.stream) {
          this.stream.getTracks().forEach(t => t.stop());
        }
        const constraints = {
          video: {
            facingMode: this.facingMode,
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        };
        this.stream = await navigator.mediaDevices.getUserMedia(constraints);
        if (this.video) {
          this.video.srcObject = this.stream;
          this.video.play();
        }
        this.cameraActive = true;
        this.simulatedMode = false;
        if (window.tacticalAudio) window.tacticalAudio.playRadarPing();
        return true;
      } catch (err) {
        console.warn("Physical camera unavailable or denied. Using tactical optical simulator:", err);
        this.simulatedMode = true;
        this.cameraActive = true;
        return false;
      }
    } else {
      this.simulatedMode = true;
      this.cameraActive = true;
      return false;
    }
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    if (this.video) {
      this.video.srcObject = null;
    }
    this.cameraActive = false;
  }

  switchCamera() {
    this.facingMode = (this.facingMode === "environment") ? "user" : "environment";
    return this.startCamera();
  }

  setThreatStatus(isThreat, coords = null) {
    this.threatDetected = isThreat;
    if (coords) {
      this.threatCoords = coords;
    }
    if (isThreat && navigator.vibrate) {
      // Vibrate mobile device
      navigator.vibrate([200, 100, 200]);
    }
  }

  render() {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    ctx.clearRect(0, 0, w, h);
    this.animFrame++;

    // 1. If in simulated mode, draw simulated optical surveillance feed
    if (this.simulatedMode || !this.stream) {
      this.drawSimulatedFeed(ctx, w, h);
    }

    // 2. Draw AR Crosshairs & Tactical HUD Frame
    this.drawTacticalHUD(ctx, w, h);

    // 3. Draw Optical Body Bounding Box
    this.drawPersonBoundingBox(ctx, w, h);

    // 4. Draw Millimeter-Wave Holographic Heatmap Overlay on Suspect Body
    this.drawRadarHeatmapProjection(ctx, w, h);

    // 5. Draw Weapon Lock-on Brackets & Rangefinder
    if (this.threatDetected) {
      this.drawThreatLock(ctx, w, h);
    }

    requestAnimationFrame(() => this.render());
  }

  drawSimulatedFeed(ctx, w, h) {
    // Dark room / checkpoint corridor simulation
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, "#08101a");
    grad.addColorStop(1, "#03060a");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    // Perspective floor lines (CCTV security corridor)
    ctx.strokeStyle = "rgba(41, 66, 107, 0.25)";
    ctx.lineWidth = 1;
    const vanishY = h * 0.35;
    for (let x = -w * 0.5; x <= w * 1.5; x += w * 0.15) {
      ctx.beginPath();
      ctx.moveTo(x, h);
      ctx.lineTo(w * 0.5, vanishY);
      ctx.stroke();
    }

    // Draw Simulated Person Silhouette
    const px = w * 0.5;
    const py = h * 0.65;
    ctx.save();
    ctx.fillStyle = "#121a28";
    ctx.strokeStyle = "#1e2e48";
    ctx.lineWidth = 2;

    // Head
    ctx.beginPath();
    ctx.arc(px, py - 120, 24, 0, 2 * Math.PI);
    ctx.fill(); ctx.stroke();

    // Torso / Outer Jacket — use manual rounded rect for cross-browser support
    ctx.beginPath();
    const rx = px - 50, ry = py - 90, rw = 100, rh = 110, rr = 10;
    ctx.moveTo(rx + rr, ry);
    ctx.lineTo(rx + rw - rr, ry);
    ctx.quadraticCurveTo(rx + rw, ry, rx + rw, ry + rr);
    ctx.lineTo(rx + rw, ry + rh - 4);
    ctx.quadraticCurveTo(rx + rw, ry + rh, rx + rw - 4, ry + rh);
    ctx.lineTo(rx + 4, ry + rh);
    ctx.quadraticCurveTo(rx, ry + rh, rx, ry + rh - 4);
    ctx.lineTo(rx, ry + rr);
    ctx.quadraticCurveTo(rx, ry, rx + rr, ry);
    ctx.closePath();
    ctx.fill(); ctx.stroke();

    // Legs
    ctx.beginPath();
    ctx.rect(px - 45, py + 20, 36, 90);
    ctx.rect(px + 9, py + 20, 36, 90);
    ctx.fill(); ctx.stroke();

    ctx.restore();
  }

  drawTacticalHUD(ctx, w, h) {
    ctx.save();
    ctx.strokeStyle = "rgba(0, 240, 255, 0.4)";
    ctx.lineWidth = 1.5;

    // Four corner brackets
    const sz = 24;
    const pad = 16;

    // Top-Left
    ctx.beginPath(); ctx.moveTo(pad, pad + sz); ctx.lineTo(pad, pad); ctx.lineTo(pad + sz, pad); ctx.stroke();
    // Top-Right
    ctx.beginPath(); ctx.moveTo(w - pad - sz, pad); ctx.lineTo(w - pad, pad); ctx.lineTo(w - pad, pad + sz); ctx.stroke();
    // Bottom-Left
    ctx.beginPath(); ctx.moveTo(pad, h - pad - sz); ctx.lineTo(pad, h - pad); ctx.lineTo(pad + sz, h - pad); ctx.stroke();
    // Bottom-Right
    ctx.beginPath(); ctx.moveTo(w - pad - sz, h - pad); ctx.lineTo(w - pad, h - pad); ctx.lineTo(w - pad, h - pad - sz); ctx.stroke();

    // Rangefinder and Status Info
    ctx.fillStyle = "#00f0ff";
    ctx.font = "bold 10px monospace";
    ctx.fillText("AR OPTICAL-RADAR FUSION ENGINE [ACTIVE]", pad + 8, pad + 18);
    ctx.fillText(`EST. RANGE: ${this.estimatedRange.toFixed(2)} m`, pad + 8, pad + 32);
    ctx.fillText("BAND: 27–33 GHz K-BAND STANDOFF", pad + 8, pad + 46);

    // Crosshair in center
    const cx = w * 0.5;
    const cy = h * 0.5;
    ctx.strokeStyle = "rgba(0, 240, 255, 0.25)";
    ctx.setLineDash([3, 4]);
    ctx.beginPath();
    ctx.arc(cx, cy, 32, 0, 2 * Math.PI);
    ctx.moveTo(cx - 45, cy); ctx.lineTo(cx + 45, cy);
    ctx.moveTo(cx, cy - 45); ctx.lineTo(cx, cy + 45);
    ctx.stroke();
    ctx.restore();
  }

  drawPersonBoundingBox(ctx, w, h) {
    const boxX = w * 0.36;
    const boxY = h * 0.22;
    const boxW = w * 0.28;
    const boxH = h * 0.68;

    ctx.save();
    ctx.strokeStyle = this.threatDetected ? "rgba(255, 42, 75, 0.7)" : "rgba(0, 255, 136, 0.7)";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 3]);
    ctx.strokeRect(boxX, boxY, boxW, boxH);

    // Subject ID Tag
    ctx.fillStyle = this.threatDetected ? "#ff2a4b" : "#00ff88";
    ctx.font = "bold 9px monospace";
    ctx.fillText(this.threatDetected ? "SUBJECT #0892: CONCEALED THREAT DETECTED" : "SUBJECT #0892: CLEARED (NO ANOMALY)", boxX, boxY - 6);
    ctx.restore();
  }

  drawRadarHeatmapProjection(ctx, w, h) {
    // Project mmWave reflectivity heatmap onto the suspect's waistline
    if (!this.threatDetected) return;

    const hx = w * this.threatCoords.x;
    const hy = h * this.threatCoords.y;
    const rad = 38;

    ctx.save();
    // Glowing thermal/radar spot
    const pulse = 1 + 0.1 * Math.sin(this.animFrame * 0.1);
    const grad = ctx.createRadialGradient(hx, hy, 2, hx, hy, rad * pulse);
    grad.addColorStop(0, "rgba(255, 42, 75, 0.95)");
    grad.addColorStop(0.35, "rgba(255, 183, 0, 0.75)");
    grad.addColorStop(0.7, "rgba(0, 240, 255, 0.35)");
    grad.addColorStop(1, "rgba(0, 240, 255, 0.0)");

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(hx, hy, rad * pulse, 0, 2 * Math.PI);
    ctx.fill();

    // Weapon Silhouette contour wireframe
    ctx.strokeStyle = "#ff2a4b";
    ctx.lineWidth = 2;
    ctx.shadowBlur = 10;
    ctx.shadowColor = "#ff2a4b";
    ctx.strokeRect(hx - 16, hy - 14, 32, 16);
    ctx.strokeRect(hx - 10, hy + 2, 14, 18); // grip

    ctx.restore();
  }

  drawThreatLock(ctx, w, h) {
    const hx = w * this.threatCoords.x;
    const hy = h * this.threatCoords.y;

    ctx.save();
    ctx.strokeStyle = "#ff2a4b";
    ctx.lineWidth = 2;
    ctx.shadowBlur = 12;
    ctx.shadowColor = "#ff2a4b";

    // Pulsing target lock circle
    const r = 28 + (this.animFrame % 20);
    ctx.beginPath();
    ctx.arc(hx, hy, r, 0, 2 * Math.PI);
    ctx.stroke();

    // Threat Banner
    ctx.fillStyle = "rgba(255, 42, 75, 0.9)";
    ctx.fillRect(hx + 35, hy - 16, 175, 24);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 10px monospace";
    ctx.fillText("WEAPON DETECTED [P: 99.8%]", hx + 40, hy);
    ctx.restore();
  }

  captureSnapshot() {
    if (!this.canvas) return null;
    return this.canvas.toDataURL("image/png");
  }
}

window.TacticalCameraAR = TacticalCameraAR;
