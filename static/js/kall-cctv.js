/**
 * kall-cctv.js
 * Standoff Moving Target Surveillance & Perimeter Radar Tracker (3–8m range).
 * Simulates overhead CCTV camera & mmWave phased array tracking walking subjects.
 */

class StandoffPerimeterTracker {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");

    this.isPlaying = true;
    this.subjectZ = 7.5; // meters (approaching from 8m to 2m)
    this.subjectX = 0.2; // meters cross-range
    this.speed = 0.025; // m per frame
    this.hasWeapon = true;
    this.alarmTriggered = false;
    this.perimeterThreshold = 5.0; // meters

    this.trajectory = [];
    this.rcsHistory = [];
    this.animFrame = 0;

    this.initEvents();
    this.resize();
    this.animate();
  }

  initEvents() {
    window.addEventListener("resize", () => this.resize());
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement ? this.canvas.parentElement.getBoundingClientRect() : null;
    const w = rect && rect.width > 0 ? rect.width : (this.canvas.width || 640);
    const h = rect && rect.height > 0 ? rect.height : (this.canvas.height || 480);
    this.canvas.width = Math.floor(w);
    this.canvas.height = Math.floor(h);
    this.width = w;
    this.height = h;
  }

  togglePlay() {
    this.isPlaying = !this.isPlaying;
    return this.isPlaying;
  }

  setWeapon(val) {
    this.hasWeapon = val;
  }

  reset() {
    this.subjectZ = 7.8;
    this.subjectX = (Math.random() - 0.5) * 1.5;
    this.trajectory = [];
    this.rcsHistory = [];
    this.alarmTriggered = false;
  }

  update() {
    if (!this.isPlaying) return;
    this.animFrame++;

    // Walk toward sensor
    this.subjectZ -= this.speed;
    this.subjectX += Math.sin(this.animFrame * 0.05) * 0.008;

    // Record trajectory
    this.trajectory.push({ x: this.subjectX, z: this.subjectZ });
    if (this.trajectory.length > 80) this.trajectory.shift();

    // Compute synthetic RCS (dBsm)
    const baseRcs = this.hasWeapon ? -10.0 : -28.0;
    const noise = (Math.random() - 0.5) * 2.5;
    const rcs = baseRcs + noise;
    this.rcsHistory.push(rcs);
    if (this.rcsHistory.length > 50) this.rcsHistory.shift();

    // Check perimeter breach
    if (this.subjectZ <= this.perimeterThreshold && this.hasWeapon && !this.alarmTriggered) {
      this.alarmTriggered = true;
      if (window.tacticalAudio) window.tacticalAudio.playThreatAlarm();
    }

    // Reset when past minimum range
    if (this.subjectZ <= 1.8) {
      this.reset();
    }
  }

  render() {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    ctx.clearRect(0, 0, w, h);

    // 1. Draw Standoff Corridor Grid
    this.drawCorridor(ctx, w, h);

    // 2. Draw 5-Meter Perimeter Warning Line
    this.drawPerimeterBoundary(ctx, w, h);

    // 3. Draw Radar Phased Beam Fan
    this.drawRadarBeam(ctx, w, h);

    // 4. Draw Subject & Trajectory
    this.drawSubject(ctx, w, h);

    // 5. Draw Mini RCS Oscilloscope in corner
    this.drawMiniRCS(ctx, w, h);
  }

  drawCorridor(ctx, w, h) {
    const pad = 30;
    const topY = pad;
    const botY = h - pad;

    ctx.save();
    ctx.strokeStyle = "rgba(41, 66, 107, 0.4)";
    ctx.lineWidth = 1;

    // Range markers from 8m down to 2m
    for (let z = 8; z >= 2; z -= 1) {
      const py = botY - ((z - 2) / 6.0) * (botY - topY);
      ctx.beginPath();
      ctx.moveTo(pad, py); ctx.lineTo(w - pad, py);
      ctx.stroke();

      ctx.fillStyle = "rgba(123, 148, 178, 0.6)";
      ctx.font = "9px monospace";
      ctx.fillText(`${z.toFixed(0)}m RANGE`, pad + 6, py - 4);
    }
    ctx.restore();
  }

  drawPerimeterBoundary(ctx, w, h) {
    const pad = 30;
    const topY = pad;
    const botY = h - pad;
    const py = botY - ((this.perimeterThreshold - 2) / 6.0) * (botY - topY);

    ctx.save();
    ctx.strokeStyle = "rgba(255, 42, 75, 0.8)";
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.moveTo(pad, py); ctx.lineTo(w - pad, py);
    ctx.stroke();

    ctx.fillStyle = "#ff2a4b";
    ctx.font = "bold 9px monospace";
    ctx.fillText("CRITICAL PERIMETER THRESHOLD (5.0 METERS STANDOFF)", pad + 10, py - 6);
    ctx.restore();
  }

  drawRadarBeam(ctx, w, h) {
    const pad = 30;
    const botY = h - pad;
    const cx = w * 0.5;

    // Draw radar head at bottom center
    ctx.save();
    ctx.fillStyle = "#00f0ff";
    ctx.beginPath();
    ctx.arc(cx, botY, 10, 0, 2 * Math.PI);
    ctx.fill();

    // Sweeping fan beam
    const angle = Math.sin(this.animFrame * 0.08) * 0.35;
    const beamLen = h * 0.8;

    const grad = ctx.createRadialGradient(cx, botY, 10, cx, botY, beamLen);
    grad.addColorStop(0, "rgba(0, 240, 255, 0.25)");
    grad.addColorStop(1, "rgba(0, 240, 255, 0.0)");

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(cx, botY);
    ctx.arc(cx, botY, beamLen, -Math.PI / 2 + angle - 0.25, -Math.PI / 2 + angle + 0.25);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  drawSubject(ctx, w, h) {
    const pad = 30;
    const topY = pad;
    const botY = h - pad;

    // Map (x, z) to screen (px, py)
    // x: [-2, 2] -> [pad, w - pad]
    // z: [2, 8] -> [botY, topY]
    const px = (w * 0.5) + (this.subjectX / 2.0) * (w * 0.35);
    const py = botY - ((this.subjectZ - 2) / 6.0) * (botY - topY);

    ctx.save();
    // Trajectory path
    ctx.strokeStyle = "rgba(0, 240, 255, 0.3)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    this.trajectory.forEach((pt, i) => {
      const tx = (w * 0.5) + (pt.x / 2.0) * (w * 0.35);
      const ty = botY - ((pt.z - 2) / 6.0) * (botY - topY);
      if (i === 0) ctx.moveTo(tx, ty);
      else ctx.lineTo(tx, ty);
    });
    ctx.stroke();

    // Subject marker
    const color = this.hasWeapon ? "#ff2a4b" : "#00ff88";
    ctx.fillStyle = color;
    ctx.shadowBlur = 10;
    ctx.shadowColor = color;
    ctx.beginPath();
    ctx.arc(px, py, 7, 0, 2 * Math.PI);
    ctx.fill();

    // Target callout tag
    ctx.fillStyle = color;
    ctx.font = "bold 9px monospace";
    ctx.fillText(
      `SUBJECT [${this.subjectZ.toFixed(2)}m] - ${this.hasWeapon ? "CONCEALED WEAPON" : "CLEARED"}`,
      px + 12,
      py + 3
    );
    ctx.restore();
  }

  drawMiniRCS(ctx, w, h) {
    const boxW = 160;
    const boxH = 65;
    const bx = w - boxW - 20;
    const by = 20;

    ctx.save();
    ctx.fillStyle = "rgba(11, 17, 28, 0.85)";
    ctx.strokeStyle = "rgba(0, 240, 255, 0.3)";
    ctx.lineWidth = 1;
    ctx.fillRect(bx, by, boxW, boxH);
    ctx.strokeRect(bx, by, boxW, boxH);

    ctx.fillStyle = "#00f0ff";
    ctx.font = "8px monospace";
    ctx.fillText("LIVE STANDOFF RCS (dBsm)", bx + 8, by + 12);

    if (this.rcsHistory.length > 1) {
      ctx.strokeStyle = this.hasWeapon ? "#ff2a4b" : "#00ff88";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      const n = this.rcsHistory.length;
      for (let i = 0; i < n; i++) {
        const val = this.rcsHistory[i]; // range [-40, 0]
        const norm = (val + 40) / 40;
        const px = bx + 8 + (i / (n - 1)) * (boxW - 16);
        const py = by + boxH - 8 - norm * (boxH - 24);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();
    }
    ctx.restore();
  }

  animate() {
    this.update();
    this.render();
    requestAnimationFrame(() => this.animate());
  }
}

window.StandoffPerimeterTracker = StandoffPerimeterTracker;
