import streamlit.components.v1 as components


def render_camera_shutdown():
    """
    Renders an active client-side cleanup snippet that immediately stops and releases
    all WebRTC camera and microphone tracks on the client device.
    Ensures camera indicator LED turns off after the interview finishes.
    """
    shutdown_html = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body>
      <script>
        (function() {
          try {
            if (window._hirexpMediaStream) {
              window._hirexpMediaStream.getTracks().forEach(function(track) {
                try { track.stop(); } catch(e) {}
              });
              window._hirexpMediaStream = null;
            }
          } catch(e) {}

          try {
            if (window.parent && window.parent._hirexpMediaStream) {
              window.parent._hirexpMediaStream.getTracks().forEach(function(track) {
                try { track.stop(); } catch(e) {}
              });
              window.parent._hirexpMediaStream = null;
            }
          } catch(e) {}

          if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ video: true, audio: true })
              .then(function(stream) {
                stream.getTracks().forEach(function(track) {
                  try { track.stop(); } catch(e) {}
                });
              })
              .catch(function() {});
          }
        })();
      </script>
    </body>
    </html>
    """
    components.html(shutdown_html, height=0)


def render_interview_security_shield(session_id: str = ""):
    """
    Enterprise-grade Client-Side Interview Security & AI Proctoring Shield:
    1. Browser Activity & Tab Switching Detection:
       - Page Visibility API, window.blur/focus, fullscreenchange.
       - Graduated 3-tier warning system (Warning 1, Warning 2, Warning 3 flagged for recruiter review).
       - Accidental focus debounce & persistent review flagging (no auto-disqualification).
    2. Real-Time Multiple-Person Detection:
       - BlazeFace computer vision model on WebRTC camera frames.
       - Draws bounding boxes on local canvas preview.
       - Consecutive-cycle verification for 0 faces, 1 face (normal), 2+ faces (violation).
    3. Mobile Phone & Gadget Detection:
       - COCO-SSD object detection model.
       - Detects mobile phones ('cell phone') and unauthorized electronic devices.
       - Highlights detected gadgets with red bounding boxes and warning overlays.
    4. Copy, Paste & Keyboard Restrictions:
       - Disables paste into protected answer fields with clear user prompt.
       - Intercepts unauthorized copy/cut and restricted developer shortcuts (F12, Ctrl+C/V/X/P/S).
    5. Camera & Microphone Monitoring:
       - Stream connection & disconnect detection with reconnect recovery.
       - Live Web Audio API microphone volume input level meter.
    6. Seamless Backend Event Dispatching:
       - Dispatches structured events to database and parent window log.
    """
    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@3.18.0/dist/tf.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/@tensorflow-models/blazeface@0.0.7/dist/blazeface.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd@2.2.2/dist/coco-ssd.min.js"></script>
      <style>
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          padding: 0;
          background: transparent;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          color: #F8FAFC;
          user-select: none;
        }}
        .shield-card {{
          background: #151C33;
          border: 1px solid #232D4B;
          border-radius: 10px;
          padding: 8px 10px;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
          position: relative;
        }}
        .shield-header {{
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 6px;
        }}
        .shield-title {{
          display: flex;
          align-items: center;
          gap: 5px;
          font-weight: 700;
          font-size: 11.5px;
          color: #F8FAFC;
        }}
        .pill-badge {{
          font-size: 9.5px;
          padding: 2px 7px;
          border-radius: 9999px;
          font-weight: 700;
        }}
        .pill-normal {{ background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #059669; }}
        .pill-warn {{ background: rgba(245, 158, 11, 0.2); color: #FBBF24; border: 1px solid #D97706; }}
        .pill-alert {{ background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #DC2626; }}

        .video-canvas-wrap {{
          width: 100%;
          height: 140px;
          border-radius: 8px;
          background: #0B0F19;
          overflow: hidden;
          position: relative;
          border: 2px solid #4F46E5;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
        }}
        .video-canvas-wrap.alert-red {{
          border: 2px solid #EF4444 !important;
          box-shadow: 0 0 12px rgba(239, 68, 68, 0.8) !important;
        }}
        canvas#camCanvas {{
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
        }}
        video#hiddenVideo {{
          display: none;
        }}

        .hud-overlay {{
          position: absolute;
          top: 4px;
          left: 4px;
          right: 4px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          pointer-events: none;
        }}
        .hud-tag {{
          background: rgba(15, 23, 42, 0.82);
          color: #FFFFFF;
          font-size: 9px;
          font-weight: 700;
          padding: 2px 6px;
          border-radius: 4px;
          backdrop-filter: blur(2px);
          border: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .audio-meter-bar {{
          position: absolute;
          bottom: 4px;
          left: 4px;
          right: 4px;
          height: 4px;
          background: rgba(15, 23, 42, 0.75);
          border-radius: 2px;
          overflow: hidden;
        }}
        .audio-level-fill {{
          height: 100%;
          width: 0%;
          background: linear-gradient(90deg, #10B981, #F59E0B, #EF4444);
          transition: width 0.1s ease;
        }}

        .indicators-grid {{
          margin-top: 6px;
          display: flex;
          flex-direction: column;
          gap: 3px;
          font-size: 10.5px;
          color: #94A3B8;
        }}
        .ind-item {{
          display: flex;
          align-items: center;
          justify-content: space-between;
        }}
        .ind-left {{
          display: flex;
          align-items: center;
          gap: 5px;
        }}
        .dot {{
          width: 6.5px;
          height: 6.5px;
          border-radius: 50%;
          display: inline-block;
        }}
        .dot-green {{ background: #10B981; }}
        .dot-amber {{ background: #F59E0B; }}
        .dot-red {{ background: #EF4444; }}

        /* Dynamic On-Screen Alerts */
        .alert-box {{
          display: none;
          margin-top: 6px;
          padding: 6px 8px;
          border-radius: 6px;
          font-size: 10.5px;
          line-height: 1.35;
          animation: slideDown 0.25s ease;
        }}
        .alert-warning {{
          background: rgba(245, 158, 11, 0.2);
          border: 1px solid #F59E0B;
          color: #FDE68A;
        }}
        .alert-danger {{
          background: rgba(239, 68, 68, 0.25);
          border: 1px solid #EF4444;
          color: #FCA5A5;
        }}
        @keyframes slideDown {{
          from {{ opacity: 0; transform: translateY(-4px); }}
          to {{ opacity: 1; transform: translateY(0); }}
        }}

        .btn-ctrl {{
          background: #3730A3;
          color: white;
          border: 1px solid #4F46E5;
          border-radius: 5px;
          padding: 3px 8px;
          font-size: 10px;
          font-weight: 600;
          cursor: pointer;
        }}
        .btn-ctrl:hover {{
          background: #4F46E5;
        }}
      </style>
    </head>
    <body>
      <div class="shield-card" id="shieldCard">
        <div class="shield-header">
          <div class="shield-title">
            <span>🛡️ AI Proctor Guard</span>
            <span class="pill-badge pill-normal" id="overallStatusBadge">● Normal</span>
          </div>
          <button class="btn-ctrl" onclick="toggleFullscreen()">⛶ Fullscreen</button>
        </div>

        <div class="video-canvas-wrap" id="videoWrap">
          <video id="hiddenVideo" autoplay playsinline muted></video>
          <canvas id="camCanvas" width="320" height="240"></canvas>
          <div class="hud-overlay">
            <span class="hud-tag" id="faceHud">👤 Faces: 1</span>
            <span class="hud-tag" id="tabHud">⚠️ Tab: 0/3</span>
          </div>
          <div class="audio-meter-bar" title="Live Microphone Input Level">
            <div class="audio-level-fill" id="micLevelFill"></div>
          </div>
        </div>

        <!-- Real-time Warning Banner -->
        <div class="alert-box" id="warningBox">
          <strong id="warningTitle">Notice:</strong> <span id="warningMsg"></span>
        </div>

        <!-- Status Indicators -->
        <div class="indicators-grid">
          <div class="ind-item">
            <div class="ind-left">
              <span class="dot dot-green" id="faceDot"></span>
              <span id="faceStatusText">Face Detection: 1 Person (Verified)</span>
            </div>
            <span id="faceCountLabel" style="font-weight: 700; color: #34D399;">1</span>
          </div>
          <div class="ind-item">
            <div class="ind-left">
              <span class="dot dot-green" id="gadgetDot"></span>
              <span id="gadgetStatusText">Gadget Scan: Clear (No phones)</span>
            </div>
            <span id="gadgetLabel" style="color: #34D399; font-weight: 700;">OK</span>
          </div>
          <div class="ind-item">
            <div class="ind-left">
              <span class="dot dot-green" id="tabDot"></span>
              <span id="tabStatusText">Window Focus: Protected</span>
            </div>
            <span id="tabCountLabel" style="font-weight: 700; color: #34D399;">0 switches</span>
          </div>
          <div class="ind-item">
            <div class="ind-left">
              <span class="dot dot-green" id="streamDot"></span>
              <span id="streamStatusText">Sensors: Camera & Mic Active</span>
            </div>
            <span id="streamLabel" style="color: #34D399; font-weight: 700;">LIVE</span>
          </div>
        </div>
      </div>

      <script>
        const sessionId = "{session_id}";
        let mediaStream = null;
        let videoTrack = null;
        let audioTrack = null;
        let audioContext = null;
        let analyser = null;
        let blazefaceModel = null;
        let cocoModel = null;

        // Proctoring State Counters & Persistence
        let tabViolations = 0;
        let lastTabSwitchTime = 0;
        let consecutiveZeroFaces = 0;
        let consecutiveMultiFaces = 0;
        let consecutivePhoneDetected = 0;
        let lastWarningType = "";
        let isArmed = false;

        const video = document.getElementById("hiddenVideo");
        const canvas = document.getElementById("camCanvas");
        const ctx = canvas.getContext("2d");

        // Helper: Record and sync security events to parent and backend
        function recordSecurityEvent(eventType, details) {{
          const eventObj = {{
            sessionId: sessionId,
            event_type: eventType,
            timestamp: new Date().toISOString(),
            details: details || {{}}
          }};

          try {{
            // Store locally in window.parent
            if (window.parent) {{
              window.parent._hirexpSecurityEvents = window.parent._hirexpSecurityEvents || [];
              window.parent._hirexpSecurityEvents.push(eventObj);
              
              // PostMessage to parent
              window.parent.postMessage({{ type: "HIREXP_SEC_EVENT", event: eventObj }}, "*");

              // Keep current URL query param updated for DB persistence on form submit/rerun
              try {{
                const curUrl = new URL(window.parent.location.href);
                curUrl.searchParams.set("sync_event", encodeURIComponent(JSON.stringify(eventObj)));
                window.parent.history.replaceState(null, '', curUrl.toString());
              }} catch(err) {{}}
            }}
          }} catch(e) {{}}
        }}

        // Helper: Display dynamic on-screen alerts
        function showAlert(type, title, message) {{
          const box = document.getElementById("warningBox");
          const t = document.getElementById("warningTitle");
          const m = document.getElementById("warningMsg");
          box.className = "alert-box " + (type === "danger" ? "alert-danger" : "alert-warning");
          t.innerText = title;
          m.innerText = message;
          box.style.display = "block";

          const wrap = document.getElementById("videoWrap");
          if (type === "danger") {{
            wrap.classList.add("alert-red");
          }} else {{
            wrap.classList.remove("alert-red");
          }}

          // Also update overall status pill
          const pill = document.getElementById("overallStatusBadge");
          if (type === "danger") {{
            pill.className = "pill-badge pill-alert";
            pill.innerText = "● Alert";
          }} else if (type === "warning") {{
            pill.className = "pill-badge pill-warn";
            pill.innerText = "● Warning";
          }}
        }}

        function clearAlertIf(typeMatch) {{
          if (lastWarningType === typeMatch) {{
            const box = document.getElementById("warningBox");
            box.style.display = "none";
            document.getElementById("videoWrap").classList.remove("alert-red");
            const pill = document.getElementById("overallStatusBadge");
            pill.className = "pill-badge pill-normal";
            pill.innerText = "● Normal";
            lastWarningType = "";
          }}
        }}

        // ── 1. TAB SWITCHING DETECTION & GRADUATED WARNING SYSTEM ──
        function handleTabSwitch(reason) {{
          if (!isArmed) return;
          const now = Date.now();
          // Debounce: prevent multiple triggers within 3.5 seconds
          if (now - lastTabSwitchTime < 3500) return;
          lastTabSwitchTime = now;

          tabViolations += 1;
          document.getElementById("tabHud").innerText = "⚠️ Tab: " + tabViolations + "/3";
          document.getElementById("tabCountLabel").innerText = tabViolations + " switches";

          const tabDot = document.getElementById("tabDot");
          const tabText = document.getElementById("tabStatusText");

          if (tabViolations === 1) {{
            tabDot.className = "dot dot-amber";
            tabText.innerText = "Tab Focus: Warning 1 issued";
            showAlert("warning", "Warning 1:", "You switched away from the interview window. Please return to your interview.");
            lastWarningType = "tab_1";
            recordSecurityEvent("tab_switch_warning_1", {{
              violation_number: 1,
              reason: reason,
              disqualified: false
            }});
          }} else if (tabViolations === 2) {{
            tabDot.className = "dot dot-amber";
            tabText.innerText = "Tab Focus: Warning 2 issued";
            showAlert("warning", "Warning 2:", "Another tab-switching violation has been detected.");
            lastWarningType = "tab_2";
            recordSecurityEvent("tab_switch_warning_2", {{
              violation_number: 2,
              reason: reason,
              disqualified: false
            }});
          }} else {{
            tabDot.className = "dot dot-red";
            tabText.innerText = "Tab Focus: Flagged for Review";
            showAlert("danger", "Flagged:", "Multiple tab-switching violations detected. Your interview has been flagged for recruiter review.");
            lastWarningType = "tab_flagged";
            recordSecurityEvent("tab_switch_flagged", {{
              violation_number: tabViolations,
              reason: reason,
              flagged_for_recruiter_review: true,
              disqualified: false
            }});
          }}
        }}

        // Window & Document Visibility Listeners (Iframe & Parent)
        document.addEventListener("visibilitychange", function() {{
          if (document.hidden || document.visibilityState === "hidden") {{
            handleTabSwitch("Browser tab hidden");
          }}
        }});
        window.addEventListener("blur", function() {{
          // Verify blur is not momentary dialog
          setTimeout(function() {{
            if (document.hidden || !document.hasFocus()) {{
              handleTabSwitch("Window focus lost or application switched");
            }}
          }}, 400);
        }});

        try {{
          if (window.parent && window.parent.document) {{
            window.parent.document.addEventListener("visibilitychange", function() {{
              if (window.parent.document.hidden || window.parent.document.visibilityState === "hidden") {{
                handleTabSwitch("Parent tab switch detected");
              }}
            }});
            window.parent.addEventListener("blur", function() {{
              setTimeout(function() {{
                if (window.parent.document.hidden || !window.parent.document.hasFocus()) {{
                  handleTabSwitch("Parent window blur or app switch");
                }}
              }}, 400);
            }});
          }}
        }} catch(e) {{}}

        // Fullscreen Change Monitor
        function onFullscreenChanged() {{
          const pDoc = (window.parent && window.parent.document) ? window.parent.document : document;
          if (!pDoc.fullscreenElement && !document.fullscreenElement) {{
            recordSecurityEvent("fullscreen_exit", {{ message: "Candidate exited fullscreen mode" }});
          }}
        }}
        document.addEventListener("fullscreenchange", onFullscreenChanged);
        document.addEventListener("webkitfullscreenchange", onFullscreenChanged);
        try {{
          if (window.parent && window.parent.document) {{
            window.parent.document.addEventListener("fullscreenchange", onFullscreenChanged);
            window.parent.document.addEventListener("webkitfullscreenchange", onFullscreenChanged);
          }}
        }} catch(e) {{}}

        function toggleFullscreen() {{
          try {{
            const pDoc = (window.parent && window.parent.document) ? window.parent.document : document;
            const target = pDoc.documentElement;
            if (!pDoc.fullscreenElement) {{
              target.requestFullscreen().catch(function() {{}});
            }} else {{
              pDoc.exitFullscreen().catch(function() {{}});
            }}
          }} catch(e) {{}}
        }}

        // ── 2. CAMERA & MICROPHONE WEBRTC INITIALIZATION ──
        async function initSensors() {{
          try {{
            mediaStream = await navigator.mediaDevices.getUserMedia({{
              video: {{ width: 320, height: 240, frameRate: 15 }},
              audio: true
            }});
            window._hirexpMediaStream = mediaStream;
            try {{
              if (window.parent) window.parent._hirexpMediaStream = mediaStream;
            }} catch(e) {{}}

            videoTrack = mediaStream.getVideoTracks()[0];
            audioTrack = mediaStream.getAudioTracks()[0];

            video.srcObject = mediaStream;
            video.onloadedmetadata = function() {{
              video.play();
              isArmed = true;
              initAudioMeter(mediaStream);
              loadAIModels();
            }};

            // Monitor Camera Disconnection
            if (videoTrack) {{
              videoTrack.onended = function() {{
                onSensorDisconnected("camera");
              }};
              videoTrack.onmute = function() {{
                onSensorDisconnected("camera");
              }};
              videoTrack.onunmute = function() {{
                onSensorReconnected("camera");
              }};
            }}

            // Monitor Microphone Disconnection
            if (audioTrack) {{
              audioTrack.onended = function() {{
                onSensorDisconnected("microphone");
              }};
              audioTrack.onmute = function() {{
                onSensorDisconnected("microphone");
              }};
              audioTrack.onunmute = function() {{
                onSensorReconnected("microphone");
              }};
            }}

            navigator.mediaDevices.ondevicechange = function() {{
              navigator.mediaDevices.enumerateDevices().then(function(devices) {{
                const hasCam = devices.some(d => d.kind === "videoinput");
                const hasMic = devices.some(d => d.kind === "audioinput");
                if (!hasCam) onSensorDisconnected("camera");
                if (!hasMic) onSensorDisconnected("microphone");
              }}).catch(function() {{}});
            }};

          }} catch(err) {{
            showAlert("danger", "Sensor Error:", "Camera or microphone permission was denied. Please allow access to proceed.");
            recordSecurityEvent("sensor_permission_denied", {{ error: String(err) }});
          }}
        }}

        function onSensorDisconnected(sensorName) {{
          const streamDot = document.getElementById("streamDot");
          const streamText = document.getElementById("streamStatusText");
          const streamLabel = document.getElementById("streamLabel");
          streamDot.className = "dot dot-red";
          streamLabel.innerText = "OFFLINE";
          streamLabel.style.color = "#EF4444";

          if (sensorName === "camera") {{
            streamText.innerText = "Sensors: Camera Disconnected";
            showAlert("danger", "Device Notice:", "Camera disconnected. Please reconnect your camera to continue.");
            recordSecurityEvent("camera_disconnected", {{ timestamp: new Date().toISOString() }});
          }} else {{
            streamText.innerText = "Sensors: Microphone Disconnected";
            showAlert("danger", "Device Notice:", "Microphone disconnected. Please reconnect your microphone.");
            recordSecurityEvent("microphone_disconnected", {{ timestamp: new Date().toISOString() }});
          }}
        }}

        function onSensorReconnected(sensorName) {{
          const streamDot = document.getElementById("streamDot");
          const streamText = document.getElementById("streamStatusText");
          const streamLabel = document.getElementById("streamLabel");
          streamDot.className = "dot dot-green";
          streamText.innerText = "Sensors: Camera & Mic Active";
          streamLabel.innerText = "LIVE";
          streamLabel.style.color = "#34D399";
          clearAlertIf("sensor");
          recordSecurityEvent("sensor_reconnected", {{ sensor: sensorName }});
        }}

        // ── 3. LIVE MICROPHONE VOLUME LEVEL METER (WEB AUDIO API) ──
        function initAudioMeter(stream) {{
          try {{
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            audioContext = new AudioCtx();
            const source = audioContext.createMediaStreamSource(stream);
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 64;
            source.connect(analyser);

            const dataArray = new Uint8Array(analyser.frequencyBinCount);
            const fill = document.getElementById("micLevelFill");

            function updateMeter() {{
              analyser.getByteFrequencyData(dataArray);
              let sum = 0;
              for (let i = 0; i < dataArray.length; i++) {{
                sum += dataArray[i];
              }}
              const avg = sum / dataArray.length;
              // Normalize volume percent
              const pct = Math.min(100, Math.round((avg / 128) * 100));
              fill.style.width = pct + "%";
              requestAnimationFrame(updateMeter);
            }}
            updateMeter();
          }} catch(e) {{}}
        }}

        // ── 4. LOAD AI VISION MODELS (BLAZEFACE & COCO-SSD) ──
        async function loadAIModels() {{
          try {{
            blazefaceModel = await blazeface.load();
            document.getElementById("faceStatusText").innerText = "Face Detection: Vision Active";
          }} catch(e) {{}}

          try {{
            cocoModel = await cocoSsd.load();
            document.getElementById("gadgetStatusText").innerText = "Gadget Scan: Active";
          }} catch(e) {{}}

          // Start continuous analysis loops
          requestAnimationFrame(renderLoop);
          setInterval(runFaceDetection, 550);
          setInterval(runGadgetDetection, 850);
        }}

        // Render Canvas Loop (Mirrored Video + Real-Time Bounding Boxes)
        let lastFaces = [];
        let lastGadgets = [];

        function renderLoop() {{
          if (video.readyState >= 2) {{
            ctx.save();
            // Draw mirrored image
            ctx.translate(canvas.width, 0);
            ctx.scale(-1, 1);
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            ctx.restore();

            // Draw Face Bounding Boxes
            if (lastFaces && lastFaces.length > 0) {{
              const isMulti = lastFaces.length > 1;
              for (let i = 0; i < lastFaces.length; i++) {{
                const f = lastFaces[i];
                // Mirror coordinates because video is mirrored
                const startX = canvas.width - f.bottomRight[0];
                const startY = f.topLeft[1];
                const w = f.bottomRight[0] - f.topLeft[0];
                const h = f.bottomRight[1] - f.topLeft[1];

                ctx.strokeStyle = isMulti ? "#EF4444" : "#10B981";
                ctx.lineWidth = 2.5;
                ctx.strokeRect(startX, startY, w, h);

                ctx.fillStyle = isMulti ? "#EF4444" : "#10B981";
                ctx.font = "bold 10px -apple-system, sans-serif";
                ctx.fillText(isMulti ? "⚠️ Person " + (i+1) : "Candidate", startX + 2, Math.max(12, startY - 4));
              }}
            }}

            // Draw Gadget Bounding Boxes
            if (lastGadgets && lastGadgets.length > 0) {{
              for (let i = 0; i < lastGadgets.length; i++) {{
                const g = lastGadgets[i];
                const startX = canvas.width - (g.bbox[0] + g.bbox[2]);
                const startY = g.bbox[1];
                const w = g.bbox[2];
                const h = g.bbox[3];

                ctx.strokeStyle = "#DC2626";
                ctx.lineWidth = 3;
                ctx.strokeRect(startX, startY, w, h);

                ctx.fillStyle = "#DC2626";
                ctx.font = "bold 10px -apple-system, sans-serif";
                ctx.fillText("📱 " + g.class + " (" + Math.round(g.score * 100) + "%)", startX + 2, Math.max(12, startY - 4));
              }}
            }}
          }}
          requestAnimationFrame(renderLoop);
        }}

        // ── 5. MULTIPLE-PERSON DETECTION ANALYSIS ──
        async function runFaceDetection() {{
          if (!blazefaceModel || video.readyState < 2) return;
          try {{
            const predictions = await blazefaceModel.estimateFaces(video, false);
            lastFaces = predictions || [];
            const count = lastFaces.length;

            document.getElementById("faceCountLabel").innerText = count;
            document.getElementById("faceHud").innerText = count > 1 ? "🚨 Faces: " + count : "👤 Faces: " + count;

            const faceDot = document.getElementById("faceDot");
            const faceText = document.getElementById("faceStatusText");

            if (count === 1) {{
              consecutiveZeroFaces = 0;
              consecutiveMultiFaces = 0;
              faceDot.className = "dot dot-green";
              faceText.innerText = "Face Detection: 1 Person (Verified)";
              clearAlertIf("face");
            }} else if (count === 0) {{
              consecutiveZeroFaces += 1;
              consecutiveMultiFaces = 0;
              if (consecutiveZeroFaces >= 4) {{
                faceDot.className = "dot dot-amber";
                faceText.innerText = "Face Detection: No Face Visible";
                showAlert("warning", "Face Visibility:", "No face detected. Please remain visible during the interview.");
                lastWarningType = "face";
                if (consecutiveZeroFaces === 4) {{
                  recordSecurityEvent("no_face_detected", {{ consecutive_cycles: consecutiveZeroFaces }});
                }}
              }}
            }} else {{
              consecutiveMultiFaces += 1;
              consecutiveZeroFaces = 0;
              if (consecutiveMultiFaces >= 3) {{
                faceDot.className = "dot dot-red";
                faceText.innerText = "Face Detection: Multiple Faces (" + count + ")";
                showAlert("danger", "Integrity Notice:", "Multiple people detected. Only one candidate is permitted during the interview.");
                lastWarningType = "face";
                if (consecutiveMultiFaces === 3) {{
                  recordSecurityEvent("multiple_people_detected", {{ face_count: count }});
                }}
              }}
            }}
          }} catch(e) {{}}
        }}

        // ── 6. MOBILE PHONE & GADGET DETECTION (COCO-SSD) ──
        const PROHIBITED_CLASSES = ["cell phone", "laptop", "remote", "tv", "tablet"];

        async function runGadgetDetection() {{
          if (!cocoModel || video.readyState < 2) return;
          try {{
            const predictions = await cocoModel.detect(video);
            const suspicious = predictions.filter(p => PROHIBITED_CLASSES.includes(p.class.toLowerCase()) && p.score >= 0.52);
            lastGadgets = suspicious;

            const gDot = document.getElementById("gadgetDot");
            const gText = document.getElementById("gadgetStatusText");
            const gLabel = document.getElementById("gadgetLabel");

            if (suspicious.length > 0) {{
              consecutivePhoneDetected += 1;
              if (consecutivePhoneDetected >= 2) {{
                const top = suspicious[0];
                const isPhone = top.class.toLowerCase() === "cell phone";
                gDot.className = "dot dot-red";
                gLabel.innerText = "DETECTED";
                gLabel.style.color = "#EF4444";

                if (isPhone) {{
                  gText.innerText = "Gadget Scan: Mobile Phone Detected";
                  showAlert("danger", "Device Prohibited:", "Mobile Phone Detected! Electronic devices are not allowed during the interview.");
                  lastWarningType = "gadget";
                  if (consecutivePhoneDetected === 2) {{
                    recordSecurityEvent("mobile_phone_detected", {{ object: top.class, confidence: Math.round(top.score * 100) }});
                  }}
                }} else {{
                  gText.innerText = "Gadget Scan: " + top.class + " Detected";
                  showAlert("danger", "Device Prohibited:", "Unauthorized electronic device detected. Please remove it from the interview area.");
                  lastWarningType = "gadget";
                  if (consecutivePhoneDetected === 2) {{
                    recordSecurityEvent("unauthorized_gadget_detected", {{ object: top.class, confidence: Math.round(top.score * 100) }});
                  }}
                }}
              }}
            }} else {{
              consecutivePhoneDetected = 0;
              gDot.className = "dot dot-green";
              gText.innerText = "Gadget Scan: Clear (No devices)";
              gLabel.innerText = "OK";
              gLabel.style.color = "#34D399";
              clearAlertIf("gadget");
            }}
          }} catch(e) {{}}
        }}

        // ── 7. COPY, PASTE & KEYBOARD RESTRICTIONS ──
        function hookParentRestrictions() {{
          try {{
            const pDoc = (window.parent && window.parent.document) ? window.parent.document : document;
            const pWin = window.parent || window;

            // Restrict paste into answer textareas
            pDoc.addEventListener("paste", function(e) {{
              const target = e.target;
              if (target && (target.tagName === "TEXTAREA" || target.tagName === "INPUT")) {{
                e.preventDefault();
                showAlert("warning", "Paste Disabled:", "Pasting is disabled in protected answer fields. Please type or speak your answer.");
                lastWarningType = "paste";
                recordSecurityEvent("paste_attempt", {{ field_tag: target.tagName }});
              }}
            }}, true);

            // Restrict copy / cut
            pDoc.addEventListener("copy", function(e) {{
              e.preventDefault();
              recordSecurityEvent("copy_attempt", {{}});
            }}, true);
            pDoc.addEventListener("cut", function(e) {{
              e.preventDefault();
              recordSecurityEvent("cut_attempt", {{}});
            }}, true);

            // Context menu restriction
            pDoc.addEventListener("contextmenu", function(e) {{
              e.preventDefault();
            }}, true);

            // Monitor Keyboard Shortcuts & DevTools attempts
            pWin.addEventListener("keydown", function(e) {{
              // F12 or Ctrl+Shift+I / J / C or Ctrl+U
              if (e.key === "F12" || (e.ctrlKey && e.shiftKey && ["I", "J", "C", "i", "j", "c"].includes(e.key)) || (e.ctrlKey && ["u", "U"].includes(e.key))) {{
                e.preventDefault();
                recordSecurityEvent("devtools_open_attempt", {{ key: e.key }});
              }}
              // Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+P, Ctrl+S
              if (e.ctrlKey && ["c", "v", "x", "p", "s", "C", "V", "X", "P", "S"].includes(e.key)) {{
                if (["p", "P", "s", "S"].includes(e.key)) {{
                  e.preventDefault();
                }}
                recordSecurityEvent("restricted_shortcut_attempt", {{ key: e.key }});
              }}
            }}, true);

          }} catch(e) {{}}
        }}

        // Start initialization
        initSensors();
        hookParentRestrictions();
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=330)
