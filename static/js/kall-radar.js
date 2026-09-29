/**
 * kall-radar.js
 * 2D Millimeter-Wave Radar Heatmap & Range-Profile Oscilloscope Renderers.
 * 100% Native Canvas2D — Zero external chart libraries required.
 */

class RadarHeatmapViewer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");
    this.colormap = "hot"; // 'hot', 'viridis', 'radar', 'cyber'
    this.matrix = null;
    this.xCoords = [];
    this.yCoords = [];
    this.targetCoords = null; // {x, y} in cm
    this.showComparison = false;
    this.compareMatrix = null;
  }

  setColormap(cmap) {
    this.colormap = cmap;
    this.render();
  }

  setData(matrix, xCoords, yCoords, targetCoords = null, compareMatrix = null) {
    this.matrix = matrix;
    this.xCoords = xCoords || [];
    this.yCoords = yCoords || [];
    this.targetCoords = targetCoords;
    this.compareMatrix = compareMatrix;
    this.render();
  }

  getColor(val) {
    val = Math.max(0, Math.min(1, val));
    if (this.colormap === "hot") {
      // Black -> Red -> Orange -> Yellow -> White
      if (val < 0.33) {
        const t = val / 0.33;
        return [Math.floor(t * 220), 0, 0];
      } else if (val < 0.66) {
        const t = (val - 0.33) / 0.33;
        return [220 + Math.floor(t * 35), Math.floor(t * 180), 0];
      } else {
        const t = (val - 0.66) / 0.34;
        return [255, 180 + Math.floor(t * 75), Math.floor(t * 255)];
      }
    } else if (this.colormap === "radar") {
      // Dark -> Deep Emerald -> Bright Neon Radar Green
      return [
        Math.floor(val * 40),
        Math.floor(val * 255),
        Math.floor(val * 120),
      ];
    } else if (this.colormap === "cyber") {
      // Navy -> Deep Cyan -> Electric Blue -> White
      return [
        Math.floor(val * 140),
        Math.floor(val * 240),
        Math.floor(180 + val * 75),
      ];
    } else {
      // Viridis approximation
      return [
        Math.floor(68 + val * 187),
        Math.floor(1 + val * 230),
        Math.floor(84 + (1 - val) * 120),
      ];
    }
  }

  render() {
    if (!this.ctx || !this.matrix) return;
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    const mat = (this.showComparison && this.compareMatrix) ? this.compareMatrix : this.matrix;
    const nx = mat.length;
    const ny = mat[0].length;

    const cellW = w / nx;
    const cellH = h / ny;

    // Render cells
    for (let ix = 0; ix < nx; ix++) {
      for (let iy = 0; iy < ny; iy++) {
        const val = mat[ix][iy];
        const [r, g, b] = this.getColor(val);
        ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
        // Flip y so positive y is up
        ctx.fillRect(ix * cellW, (ny - 1 - iy) * cellH, cellW + 0.5, cellH + 0.5);
      }
    }

    // Draw Radar Range Rings & Crosshairs
    ctx.save();
    ctx.strokeStyle = "rgba(0, 240, 255, 0.25)";
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 3]);

    const cx = w / 2;
    const cy = h / 2;

    // Crosshairs
    ctx.beginPath();
    ctx.moveTo(cx, 0); ctx.lineTo(cx, h);
    ctx.moveTo(0, cy); ctx.lineTo(w, cy);
    ctx.stroke();

    // Range rings
    [0.2, 0.4, 0.6, 0.8].forEach((scale) => {
      ctx.beginPath();
      ctx.arc(cx, cy, (Math.min(w, h) / 2) * scale, 0, 2 * Math.PI);
      ctx.stroke();
    });

    // Draw Target Acquisition Bounding Crosshair
    if (this.targetCoords) {
      const tx = this.targetCoords.x; // in cm
      const ty = this.targetCoords.y; // in cm

      // Map cm [-20, 20] to [0, w]
      const px = ((tx + 20) / 40) * w;
      const py = h - ((ty + 20) / 40) * h;

      ctx.setLineDash([]);
      ctx.strokeStyle = "#ff2a4b";
      ctx.lineWidth = 2;
      ctx.shadowBlur = 10;
      ctx.shadowColor = "#ff2a4b";

      const sz = 14;
      ctx.strokeRect(px - sz, py - sz, sz * 2, sz * 2);

      ctx.fillStyle = "#ff2a4b";
      ctx.font = "bold 9px monospace";
      ctx.fillText(`TARGET [${tx.toFixed(1)}, ${ty.toFixed(1)}cm]`, px + sz + 4, py - 4);
    }

    ctx.restore();
  }
}


class RangeProfilePlotter {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");
    this.zArr = [];
    this.profile = [];
    this.fwhm_cm = 2.48;
    this.theory_dz_cm = 2.50;
  }

  setData(zArr, profile, fwhm_cm = 2.48, theory_dz_cm = 2.50) {
    this.zArr = zArr || [];
    this.profile = profile || [];
    this.fwhm_cm = fwhm_cm;
    this.theory_dz_cm = theory_dz_cm;
    this.render();
  }

  render() {
    if (!this.ctx || this.zArr.length === 0) return;
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    const padLeft = 45;
    const padRight = 20;
    const padTop = 20;
    const padBottom = 25;

    const plotW = w - padLeft - padRight;
    const plotH = h - padTop - padBottom;

    // Draw Grid
    ctx.strokeStyle = "rgba(28, 43, 69, 0.6)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let y = 0; y <= 4; y++) {
      const py = padTop + (plotH / 4) * y;
      ctx.moveTo(padLeft, py);
      ctx.lineTo(padLeft + plotW, py);
    }
    ctx.stroke();

    // Axis Labels
    ctx.fillStyle = "rgba(123, 148, 178, 0.7)";
    ctx.font = "9px monospace";
    ctx.fillText("1.0", 12, padTop + 4);
    ctx.fillText("-3dB", 12, padTop + plotH * 0.5 + 4);
    ctx.fillText("0.0", 12, padTop + plotH + 4);

    // Half power line (-3dB / 0.5)
    ctx.save();
    ctx.strokeStyle = "rgba(255, 183, 0, 0.7)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    const halfY = padTop + plotH * 0.5;
    ctx.moveTo(padLeft, halfY);
    ctx.lineTo(padLeft + plotW, halfY);
    ctx.stroke();
    ctx.restore();

    // Plot Signal Profile Curve
    const n = this.profile.length;
    ctx.save();
    ctx.strokeStyle = "#00f0ff";
    ctx.lineWidth = 2;
    ctx.shadowBlur = 8;
    ctx.shadowColor = "rgba(0, 240, 255, 0.6)";
    ctx.beginPath();

    for (let i = 0; i < n; i++) {
      const px = padLeft + (i / (n - 1)) * plotW;
      const py = padTop + plotH * (1 - this.profile[i]);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();

    // Fill area under curve
    ctx.lineTo(padLeft + plotW, padTop + plotH);
    ctx.lineTo(padLeft, padTop + plotH);
    ctx.closePath();
    ctx.fillStyle = "rgba(0, 240, 255, 0.1)";
    ctx.fill();
    ctx.restore();

    // Range coordinates along bottom
    const zMin = this.zArr[0];
    const zMax = this.zArr[this.zArr.length - 1];
    ctx.fillStyle = "rgba(123, 148, 178, 0.8)";
    ctx.font = "9px monospace";
    ctx.fillText(`${zMin}cm`, padLeft, h - 8);
    ctx.fillText("DEPTH Z (RANGE PROFILE)", padLeft + plotW / 2 - 50, h - 8);
    ctx.fillText(`${zMax}cm`, padLeft + plotW - 35, h - 8);

    // FWHM Resolution Annotation
    ctx.fillStyle = "#ffb700";
    ctx.font = "bold 10px monospace";
    ctx.fillText(`MEASURED FWHM: ${this.fwhm_cm.toFixed(2)} cm  |  THEORY δz: ${this.theory_dz_cm.toFixed(2)} cm (Ratio: ${(this.fwhm_cm/this.theory_dz_cm).toFixed(2)})`, padLeft + 10, padTop - 6);
  }
}

window.RadarHeatmapViewer = RadarHeatmapViewer;
window.RangeProfilePlotter = RangeProfilePlotter;
