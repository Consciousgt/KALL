/**
 * kall-3d.js
 * High-performance 3-D Holographic Matrix Engine for KALL Security Portal.
 * Pure native Canvas2D Vector & Voxel Projection — 100% Offline, Zero CDN dependency.
 */

class HolographicVolumeViewer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");

    // Camera & Transform state
    this.rotX = 0.38; // Elevation (rad)
    this.rotY = -0.65; // Azimuth (rad)
    this.zoom = 1.0;
    this.panX = 0;
    this.panY = 0;
    this.autoRotate = true;
    this.rotationSpeed = 0.005;

    // Interaction state
    this.isDragging = false;
    this.lastMouseX = 0;
    this.lastMouseY = 0;

    // Data state
    this.voxels = []; // [[x_cm, y_cm, z_cm, intensity], ...]
    this.peakTarget = null; // {x, y, z} in cm
    this.sliceZ = 50.0; // cm
    this.threshold = 0.22;

    this.initEvents();
    this.resize();
    this.animate();
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.floor(rect.width * dpr);
    this.canvas.height = Math.floor(rect.height * dpr);
    this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    this.ctx.scale(dpr, dpr);
    this.width = rect.width;
    this.height = rect.height;
  }

  initEvents() {
    window.addEventListener("resize", () => this.resize());

    this.canvas.addEventListener("mousedown", (e) => {
      this.isDragging = true;
      this.autoRotate = false;
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
      if (window.tacticalAudio) window.tacticalAudio.playClick();
    });

    window.addEventListener("mousemove", (e) => {
      if (!this.isDragging) return;
      const dx = e.clientX - this.lastMouseX;
      const dy = e.clientY - this.lastMouseY;
      this.rotY += dx * 0.008;
      this.rotX += dy * 0.008;
      // Clamp elevation
      this.rotX = Math.max(-Math.PI / 2.2, Math.min(Math.PI / 2.2, this.rotX));
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
    });

    window.addEventListener("mouseup", () => {
      this.isDragging = false;
    });

    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
      this.zoom = Math.max(0.4, Math.min(3.5, this.zoom * zoomFactor));
    }, { passive: false });
  }

  setData(voxels, peakTarget = null) {
    this.voxels = voxels || [];
    this.peakTarget = peakTarget;
  }

  setSliceDepth(z_cm) {
    this.sliceZ = parseFloat(z_cm);
  }

  setThreshold(val) {
    this.threshold = parseFloat(val);
  }

  resetView() {
    this.rotX = 0.38;
    this.rotY = -0.65;
    this.zoom = 1.0;
    this.panX = 0;
    this.panY = 0;
    this.autoRotate = false;
  }

  toggleAutoRotate() {
    this.autoRotate = !this.autoRotate;
    return this.autoRotate;
  }

  // 3-D -> 2-D Projection Matrix Pipeline
  projectPoint(x, y, z) {
    // Center point in aperture bounding volume
    // x: [-25, 25], y: [-25, 25], z: [25, 75] -> center at z=50
    const cx = x;
    const cy = y;
    const cz = z - 50.0;

    // Rotate around Y (Azimuth)
    const cosY = Math.cos(this.rotY);
    const sinY = Math.sin(this.rotY);
    const x1 = cx * cosY + cz * sinY;
    const z1 = -cx * sinY + cz * cosY;

    // Rotate around X (Elevation)
    const cosX = Math.cos(this.rotX);
    const sinX = Math.sin(this.rotX);
    const y2 = cy * cosX - z1 * sinX;
    const z2 = cy * sinX + z1 * cosX;

    // Perspective Projection
    const cameraDist = 120.0; // Distance of viewpoint
    const pz = z2 + cameraDist;
    const fov = 420.0 * this.zoom;

    if (pz <= 1) return null; // Behind camera plane

    const projX = (x1 / pz) * fov + (this.width / 2) + this.panX;
    const projY = (-y2 / pz) * fov + (this.height / 2) + this.panY;

    return { x: projX, y: projY, depth: z2 };
  }

  render() {
    if (!this.ctx) return;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    if (this.autoRotate && !this.isDragging) {
      this.rotY += this.rotationSpeed;
    }

    // 1. Draw 3-D Bounding Wireframe Box
    this.drawBoundingBox(ctx);

    // 2. Draw Aperture Plane at Z=25cm (Near Plane)
    this.drawAperturePlane(ctx);

    // 3. Draw Depth Slice Plane (Moves dynamically along Z)
    this.drawDepthSlicePlane(ctx);

    // 4. Project and Sort Voxels by Depth
    const projectedVoxels = [];
    const thresh = this.threshold;

    for (let i = 0; i < this.voxels.length; i++) {
      const v = this.voxels[i];
      const intensity = v[3];
      if (intensity < thresh) continue;

      const proj = this.projectPoint(v[0], v[1], v[2]);
      if (proj) {
        projectedVoxels.push({
          x: proj.x,
          y: proj.y,
          depth: proj.depth,
          intensity: intensity,
          z_cm: v[2],
        });
      }
    }

    // Painter's algorithm: draw farthest voxels first
    projectedVoxels.sort((a, b) => b.depth - a.depth);

    // Draw Voxels with Glow
    for (let i = 0; i < projectedVoxels.length; i++) {
      const pv = projectedVoxels[i];
      const int = pv.intensity;
      const size = Math.max(2.5, int * 7.5 * this.zoom);

      // Color mapping: Low=Cyan, Mid=Amber, High=Crimson
      let r = 0, g = 240, b = 255;
      if (int > 0.65) {
        // Red / Crimson
        r = 255; g = Math.floor(42 + (1 - int) * 100); b = 75;
      } else if (int > 0.4) {
        // Amber / Gold
        r = 255; g = 183; b = 0;
      }

      ctx.beginPath();
      ctx.arc(pv.x, pv.y, size, 0, 2 * Math.PI);
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${0.35 + int * 0.65})`;
      ctx.shadowBlur = 10 * int;
      ctx.shadowColor = `rgba(${r}, ${g}, ${b}, 0.8)`;
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    // 5. Draw Peak Target Reticle if active
    if (this.peakTarget) {
      this.drawPeakTargetCrosshair(ctx, this.peakTarget);
    }
  }

  drawBoundingBox(ctx) {
    const minX = -20, maxX = 20;
    const minY = -20, maxY = 20;
    const minZ = 25,  maxZ = 75;

    const corners = [
      [minX, minY, minZ], [maxX, minY, minZ],
      [maxX, maxY, minZ], [minX, maxY, minZ],
      [minX, minY, maxZ], [maxX, minY, maxZ],
      [maxX, maxY, maxZ], [minX, maxY, maxZ],
    ];

    const edges = [
      [0,1], [1,2], [2,3], [3,0], // Front (Near Z)
      [4,5], [5,6], [6,7], [7,4], // Back (Far Z)
      [0,4], [1,5], [2,6], [3,7], // Connectors
    ];

    const projectedCorners = corners.map(c => this.projectPoint(c[0], c[1], c[2]));

    ctx.save();
    ctx.strokeStyle = "rgba(41, 66, 107, 0.4)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    for (const [start, end] of edges) {
      const p1 = projectedCorners[start];
      const p2 = projectedCorners[end];
      if (p1 && p2) {
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }
    }

    // Corner Range Depth Labels
    ctx.fillStyle = "rgba(123, 148, 178, 0.6)";
    ctx.font = "9px monospace";
    const pFront = projectedCorners[0];
    const pBack = projectedCorners[4];
    if (pFront) ctx.fillText("Z=25cm", pFront.x - 10, pFront.y + 14);
    if (pBack) ctx.fillText("Z=75cm", pBack.x - 10, pBack.y + 14);

    ctx.restore();
  }

  drawAperturePlane(ctx) {
    const p1 = this.projectPoint(-20, -20, 25);
    const p2 = this.projectPoint( 20, -20, 25);
    const p3 = this.projectPoint( 20,  20, 25);
    const p4 = this.projectPoint(-20,  20, 25);

    if (p1 && p2 && p3 && p4) {
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.lineTo(p3.x, p3.y);
      ctx.lineTo(p4.x, p4.y);
      ctx.closePath();
      ctx.fillStyle = "rgba(0, 240, 255, 0.04)";
      ctx.fill();
      ctx.strokeStyle = "rgba(0, 240, 255, 0.25)";
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.fillStyle = "rgba(0, 240, 255, 0.7)";
      ctx.font = "9px monospace";
      ctx.fillText("[APERTURE PLANE Z=25cm]", p1.x + 8, p1.y - 6);
      ctx.restore();
    }
  }

  drawDepthSlicePlane(ctx) {
    const z = this.sliceZ;
    const p1 = this.projectPoint(-20, -20, z);
    const p2 = this.projectPoint( 20, -20, z);
    const p3 = this.projectPoint( 20,  20, z);
    const p4 = this.projectPoint(-20,  20, z);

    if (p1 && p2 && p3 && p4) {
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.lineTo(p3.x, p3.y);
      ctx.lineTo(p4.x, p4.y);
      ctx.closePath();
      ctx.fillStyle = "rgba(255, 183, 0, 0.08)";
      ctx.fill();
      ctx.strokeStyle = "rgba(255, 183, 0, 0.8)";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.stroke();

      ctx.fillStyle = "#ffb700";
      ctx.font = "10px monospace";
      ctx.fillText(`SLICE Z=${z.toFixed(1)}cm`, p2.x + 6, p2.y);
      ctx.restore();
    }
  }

  drawPeakTargetCrosshair(ctx, target) {
    const proj = this.projectPoint(target.x, target.y, target.z);
    if (!proj) return;

    ctx.save();
    const sz = 16;
    ctx.strokeStyle = "#ff2a4b";
    ctx.lineWidth = 2;
    ctx.shadowBlur = 12;
    ctx.shadowColor = "#ff2a4b";

    // Reticle brackets
    ctx.beginPath();
    ctx.arc(proj.x, proj.y, sz, 0, 2 * Math.PI);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(proj.x - sz - 6, proj.y);
    ctx.lineTo(proj.x + sz + 6, proj.y);
    ctx.moveTo(proj.x, proj.y - sz - 6);
    ctx.lineTo(proj.x, proj.y + sz + 6);
    ctx.stroke();

    ctx.fillStyle = "#ff2a4b";
    ctx.font = "bold 10px monospace";
    ctx.fillText(`THREAT ACQUIRED [${target.x.toFixed(1)}, ${target.y.toFixed(1)}, ${target.z.toFixed(1)}cm]`, proj.x + sz + 8, proj.y + 4);
    ctx.restore();
  }

  animate() {
    this.render();
    requestAnimationFrame(() => this.animate());
  }
}

window.HolographicVolumeViewer = HolographicVolumeViewer;
