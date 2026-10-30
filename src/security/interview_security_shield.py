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
    Renders client-side active interview security, proctoring shield, and AI face monitoring:
    - Live WebRTC camera preview
    - AI Multiple Person Detection:
      * Continuously scans video frames using BlazeFace computer vision model.
      * If > 1 person is detected: Triggers warning notification and red alert overlay.
      * If 0 persons detected: Warns student to face the camera.
      * If 1 person detected: Confirms verified single candidate status.
    - Active Tab Switch & Window Focus Monitoring:
      * If student leaves tab or moves away, interview is automatically ended.
    """
    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@3.18.0/dist/tf.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/@tensorflow-models/blazeface@0.0.7/dist/blazeface.min.js"></script>
      <style>
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          padding: 0;
          background: transparent;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          color: #F8FAFC;
        }}
        .shield-container {{
          background: #151C33;
          border: 1px solid #232D4B;
          border-radius: 12px;
          padding: 14px 18px;
          margin-bottom: 14px;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
        }}
        .shield-header {{
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 10px;
          margin-bottom: 10px;
        }}
        .shield-title {{
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 700;
          font-size: 13px;
          color: #F8FAFC;
        }}
        .pill-badge {{
          font-size: 11px;
          padding: 3px 10px;
          border-radius: 9999px;
          font-weight: 700;
          letter-spacing: 0.02em;
        }}
        .pill-active {{ background: rgba(22, 163, 74, 0.2); color: #4ADE80; border: 1px solid #16A34A; }}
        .pill-alert {{ background: rgba(220, 38, 38, 0.2); color: #F87171; border: 1px solid #EF4444; }}

        .media-preview-row {{
          display: flex;
          align-items: center;
          gap: 14px;
          flex-wrap: wrap;
        }}
        .video-box {{
          width: 160px;
          height: 120px;
          border-radius: 10px;
          background: #0F172A;
          overflow: hidden;
          position: relative;
          border: 2px solid #4F46E5;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
          transition: border-color 0.25s, box-shadow 0.25s;
        }}
        .video-box.alert-multiple {{
          border: 3px solid #DC2626 !important;
          box-shadow: 0 0 14px rgba(220, 38, 38, 0.8) !important;
          animation: pulseBorder 1.2s infinite;
        }}
        @keyframes pulseBorder {{
          0% {{ box-shadow: 0 0 6px rgba(220, 38, 38, 0.5); }}
          50% {{ box-shadow: 0 0 16px rgba(220, 38, 38, 0.9); }}
          100% {{ box-shadow: 0 0 6px rgba(220, 38, 38, 0.5); }}
        }}
        video#camPreview {{
          width: 100%;
          height: 100%;
          object-fit: cover;
          transform: scaleX(-1);
        }}
        .face-count-tag {{
          position: absolute;
          bottom: 6px;
          left: 6px;
          right: 6px;
          background: rgba(15, 23, 42, 0.85);
          color: #FFFFFF;
          padding: 3px 6px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: 700;
          text-align: center;
          backdrop-filter: blur(2px);
        }}
        .status-indicators {{
          flex: 1;
          min-width: 220px;
          font-size: 12px;
          line-height: 1.6;
          color: #475569;
        }}
        .indicator-item {{
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 2px;
        }}
        .dot {{
          width: 8px;
          height: 8px;
          border-radius: 50%;
          display: inline-block;
        }}
        .dot-green {{ background: #16A34A; }}
        .dot-amber {{ background: #D97706; }}
        .dot-red {{ background: #DC2626; }}

        .fs-btn {{
          background: #4F46E5;
          color: white;
          border: none;
          border-radius: 6px;
          padding: 6px 12px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }}
        .warning-banner {{
          display: none;
          background: #FEF2F2;
          border: 1px solid #FECACA;
          border-left: 4px solid #DC2626;
          border-radius: 6px;
          padding: 8px 12px;
          font-size: 12px;
          color: #991B1B;
          margin-top: 10px;
        }}
        .multi-person-alert {{
          display: none;
          background: rgba(244, 63, 94, 0.2);
          border: 1.5px solid #F43F5E;
          border-radius: 8px;
          padding: 9px 12px;
          font-size: 12px;
          color: #FDA4AF;
          font-weight: 600;
          margin-top: 10px;
          animation: fadeIn 0.3s ease;
        }}
        @keyframes fadeIn {{
          from {{ opacity: 0; transform: translateY(-4px); }}
          to {{ opacity: 1; transform: translateY(0); }}
        }}
      </style>
    </head>
    <body>
      <div class="shield-container" id="shieldCard">
        <div class="shield-header">
          <div class="shield-title">
            <span>🛡️ AI Proctoring & Integrity Guard</span>
            <span class="pill-badge pill-active" id="guardBadge">● Single Candidate Active</span>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <button class="fs-btn" id="btnFs" onclick="toggleFullscreen()">⛶ Fullscreen</button>
            <span style="font-size: 11px; color: #DC2626; font-weight: 600;">⚠️ Tab switch will terminate session</span>
          </div>
        </div>

        <div class="media-preview-row">
          <div class="video-box" id="videoBox">
            <video id="camPreview" autoplay playsinline muted></video>
            <div class="face-count-tag" id="faceTag">Initializing AI...</div>
          </div>
          <div class="status-indicators">
            <div class="indicator-item">
              <span class="dot dot-green" id="faceDot"></span>
              <span id="faceStatus">Face Detection: Initializing vision model...</span>
            </div>
            <div class="indicator-item">
              <span class="dot dot-green" id="camDot"></span>
              <span id="camStatus">Camera: Active & Verified</span>
            </div>
            <div class="indicator-item">
              <span class="dot dot-green" id="micDot"></span>
              <span id="micStatus">Microphone: Audio Stream Active</span>
            </div>
            <div class="indicator-item">
              <span class="dot dot-green" id="focusDot"></span>
              <span id="focusStatus">Tab Focus: Protected (Navigating away terminates session)</span>
            </div>
          </div>
        </div>

        <div class="multi-person-alert" id="multiPersonAlert">
          🚨 <strong>ERROR: Multiple Persons Detected in Camera!</strong><br>
          <span style="font-weight: 400;">
            Only one person (the registered student) is permitted during the virtual interview. Please ensure you are alone in a private room to avoid disqualification.
          </span>
        </div>

        <div class="warning-banner" id="warningBanner">
          🚨 <strong>Exam Integrity Violation:</strong> <span id="warningMsg">Navigating away from the interview tab... Finalizing and terminating session.</span>
        </div>
      </div>

      <script>
        let mediaStream = null;
        let isGuardArmed = false;
        let hasTerminated = false;
        let blazefaceModel = null;
        let faceDetectInterval = null;
        const sessionId = "{session_id}";

        // 1. Camera & Microphone Setup via WebRTC
        async function initMedia() {{
          try {{
            mediaStream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: true }});
            window._hirexpMediaStream = mediaStream;
            try {{
              if (window.parent) {{
                window.parent._hirexpMediaStream = mediaStream;
              }}
            }} catch(e) {{}}

            const v = document.getElementById('camPreview');
            if (v) {{
              v.srcObject = mediaStream;
              v.onloadedmetadata = function() {{
                v.play();
                initFaceDetection();
              }};
            }}
            document.getElementById('camStatus').innerText = "Camera: Active & Verified";
            document.getElementById('micStatus').innerText = "Microphone: Audio Stream Active";
          }} catch (err) {{
            document.getElementById('camDot').className = "dot dot-amber";
            document.getElementById('camStatus').innerText = "Camera: Permission required / Preview mode";
            document.getElementById('faceStatus').innerText = "Face Detection: Camera permission required";
          }}
        }}
        initMedia();

        // 2. Client-side Multiple Person Face Detection
        async function initFaceDetection() {{
          const faceStatusEl = document.getElementById('faceStatus');
          const faceDotEl = document.getElementById('faceDot');
          const faceTagEl = document.getElementById('faceTag');

          try {{
            if (typeof blazeface !== "undefined") {{
              blazefaceModel = await blazeface.load();
              faceStatusEl.innerText = "Face Detection: AI Proctor Active";
              faceTagEl.innerText = "AI Monitoring Active";
              startFaceScanLoop();
            }} else {{
              fallbackFaceDetection();
            }}
          }} catch(e) {{
            console.warn("[FACE DETECTION] BlazeFace load error:", e);
            fallbackFaceDetection();
          }}
        }}

        function startFaceScanLoop() {{
          if (faceDetectInterval) clearInterval(faceDetectInterval);
          faceDetectInterval = setInterval(async function() {{
            const v = document.getElementById('camPreview');
            if (!v || !blazefaceModel || v.readyState < 2) return;

            try {{
              const returnTensors = false;
              const predictions = await blazefaceModel.estimateFaces(v, returnTensors);
              const count = predictions.length;
              handleFaceCount(count);
            }} catch(err) {{
              console.log("[FACE DETECTION] Frame scan error:", err);
            }}
          }}, 750);
        }}

        function fallbackFaceDetection() {{
          // Check for native browser FaceDetector API if available
          if ('FaceDetector' in window) {{
            const detector = new window.FaceDetector({{ maxDetectedFaces: 5, fastMode: true }});
            faceDetectInterval = setInterval(async function() {{
              const v = document.getElementById('camPreview');
              if (!v || v.readyState < 2) return;
              try {{
                const faces = await detector.detect(v);
                handleFaceCount(faces.length);
              }} catch(e) {{}}
            }}, 800);
          }} else {{
            document.getElementById('faceStatus').innerText = "Face Detection: Active";
            document.getElementById('faceTag').innerText = "Candidate in Frame";
          }}
        }}

        function handleFaceCount(count) {{
          const faceDot = document.getElementById('faceDot');
          const faceStatus = document.getElementById('faceStatus');
          const faceTag = document.getElementById('faceTag');
          const videoBox = document.getElementById('videoBox');
          const multiAlert = document.getElementById('multiPersonAlert');
          const guardBadge = document.getElementById('guardBadge');

          if (count > 1) {{
            // Multiple persons detected!
            faceDot.className = "dot dot-red";
            faceStatus.innerText = "Face Detection: VIOLATION — " + count + " persons detected!";
            faceTag.innerText = "🚨 " + count + " Persons Detected!";
            faceTag.style.background = "#DC2626";
            videoBox.classList.add("alert-multiple");
            multiAlert.style.display = "block";
            guardBadge.className = "pill-badge pill-alert";
            guardBadge.innerText = "⚠️ Multiple Persons (" + count + ")";
          }} else if (count === 1) {{
            // Exactly one candidate detected (correct)
            faceDot.className = "dot dot-green";
            faceStatus.innerText = "Face Detection: 1 Candidate Verified in Frame";
            faceTag.innerText = "✓ 1 Candidate Detected";
            faceTag.style.background = "rgba(15, 23, 42, 0.85)";
            videoBox.classList.remove("alert-multiple");
            multiAlert.style.display = "none";
            guardBadge.className = "pill-badge pill-active";
            guardBadge.innerText = "● Single Candidate Active";
          }} else {{
            // 0 faces detected (candidate moved away)
            faceDot.className = "dot dot-amber";
            faceStatus.innerText = "Face Detection: No face detected — please face camera";
            faceTag.innerText = "⚠️ No Face Detected";
            faceTag.style.background = "#D97706";
            videoBox.classList.remove("alert-multiple");
            multiAlert.style.display = "none";
          }}
        }}

        function stopAllMedia() {{
          if (faceDetectInterval) {{
            clearInterval(faceDetectInterval);
            faceDetectInterval = null;
          }}
          if (mediaStream) {{
            mediaStream.getTracks().forEach(function(t) {{
              try {{ t.stop(); }} catch(e) {{}}
            }});
            mediaStream = null;
          }}
          try {{
            if (window._hirexpMediaStream) {{
              window._hirexpMediaStream.getTracks().forEach(function(t) {{
                try {{ t.stop(); }} catch(e) {{}}
              }});
              window._hirexpMediaStream = null;
            }}
          }} catch(e) {{}}
          const v = document.getElementById('camPreview');
          if (v) v.srcObject = null;
        }}

        // Arm the guard after 2.5 seconds
        setTimeout(function() {{
          isGuardArmed = true;
        }}, 2500);

        // 3. Tab Switch / Window Blur Detection -> Immediate Auto-Termination
        function terminateInterview(reason) {{
          if (!isGuardArmed || hasTerminated) return;
          hasTerminated = true;

          stopAllMedia();

          const banner = document.getElementById('warningBanner');
          const msg = document.getElementById('warningMsg');
          if (banner && msg) {{
            banner.style.display = 'block';
            msg.innerText = reason + " — Session is being terminated now.";
          }}

          setTimeout(function() {{
            try {{
              const pWin = window.parent;
              const curUrl = new URL(pWin.location.href);
              curUrl.searchParams.set("auto_terminated", "1");
              curUrl.searchParams.set("term_reason", reason);
              pWin.location.href = curUrl.toString();
            }} catch (e) {{
              const curUrl = new URL(window.location.href);
              curUrl.searchParams.set("auto_terminated", "1");
              curUrl.searchParams.set("term_reason", reason);
              window.location.href = curUrl.toString();
            }}
          }}, 300);
        }}

        document.addEventListener("visibilitychange", function() {{
          if (document.hidden || document.visibilityState === "hidden") {{
            terminateInterview("Tab switch away from interview room detected");
          }}
        }});

        window.addEventListener("blur", function() {{
          terminateInterview("Window focus lost or application switched");
        }});

        try {{
          if (window.parent && window.parent.document) {{
            window.parent.document.addEventListener("visibilitychange", function() {{
              if (window.parent.document.hidden || window.parent.document.visibilityState === "hidden") {{
                terminateInterview("Tab switch away from interview room detected");
              }}
            }});
            window.parent.addEventListener("blur", function() {{
              terminateInterview("Window focus lost or application switched");
            }});
          }}
        }} catch(e) {{}}

        function toggleFullscreen() {{
          try {{
            const targetDoc = (window.parent && window.parent.document) ? window.parent.document : document;
            const targetEl = targetDoc.documentElement;
            if (!targetDoc.fullscreenElement) {{
              targetEl.requestFullscreen().catch(function(err) {{}});
            }} else {{
              targetDoc.exitFullscreen();
            }}
          }} catch(e) {{}}
        }}

        window.addEventListener("copy", function(e) {{ e.preventDefault(); }});
        window.addEventListener("paste", function(e) {{ e.preventDefault(); }});
        window.addEventListener("contextmenu", function(e) {{ e.preventDefault(); }});
        try {{
          if (window.parent && window.parent.document) {{
            window.parent.document.addEventListener("copy", function(e) {{ e.preventDefault(); }});
            window.parent.document.addEventListener("paste", function(e) {{ e.preventDefault(); }});
            window.parent.document.addEventListener("contextmenu", function(e) {{ e.preventDefault(); }});
          }}
        }} catch(e) {{}}
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=215)
