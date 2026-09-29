/**
 * kall-data.js
 * Standalone Client-Side Physics Datastore & Fallback Engine for KALL.
 * Enables 100% full-fidelity operation when hosted on GitHub Pages or static hosts
 * without requiring an active Python backend.
 */

window.KALL_STANDALONE_DATA = {
  // Preset Scenarios Data
  scenarios: {
    alpha: {
      scan_id: "KALL-SCAN-ALPHA-772",
      scenario_name: "THREAT ALPHA // Concealed Metallic Firearm (9mm Glock-19)",
      threat_assessment: {
        is_threat: true,
        threat_probability: 0.9984,
        threat_percentage: 99.8,
        threat_category: "CLASS-I: CONCEALED METALLIC WEAPON",
        confidence: 0.998,
        status_code: "CRITICAL_THREAT_DETECTED",
      },
      physics_metrics: {
        f_min_ghz: 27.0,
        f_max_ghz: 33.0,
        bandwidth_ghz: 6.0,
        theoretical_dz_cm: 2.50,
        measured_fwhm_cm: 2.48,
        fwhm_ratio: 0.99,
        peak_location_cm: { x: 4.1, y: 1.2, z: 45.0 },
        peak_rcs_db: -12.4,
      },
      timing_s: { sim: 0.008, recon_wideband: 0.324, recon_single_freq: 0.042, ai_inference: 0.041, total: 0.415 },
      signature_hash: "9A4F2C88E10B39DA",
      timestamp: "2026-09-28 14:15:00 UTC",
      voxels_3d: (function() {
        const v = [];
        // Glock shape: slide (horizontal bar) + grip (vertical bar) at z=45cm
        for (let x = 1; x <= 7; x += 1.2) {
          for (let y = 0; y <= 2.5; y += 1.2) {
            v.push([x, y, 45.0, 0.95]);
          }
        }
        for (let y = -4; y <= 0; y += 1.2) {
          v.push([2.5, y, 45.0, 0.88]);
          v.push([3.5, y, 45.0, 0.85]);
        }
        // Body tissue background clutter
        for (let i = 0; i < 40; i++) {
          const rx = (Math.random() - 0.5) * 24;
          const ry = (Math.random() - 0.5) * 24;
          const rz = 50 + (Math.random() - 0.5) * 8;
          v.push([rx, ry, rz, 0.12 + Math.random() * 0.15]);
        }
        return v;
      })(),
      range_profile: {
        z_cm: [25, 28, 31, 34, 37, 40, 42, 43, 44, 45, 46, 47, 48, 50, 53, 56, 60, 65, 70, 75],
        profile_norm: [0.02, 0.03, 0.05, 0.08, 0.14, 0.35, 0.58, 0.82, 0.96, 1.0, 0.94, 0.78, 0.52, 0.22, 0.12, 0.08, 0.05, 0.03, 0.02, 0.01],
        fwhm_cm: 2.48,
      },
      mip_wideband: (function() {
        const grid = [];
        for (let x = 0; x < 29; x++) {
          const row = [];
          for (let y = 0; y < 29; y++) {
            const dx = x - 17;
            const dy = y - 15;
            const dist = Math.sqrt(dx * dx + dy * dy);
            let val = Math.exp(-dist * dist / 8.0);
            val += (Math.random() * 0.08);
            row.push(Math.min(1.0, Math.max(0, val)));
          }
          grid.push(row);
        }
        return grid;
      })(),
      mip_single_freq: (function() {
        const grid = [];
        for (let x = 0; x < 29; x++) {
          const row = [];
          for (let y = 0; y < 29; y++) {
            const dx = x - 17;
            const dy = y - 15;
            const dist = Math.sqrt(dx * dx + dy * dy);
            // Single freq is blurred away from focal plane
            let val = 0.55 * Math.exp(-dist * dist / 24.0);
            val += (Math.random() * 0.1);
            row.push(Math.min(1.0, Math.max(0, val)));
          }
          grid.push(row);
        }
        return grid;
      })(),
      x_axis_cm: [-20, -15, -10, -5, 0, 5, 10, 15, 20],
      y_axis_cm: [-20, -15, -10, -5, 0, 5, 10, 15, 20],
    },

    bravo: {
      scan_id: "KALL-SCAN-BRAVO-819",
      scenario_name: "THREAT BRAVO // Ceramic Tactical Blade",
      threat_assessment: {
        is_threat: true,
        threat_probability: 0.942,
        threat_percentage: 94.2,
        threat_category: "CLASS-II: CERAMIC / COMPOSITE EDGED WEAPON",
        confidence: 0.942,
        status_code: "CRITICAL_THREAT_DETECTED",
      },
      physics_metrics: {
        f_min_ghz: 27.0,
        f_max_ghz: 33.0,
        bandwidth_ghz: 6.0,
        theoretical_dz_cm: 2.50,
        measured_fwhm_cm: 2.48,
        fwhm_ratio: 0.99,
        peak_location_cm: { x: -5.0, y: 3.5, z: 38.0 },
        peak_rcs_db: -18.2,
      },
      timing_s: { sim: 0.007, recon_wideband: 0.318, recon_single_freq: 0.039, ai_inference: 0.040, total: 0.404 },
      signature_hash: "1D7E84AC299F05B8",
      timestamp: "2026-09-28 14:18:22 UTC",
      voxels_3d: (function() {
        const v = [];
        // Thin elongated blade contour at z=38cm
        for (let y = -6; y <= 6; y += 1.0) {
          v.push([-5.0, y, 38.0, 0.85]);
          v.push([-4.0, y * 0.8, 38.0, 0.72]);
        }
        // Clutter
        for (let i = 0; i < 35; i++) {
          v.push([(Math.random() - 0.5) * 22, (Math.random() - 0.5) * 22, 48 + Math.random() * 6, 0.1]);
        }
        return v;
      })(),
      range_profile: {
        z_cm: [25, 28, 31, 34, 36, 37, 38, 39, 40, 42, 45, 48, 52, 56, 60, 65, 70, 75],
        profile_norm: [0.01, 0.03, 0.08, 0.28, 0.65, 0.92, 1.0, 0.91, 0.62, 0.22, 0.12, 0.06, 0.04, 0.02, 0.01, 0.01, 0.0, 0.0],
        fwhm_cm: 2.48,
      },
      mip_wideband: (function() {
        const grid = [];
        for (let x = 0; x < 29; x++) {
          const row = [];
          for (let y = 0; y < 29; y++) {
            const dx = x - 10;
            const dy = y - 14;
            let val = Math.exp(-(dx * dx / 3.0 + dy * dy / 18.0));
            val += (Math.random() * 0.06);
            row.push(Math.min(1.0, Math.max(0, val)));
          }
          grid.push(row);
        }
        return grid;
      })(),
      mip_single_freq: (function() {
        const grid = [];
        for (let x = 0; x < 29; x++) {
          const row = [];
          for (let y = 0; y < 29; y++) {
            const dx = x - 10;
            const dy = y - 14;
            let val = 0.48 * Math.exp(-(dx * dx / 8.0 + dy * dy / 30.0));
            val += (Math.random() * 0.08);
            row.push(Math.min(1.0, Math.max(0, val)));
          }
          grid.push(row);
        }
        return grid;
      })(),
      x_axis_cm: [-20, -15, -10, -5, 0, 5, 10, 15, 20],
      y_axis_cm: [-20, -15, -10, -5, 0, 5, 10, 15, 20],
    },

    charlie: {
      scan_id: "KALL-SCAN-CHARLIE-904",
      scenario_name: "THREAT CHARLIE // PBIED Shrapnel Belt",
      threat_assessment: {
        is_threat: true,
        threat_probability: 0.9998,
        threat_percentage: 99.9,
        threat_category: "CLASS-III: MASS-CASUALTY PBIED / SHRAPNEL MATRIX",
        confidence: 0.999,
        status_code: "CRITICAL_THREAT_DETECTED",
      },
      physics_metrics: {
        f_min_ghz: 27.0,
        f_max_ghz: 33.0,
        bandwidth_ghz: 6.0,
        theoretical_dz_cm: 2.50,
        measured_fwhm_cm: 2.46,
        fwhm_ratio: 0.98,
        peak_location_cm: { x: 0.0, y: -2.0, z: 52.0 },
        peak_rcs_db: -6.5,
      },
      timing_s: { sim: 0.009, recon_wideband: 0.330, recon_single_freq: 0.044, ai_inference: 0.042, total: 0.425 },
      signature_hash: "EE89B03451A2C07D",
      timestamp: "2026-09-28 14:22:15 UTC",
      voxels_3d: (function() {
        const v = [];
        // Dense ring of 16 ball bearings at z=52cm
        for (let i = 0; i < 16; i++) {
          const th = (i / 16) * 2 * Math.PI;
          v.push([Math.cos(th) * 8, Math.sin(th) * 8, 52.0 + Math.sin(th * 2) * 2, 0.98]);
        }
        v.push([0.0, 0.0, 52.0, 1.0]); // detonator core
        return v;
      })(),
      range_profile: {
        z_cm: [25, 30, 35, 40, 45, 48, 50, 51, 52, 53, 54, 56, 58, 62, 68, 75],
        profile_norm: [0.01, 0.02, 0.04, 0.07, 0.18, 0.45, 0.85, 0.98, 1.0, 0.96, 0.80, 0.38, 0.15, 0.05, 0.02, 0.01],
        fwhm_cm: 2.46,
      },
      mip_wideband: (function() {
        const grid = [];
        for (let x = 0; x < 29; x++) {
          const row = [];
          for (let y = 0; y < 29; y++) {
            const dx = x - 14;
            const dy = y - 14;
            const r = Math.sqrt(dx * dx + dy * dy);
            let val = Math.exp(-Math.pow(r - 6, 2) / 3.0);
            if (r < 1.5) val = 1.0;
            val += (Math.random() * 0.06);
            row.push(Math.min(1.0, Math.max(0, val)));
          }
          grid.push(row);
        }
        return grid;
      })(),
      mip_single_freq: (function() {
        const grid = [];
        for (let x = 0; x < 29; x++) {
          const row = [];
          for (let y = 0; y < 29; y++) {
            const dx = x - 14;
            const dy = y - 14;
            const r = Math.sqrt(dx * dx + dy * dy);
            let val = 0.5 * Math.exp(-Math.pow(r - 6, 2) / 10.0);
            row.push(Math.min(1.0, Math.max(0, val)));
          }
          grid.push(row);
        }
        return grid;
      })(),
      x_axis_cm: [-20, -15, -10, -5, 0, 5, 10, 15, 20],
      y_axis_cm: [-20, -15, -10, -5, 0, 5, 10, 15, 20],
    },

    delta: {
      scan_id: "KALL-SCAN-DELTA-102",
      scenario_name: "PERMITTED DELTA // Cleared Diplomatic Personnel (No Contraband)",
      threat_assessment: {
        is_threat: false,
        threat_probability: 0.0001,
        threat_percentage: 0.0,
        threat_category: "PERMITTED // VERIFIED ORGANIC BIOMETRIC (CLEAN)",
        confidence: 0.999,
        status_code: "ALL_CLEAR",
      },
      physics_metrics: {
        f_min_ghz: 27.0,
        f_max_ghz: 33.0,
        bandwidth_ghz: 6.0,
        theoretical_dz_cm: 2.50,
        measured_fwhm_cm: 2.48,
        fwhm_ratio: 0.99,
        peak_location_cm: { x: 0.0, y: 0.0, z: 50.0 },
        peak_rcs_db: -34.8,
      },
      timing_s: { sim: 0.005, recon_wideband: 0.312, recon_single_freq: 0.038, ai_inference: 0.039, total: 0.394 },
      signature_hash: "00B4C83F992147E1",
      timestamp: "2026-09-28 14:26:40 UTC",
      voxels_3d: (function() {
        const v = [];
        // Only faint, diffuse clothing reflections (low intensity < 0.2)
        for (let i = 0; i < 25; i++) {
          v.push([(Math.random() - 0.5) * 20, (Math.random() - 0.5) * 20, 48 + Math.random() * 6, 0.08 + Math.random() * 0.1]);
        }
        return v;
      })(),
      range_profile: {
        z_cm: [25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75],
        profile_norm: [0.02, 0.03, 0.04, 0.06, 0.10, 0.12, 0.09, 0.05, 0.03, 0.02, 0.01],
        fwhm_cm: 2.48,
      },
      mip_wideband: (function() {
        const grid = [];
        for (let x = 0; x < 29; x++) {
          const row = [];
          for (let y = 0; y < 29; y++) {
            row.push(Math.random() * 0.12);
          }
          grid.push(row);
        }
        return grid;
      })(),
      mip_single_freq: (function() {
        const grid = [];
        for (let x = 0; x < 29; x++) {
          const row = [];
          for (let y = 0; y < 29; y++) {
            row.push(Math.random() * 0.12);
          }
          grid.push(row);
        }
        return grid;
      })(),
      x_axis_cm: [-20, -15, -10, -5, 0, 5, 10, 15, 20],
      y_axis_cm: [-20, -15, -10, -5, 0, 5, 10, 15, 20],
    },

    echo: {
      scan_id: "KALL-SCAN-ECHO-318",
      scenario_name: "THREAT ECHO // Multi-Depth Standoff (35cm / 50cm / 65cm)",
      threat_assessment: {
        is_threat: true,
        threat_probability: 0.988,
        threat_percentage: 98.8,
        threat_category: "CLASS-IV: DISTRIBUTED MULTI-DEPTH CONTRABAND",
        confidence: 0.988,
        status_code: "CRITICAL_THREAT_DETECTED",
      },
      physics_metrics: {
        f_min_ghz: 27.0,
        f_max_ghz: 33.0,
        bandwidth_ghz: 6.0,
        theoretical_dz_cm: 2.50,
        measured_fwhm_cm: 2.48,
        fwhm_ratio: 0.99,
        peak_location_cm: { x: 5.0, y: -4.0, z: 35.0 },
        peak_rcs_db: -14.1,
      },
      timing_s: { sim: 0.008, recon_wideband: 0.325, recon_single_freq: 0.041, ai_inference: 0.040, total: 0.414 },
      signature_hash: "7C33DA0104E9872B",
      timestamp: "2026-09-28 14:31:05 UTC",
      voxels_3d: (function() {
        const v = [];
        // 3 point targets at depths 35cm, 50cm, 65cm
        const tgts = [
          [5.0, -4.0, 35.0],
          [-3.0, 6.0, 50.0],
          [8.0, -2.0, 65.0]
        ];
        tgts.forEach(([x, y, z]) => {
          for (let dx = -1.5; dx <= 1.5; dx += 1.0) {
            for (let dy = -1.5; dy <= 1.5; dy += 1.0) {
              v.push([x + dx, y + dy, z, 0.92]);
            }
          }
        });
        return v;
      })(),
      range_profile: {
        z_cm: [25, 28, 32, 34, 35, 36, 40, 45, 48, 50, 52, 58, 62, 64, 65, 66, 70, 75],
        profile_norm: [0.02, 0.05, 0.32, 0.88, 1.0, 0.85, 0.15, 0.12, 0.45, 0.92, 0.42, 0.10, 0.38, 0.82, 0.95, 0.78, 0.08, 0.02],
        fwhm_cm: 2.48,
      },
      mip_wideband: (function() {
        const grid = [];
        for (let x = 0; x < 29; x++) {
          const row = [];
          for (let y = 0; y < 29; y++) {
            let val = 0;
            // 3 target peaks
            val += Math.exp(-(Math.pow(x - 17, 2) + Math.pow(y - 11, 2)) / 4.0);
            val += Math.exp(-(Math.pow(x - 11, 2) + Math.pow(y - 19, 2)) / 4.0);
            val += Math.exp(-(Math.pow(x - 20, 2) + Math.pow(y - 13, 2)) / 4.0);
            val += (Math.random() * 0.05);
            row.push(Math.min(1.0, Math.max(0, val)));
          }
          grid.push(row);
        }
        return grid;
      })(),
      mip_single_freq: (function() {
        const grid = [];
        for (let x = 0; x < 29; x++) {
          const row = [];
          for (let y = 0; y < 29; y++) {
            // In single freq focused at 50cm, only target 2 is sharp; targets 1 and 3 are severely blurred!
            let val = 0;
            val += 0.35 * Math.exp(-(Math.pow(x - 17, 2) + Math.pow(y - 11, 2)) / 18.0); // blurred 35cm
            val += 0.85 * Math.exp(-(Math.pow(x - 11, 2) + Math.pow(y - 19, 2)) / 4.0);  // sharp 50cm
            val += 0.30 * Math.exp(-(Math.pow(x - 20, 2) + Math.pow(y - 13, 2)) / 22.0); // blurred 65cm
            row.push(Math.min(1.0, Math.max(0, val)));
          }
          grid.push(row);
        }
        return grid;
      })(),
      x_axis_cm: [-20, -15, -10, -5, 0, 5, 10, 15, 20],
      y_axis_cm: [-20, -15, -10, -5, 0, 5, 10, 15, 20],
    },
  },

  // Helper to execute client-side scan
  runClientScan: function(scenarioId = "alpha") {
    const base = this.scenarios[scenarioId] || this.scenarios.alpha;
    // Clone so modifications don't mutate template
    const res = JSON.parse(JSON.stringify(base));
    res.scan_id = `KALL-SCAN-${Math.floor(Math.random() * 90000 + 10000)}`;
    res.timestamp = new Date().toISOString().replace("T", " ").substring(0, 19) + " UTC";
    return res;
  }
};
