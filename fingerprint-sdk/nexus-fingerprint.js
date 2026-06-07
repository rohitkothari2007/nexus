// ============================================================
// NEXUS Fingerprint SDK
// Collects device fingerprint + behavioral signals
// Include this script in any onboarding form
// ============================================================

const NexusFingerprint = {

  // ============================================================
  // Device Fingerprinting
  // Each signal alone is not unique enough
  // Combined together they create a highly unique device ID
  // ============================================================

  async getCanvasFingerprint() {
    // Every GPU + driver combination renders canvas slightly differently
    // This creates a unique hash per device hardware
    try {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      ctx.textBaseline = "top";
      ctx.font = "14px Arial";
      ctx.fillStyle = "#f60";
      ctx.fillRect(125, 1, 62, 20);
      ctx.fillStyle = "#069";
      ctx.fillText("NEXUS fingerprint 🔍", 2, 15);
      ctx.fillStyle = "rgba(102, 204, 0, 0.7)";
      ctx.fillText("NEXUS fingerprint 🔍", 4, 17);
      return canvas.toDataURL().slice(-50);
    } catch (e) {
      return "canvas_blocked";
    }
  },

  async getWebGLFingerprint() {
    // GPU model and driver leave unique rendering signatures
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl") ||
                 canvas.getContext("experimental-webgl");
      if (!gl) return "webgl_not_supported";
      const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
      if (debugInfo) {
        const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
        const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
        return `${vendor}~${renderer}`;
      }
      return "webgl_no_debug";
    } catch (e) {
      return "webgl_blocked";
    }
  },

  async getAudioFingerprint() {
    // Audio processing hardware leaves unique signatures
    // Different sound cards produce slightly different outputs
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return "audio_not_supported";
      const context = new AudioContext();
      const oscillator = context.createOscillator();
      const analyser = context.createAnalyser();
      const gainNode = context.createGain();
      gainNode.gain.value = 0;
      oscillator.connect(analyser);
      analyser.connect(gainNode);
      gainNode.connect(context.destination);
      oscillator.start(0);
      const frequencyData = new Float32Array(analyser.frequencyBinCount);
      analyser.getFloatFrequencyData(frequencyData);
      oscillator.stop();
      context.close();
      return frequencyData.slice(0, 10).join(",");
    } catch (e) {
      return "audio_blocked";
    }
  },

  getBasicFingerprint() {
    // Basic browser and system info
    // None of these alone are unique but combined they are
    return {
      userAgent: navigator.userAgent,
      language: navigator.language,
      languages: navigator.languages ? navigator.languages.join(",") : "",
      platform: navigator.platform,
      hardwareConcurrency: navigator.hardwareConcurrency || 0,
      deviceMemory: navigator.deviceMemory || 0,
      screenResolution: `${screen.width}x${screen.height}`,
      screenDepth: screen.colorDepth,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      timezoneOffset: new Date().getTimezoneOffset(),
      cookiesEnabled: navigator.cookieEnabled,
      doNotTrack: navigator.doNotTrack,
      touchPoints: navigator.maxTouchPoints || 0,
      plugins: Array.from(navigator.plugins || [])
        .map(p => p.name).join(",")
    };
  },

  detectEmulator() {
    // Emulators and automation tools leave specific traces
    // Real browsers don't have these
    const flags = [];

    // Check for WebDriver (Selenium/Playwright)
    if (navigator.webdriver) {
      flags.push("webdriver_detected");
    }

    // Check for automation properties
    if (window.callPhantom || window._phantom) {
      flags.push("phantomjs_detected");
    }

    // Check for impossible hardware
    if (navigator.hardwareConcurrency > 64) {
      flags.push("impossible_cpu_count");
    }

    // Check for headless Chrome
    if (/HeadlessChrome/.test(navigator.userAgent)) {
      flags.push("headless_chrome");
    }

    // Check for missing browser features real browsers have
    if (!window.chrome && /Chrome/.test(navigator.userAgent)) {
      flags.push("chrome_missing_runtime");
    }

    // Check screen resolution - emulators often use default sizes
    if (screen.width === 800 && screen.height === 600) {
      flags.push("default_emulator_resolution");
    }

    return {
      is_emulator: flags.length > 0,
      emulator_flags: flags
    };
  },

  // ============================================================
  // Behavioral Tracking
  // How a user interacts with a form reveals if they're human
  // Bots complete forms too fast, too perfectly, in wrong order
  // ============================================================

  startBehaviorTracking(formId) {
    // Initialize behavior data store
    window._nexusBehavior = {
      formId: formId,
      startTime: Date.now(),
      keystrokes: [],
      mouseMovements: [],
      fieldTimings: {},
      pasteEvents: [],
      fieldOrder: [],
      currentField: null
    };

    // Track keystroke timing
    // Real humans have irregular typing rhythm
    // Bots type at perfectly consistent intervals
    document.addEventListener("keydown", (e) => {
      window._nexusBehavior.keystrokes.push({
        key: e.key.length === 1 ? "char" : e.key,
        time: Date.now() - window._nexusBehavior.startTime
      });
    });

    // Track mouse movement
    // Real humans move mouse in curved, irregular paths
    // Bots move in straight lines or don't move at all
    let lastMouseTime = 0;
    document.addEventListener("mousemove", (e) => {
      const now = Date.now();
      if (now - lastMouseTime > 100) {
        window._nexusBehavior.mouseMovements.push({
          x: e.clientX,
          y: e.clientY,
          t: now - window._nexusBehavior.startTime
        });
        lastMouseTime = now;
      }
    });

    // Track paste events
    // Fraudsters often paste pre-filled data
    document.addEventListener("paste", (e) => {
      window._nexusBehavior.pasteEvents.push({
        target: e.target.name || e.target.id || "unknown",
        time: Date.now() - window._nexusBehavior.startTime
      });
    });

    // Track field focus timing
    // Which fields they focus on and for how long
    document.querySelectorAll("input, select, textarea").forEach(field => {
      field.addEventListener("focus", () => {
        const fieldName = field.name || field.id || "unknown";
        window._nexusBehavior.currentField = fieldName;
        window._nexusBehavior.fieldTimings[fieldName] = {
          focusTime: Date.now() - window._nexusBehavior.startTime,
          blurTime: null,
          duration: null
        };
        if (!window._nexusBehavior.fieldOrder.includes(fieldName)) {
          window._nexusBehavior.fieldOrder.push(fieldName);
        }
      });

      field.addEventListener("blur", () => {
        const fieldName = field.name || field.id || "unknown";
        if (window._nexusBehavior.fieldTimings[fieldName]) {
          const blurTime = Date.now() - window._nexusBehavior.startTime;
          window._nexusBehavior.fieldTimings[fieldName].blurTime = blurTime;
          window._nexusBehavior.fieldTimings[fieldName].duration =
            blurTime - window._nexusBehavior.fieldTimings[fieldName].focusTime;
        }
      });
    });

    console.log("NEXUS behavior tracking started for form:", formId);
  },

  analyzeBehavior() {
    const b = window._nexusBehavior;
    if (!b) return { error: "Tracking not started" };

    const totalTime = Date.now() - b.startTime;
    const keystrokeCount = b.keystrokes.length;
    const mouseMovementCount = b.mouseMovements.length;
    const pasteCount = b.pasteEvents.length;

    // Calculate typing speed consistency
    // Real humans have variable inter-key timing
    // Bots are too consistent
    let typingConsistency = 0;
    if (keystrokeCount > 5) {
      const intervals = [];
      for (let i = 1; i < b.keystrokes.length; i++) {
        intervals.push(b.keystrokes[i].time - b.keystrokes[i-1].time);
      }
      const mean = intervals.reduce((a, b) => a + b, 0) / intervals.length;
      const variance = intervals.reduce((a, b) => a + Math.pow(b - mean, 2), 0)
                       / intervals.length;
      // High variance = human, low variance = bot
      typingConsistency = Math.min(1, variance / 10000);
    }

    // Bot risk score based on behavior
    let botRiskScore = 0;

    // Too fast = suspicious
    if (totalTime < 10000) botRiskScore += 0.4;
    else if (totalTime < 30000) botRiskScore += 0.2;

    // No mouse movement = suspicious
    if (mouseMovementCount < 5) botRiskScore += 0.2;

    // Too many pastes = suspicious
    if (pasteCount > 3) botRiskScore += 0.2;

    // Very few keystrokes = form filled by script
    if (keystrokeCount < 10 && totalTime < 60000) botRiskScore += 0.2;

    return {
      total_time_ms: totalTime,
      keystroke_count: keystrokeCount,
      mouse_movement_count: mouseMovementCount,
      paste_count: pasteCount,
      paste_events: b.pasteEvents,
      typing_consistency: Math.round(typingConsistency * 1000) / 1000,
      field_order: b.fieldOrder,
      field_timings: b.fieldTimings,
      bot_risk_score: Math.min(1, Math.round(botRiskScore * 100) / 100)
    };
  },

  // ============================================================
  // Main collect function
  // Call this when form is submitted
  // Returns everything NEXUS needs
  // ============================================================

  async collect() {
    const basic = this.getBasicFingerprint();
    const canvas = await this.getCanvasFingerprint();
    const webgl = await this.getWebGLFingerprint();
    const audio = await this.getAudioFingerprint();
    const emulator = this.detectEmulator();
    const behavior = this.analyzeBehavior();

    // Create combined fingerprint string
    const fingerprintString = [
      basic.userAgent,
      basic.screenResolution,
      basic.timezone,
      basic.hardwareConcurrency,
      canvas,
      webgl
    ].join("|");

    // Simple hash function
    let hash = 0;
    for (let i = 0; i < fingerprintString.length; i++) {
      const char = fingerprintString.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    const deviceId = Math.abs(hash).toString(16).padStart(8, "0");

    return {
      device_id: deviceId,
      fingerprint: {
        canvas: canvas,
        webgl: webgl,
        audio: audio,
        basic: basic
      },
      emulator_detection: emulator,
      behavior: behavior,
      collected_at: new Date().toISOString()
    };
  }
};

// Make available globally
window.NexusFingerprint = NexusFingerprint;