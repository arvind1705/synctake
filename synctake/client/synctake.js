/**
 * SyncTake Client SDK
 * Browser-driven guided walkthrough player and automated screen recorder.
 * Features automatic Host Theme Adaptation to match the host application's design system.
 */
(function (global) {
  "use strict";

  function parseRGB(colorStr) {
    if (!colorStr) return null;
    const match = colorStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (match) {
      return { r: parseInt(match[1]), g: parseInt(match[2]), b: parseInt(match[3]) };
    }
    return null;
  }

  function getLuminance(rgb) {
    if (!rgb) return 1.0;
    return (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
  }

  function detectHostTheme() {
    const root = document.documentElement;
    const body = document.body;
    if (!body) return;

    const bodyStyle = window.getComputedStyle(body);
    const htmlStyle = window.getComputedStyle(root);

    // 1. Font Family
    const font = bodyStyle.fontFamily || htmlStyle.fontFamily || "system-ui, -apple-system, sans-serif";
    root.style.setProperty("--st-font", font);

    // 2. Background & Luminance
    let bgStr = bodyStyle.backgroundColor;
    if (!bgStr || bgStr === "transparent" || bgStr === "rgba(0, 0, 0, 0)") {
      bgStr = htmlStyle.backgroundColor || "rgb(255, 255, 255)";
    }
    const bgRGB = parseRGB(bgStr) || { r: 245, g: 247, b: 242 };
    const isDark = getLuminance(bgRGB) < 0.45;

    // 3. Detect Brand Accent
    // Look for brand elements, header, logo, or primary links/buttons
    let accent = null;
    let accentText = "#ffffff";

    const brandEl = document.querySelector(".logo, .brand, header a, button.primary, button[type='submit'], .btn-primary");
    if (brandEl) {
      const bs = window.getComputedStyle(brandEl);
      const bg = bs.backgroundColor;
      const fg = bs.color;
      if (bg && bg !== "transparent" && bg !== "rgba(0, 0, 0, 0)") {
        accent = bg;
        accentText = fg || "#ffffff";
      } else if (fg && fg !== bodyStyle.color) {
        accent = fg;
      }
    }

    if (!accent) {
      const linkEl = document.querySelector("a");
      if (linkEl) {
        accent = window.getComputedStyle(linkEl).color;
      }
    }

    // Default accents if not found
    if (!accent) {
      accent = isDark ? "#3b82f6" : "#244b35";
    }

    // 4. Detect Borders
    let borderColor = null;
    const cardEl = document.querySelector(".card, .recommendation-card, section, panel, border");
    if (cardEl) {
      const cs = window.getComputedStyle(cardEl);
      if (cs.borderColor && cs.borderColor !== "transparent") {
        borderColor = cs.borderColor;
      }
    }

    if (!borderColor) {
      borderColor = isDark ? "rgba(255, 255, 255, 0.12)" : "#dce4d8";
    }

    // 5. Apply Theme Variables
    if (isDark) {
      root.style.setProperty("--st-bg", "rgba(18, 22, 31, 0.92)");
      root.style.setProperty("--st-border", borderColor);
      root.style.setProperty("--st-text", "#f8fafc");
      root.style.setProperty("--st-text-muted", "#94a3b8");
      root.style.setProperty("--st-accent", accent);
      root.style.setProperty("--st-accent-text", accentText);
      root.style.setProperty("--st-btn-bg", "rgba(255, 255, 255, 0.08)");
      root.style.setProperty("--st-btn-hover", "rgba(255, 255, 255, 0.15)");
      root.style.setProperty("--st-shadow", "0 12px 36px rgba(0, 0, 0, 0.45)");
      root.style.setProperty("--st-ring", "rgba(96, 165, 250, 0.25)");
    } else {
      root.style.setProperty("--st-bg", "rgba(255, 255, 255, 0.94)");
      root.style.setProperty("--st-border", borderColor);
      root.style.setProperty("--st-text", bodyStyle.color || "#243629");
      root.style.setProperty("--st-text-muted", "#667667");
      root.style.setProperty("--st-accent", accent);
      root.style.setProperty("--st-accent-text", accentText);
      root.style.setProperty("--st-btn-bg", "#f4f8f1");
      root.style.setProperty("--st-btn-hover", "#e9f2e3");
      root.style.setProperty("--st-shadow", "0 10px 30px rgba(36, 54, 41, 0.1)");
      root.style.setProperty("--st-ring", "rgba(36, 75, 53, 0.18)");
    }
  }

  class SyncTakePlayer {
    constructor(config) {
      this.config = config;
      this.mediaRecorder = null;
      this.recordedBlobs = [];
      this.startTime = null;
      this.timerInterval = null;
      this.currentSceneIndex = -1;
      this.activeHighlight = null;

      // Adapt theme to host application
      detectHostTheme();
      this.initUI();
    }

    initUI() {
      // 1. Create Floating Controller Widget
      const widget = document.createElement("div");
      widget.className = "synctake-widget";
      widget.innerHTML = `
        <div class="synctake-btn-group">
          <button class="synctake-btn" id="synctake-preview-btn">▶ Preview Tour</button>
          <button class="synctake-btn synctake-btn-primary" id="synctake-record-btn">● Record Take</button>
          <span class="synctake-btn" id="synctake-timer" style="display:none;font-variant-numeric:tabular-nums;">00:00</span>
        </div>
      `;
      document.body.appendChild(widget);

      // 2. Create Callout Overlay
      const overlay = document.createElement("div");
      overlay.className = "synctake-callout-overlay";
      overlay.id = "synctake-callout";
      overlay.innerHTML = `
        <div class="synctake-callout-title" id="synctake-callout-title"></div>
        <div class="synctake-callout-sub" id="synctake-callout-sub"></div>
      `;
      document.body.appendChild(overlay);

      // Event Listeners
      document.getElementById("synctake-preview-btn").addEventListener("click", () => this.startTour(false));
      document.getElementById("synctake-record-btn").addEventListener("click", () => this.startTour(true));
    }

    async startTour(record = false) {
      if (record) {
        try {
          const stream = await navigator.mediaDevices.getDisplayMedia({
            video: {
              displaySurface: "browser",
              frameRate: 30,
            },
            audio: false,
          });

          this.recordedBlobs = [];
          this.mediaRecorder = new MediaRecorder(stream, {
            mimeType: "video/webm;codecs=vp9",
          });

          this.mediaRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
              this.recordedBlobs.push(event.data);
            }
          };

          this.mediaRecorder.onstop = () => {
            stream.getTracks().forEach((track) => track.stop());
            this.downloadTake();
          };

          this.mediaRecorder.start(100);
          document.getElementById("synctake-record-btn").classList.add("synctake-btn-recording");
          document.getElementById("synctake-record-btn").innerText = "■ Recording...";
        } catch (err) {
          console.error("[SyncTake] Screen recording cancelled or denied:", err);
          return;
        }
      }

      const timerEl = document.getElementById("synctake-timer");
      timerEl.style.display = "inline-flex";

      this.startTime = performance.now();
      this.currentSceneIndex = -1;

      // Master tick loop
      this.timerInterval = setInterval(() => {
        const elapsed = (performance.now() - this.startTime) / 1000;
        const total = this.config.duration_seconds;

        const mins = Math.floor(elapsed / 60);
        const secs = Math.floor(elapsed % 60);
        timerEl.innerText = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")} / ${Math.round(total)}s`;

        this.checkScene(elapsed);

        if (elapsed >= total) {
          this.stopTour();
        }
      }, 50);
    }

    checkScene(elapsed) {
      const scenes = this.config.scenes;
      let activeIndex = -1;

      for (let i = 0; i < scenes.length; i++) {
        if (elapsed >= scenes[i].at) {
          activeIndex = i;
        }
      }

      if (activeIndex !== -1 && activeIndex !== this.currentSceneIndex) {
        this.currentSceneIndex = activeIndex;
        this.triggerScene(scenes[activeIndex]);
      }
    }

    triggerScene(scene) {
      window.dispatchEvent(
        new CustomEvent("synctake:scene", {
          detail: scene,
        })
      );

      const overlay = document.getElementById("synctake-callout");
      const titleEl = document.getElementById("synctake-callout-title");
      const subEl = document.getElementById("synctake-callout-sub");

      if (scene.title || scene.callout) {
        titleEl.innerText = scene.title || "";
        subEl.innerText = scene.callout || "";
        overlay.classList.add("active");
        setTimeout(() => overlay.classList.remove("active"), 4500);
      } else {
        overlay.classList.remove("active");
      }

      if (this.activeHighlight) {
        this.activeHighlight.classList.remove("synctake-highlight");
        this.activeHighlight = null;
      }

      if (scene.focus) {
        const target = document.querySelector(scene.focus);
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "center" });
          target.classList.add("synctake-highlight");
          this.activeHighlight = target;
        }
      }
    }

    stopTour() {
      clearInterval(this.timerInterval);
      const timerEl = document.getElementById("synctake-timer");
      timerEl.style.display = "none";

      const recordBtn = document.getElementById("synctake-record-btn");
      recordBtn.classList.remove("synctake-btn-recording");
      recordBtn.innerText = "● Record Take";

      if (this.activeHighlight) {
        this.activeHighlight.classList.remove("synctake-highlight");
      }
      document.getElementById("synctake-callout").classList.remove("active");

      if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
        this.mediaRecorder.stop();
      }
    }

    downloadTake() {
      const blob = new Blob(this.recordedBlobs, { type: "video/webm" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = `synctake-${Date.now()}.webm`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }, 100);
    }
  }

  global.SyncTake = {
    init: function (config) {
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => new SyncTakePlayer(config));
      } else {
        new SyncTakePlayer(config);
      }
    },
    autoInit: function (configUrl = "./synctake.json") {
      fetch(configUrl)
        .then((r) => r.json())
        .then((config) => global.SyncTake.init(config))
        .catch((err) => console.error("[SyncTake] Failed to auto-load config:", err));
    },
  };
})(window);
