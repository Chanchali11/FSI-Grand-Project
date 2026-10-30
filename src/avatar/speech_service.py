import streamlit.components.v1 as components


class SpeechService:
    """
    Provides client-side browser speech synthesis (TTS) for the AI Interviewer,
    and HTML5 MediaRecorder + Web Speech API for candidate audio recording and transcription.
    """

    @staticmethod
    def render_speech_controls(text_to_speak: str = ""):
        """Browser speech synthesis controls allowing candidate to replay question aloud or pause."""
        clean_text = (text_to_speak or "").replace("`", "'").replace('"', '\\"').replace("\n", " ")
        js_code = f"""
        <div style="display: flex; gap: 8px; margin-top: 10px; justify-content: center;">
          <button id="ttsBtn" onclick="speakText()" style="
            background: #4F46E5; color: white; border: none; border-radius: 8px; padding: 7px 14px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 13px; font-family: -apple-system, sans-serif; box-shadow: 0 1px 2px rgba(79, 70, 229, 0.2);
          ">
            🔊 Replay Question
          </button>
          <button id="stopTtsBtn" onclick="stopSpeech()" style="
            background: #F1F5F9; color: #475569; border: 1px solid #E2E8F0; border-radius: 8px; padding: 7px 14px; font-weight: 600; cursor: pointer; font-size: 13px; font-family: -apple-system, sans-serif;
          ">
            ⏹ Stop Voice
          </button>
        </div>

        <script>
          function speakText() {{
            if ('speechSynthesis' in window) {{
              window.speechSynthesis.cancel();
              const text = "{clean_text}";
              const utterance = new SpeechSynthesisUtterance(text);
              utterance.rate = 1.0;
              window.speechSynthesis.speak(utterance);
            }}
          }}

          function stopSpeech() {{
            if ('speechSynthesis' in window) {{
              window.speechSynthesis.cancel();
            }}
          }}
        </script>
        """
        components.html(js_code, height=52)

    @staticmethod
    def render_audio_recorder_and_transcriber(session_key: str = "q_rec"):
        """
        High-performance in-browser audio recorder and real-time speech transcriber.
        Uses MediaRecorder API for audio capture & Web Speech Recognition for live text transcription.
        Allows instant one-click copy/transfer into the candidate answer area.
        """
        html_code = f"""
        <div style="background: #19223C; border: 1px solid #232D4B; border-radius: 10px; padding: 14px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
          <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span id="recStatusDot" style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #94A3B8;"></span>
              <span id="recStatusText" style="font-weight: 600; color: #F8FAFC; font-size: 13px;">Microphone Ready</span>
              <span id="recTimer" style="font-size: 12px; color: #94A3B8; font-weight: 600; display: none;">00:00</span>
            </div>
            <div style="display: flex; gap: 6px;">
              <button id="startRecBtn" onclick="startRecording()" style="
                background: #16A34A; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 4px;
              ">
                🎙 Start Speaking
              </button>
              <button id="stopRecBtn" onclick="stopRecording()" disabled style="
                background: #DC2626; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 700; cursor: pointer; display: none;
              ">
                ⏹ Stop & Transcribe
              </button>
              <button id="copyBtn" onclick="copyTranscript()" style="
                background: #232D4B; color: #E2E8F0; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; font-size: 12px; font-weight: 600; cursor: pointer;
              ">
                📋 Copy Transcript
              </button>
            </div>
          </div>

          <div id="transcriptBox" style="min-height: 48px; max-height: 100px; overflow-y: auto; background: #151C33; border: 1px solid #232D4B; border-radius: 6px; padding: 8px 10px; font-size: 12.5px; color: #F8FAFC; line-height: 1.45;">
            <span id="placeholderText" style="color: #94A3B8; font-style: italic;">Your speech transcription will appear here in real-time as you speak...</span>
            <span id="recognizedText" style="font-weight: 500;"></span>
          </div>
          
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
            <span style="font-size: 11px; color: #94A3B8;">Supported in Chrome, Edge, Safari & Firefox via Web Speech & MediaRecorder</span>
            <span id="copyConfirm" style="font-size: 11px; color: #16A34A; font-weight: 600; display: none;">✓ Copied to clipboard!</span>
          </div>
        </div>

        <script>
          let mediaRecorder = null;
          let audioChunks = [];
          let recognition = null;
          let timerInterval = null;
          let seconds = 0;
          let fullTranscript = "";

          // Initialize Web Speech API if supported
          const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
          if (SpeechRecognition) {{
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onresult = (event) => {{
              let interim = '';
              for (let i = event.resultIndex; i < event.results.length; ++i) {{
                if (event.results[i].isFinal) {{
                  fullTranscript += event.results[i][0].transcript + ' ';
                }} else {{
                  interim += event.results[i][0].transcript;
                }}
              }}
              const disp = document.getElementById('recognizedText');
              const ph = document.getElementById('placeholderText');
              if (ph) ph.style.display = 'none';
              disp.innerText = fullTranscript + (interim ? '(' + interim + ')' : '');
            }};

            recognition.onerror = (e) => {{
              console.log('Recognition event:', e.error);
            }};
          }}

          async function startRecording() {{
            try {{
              const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
              mediaRecorder = new MediaRecorder(stream);
              audioChunks = [];
              fullTranscript = "";
              document.getElementById('recognizedText').innerText = "";
              document.getElementById('placeholderText').style.display = 'none';

              mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
              mediaRecorder.start();

              if (recognition) {{
                try {{ recognition.start(); }} catch(err) {{}}
              }}

              // Update UI
              document.getElementById('startRecBtn').style.display = 'none';
              const stopBtn = document.getElementById('stopRecBtn');
              stopBtn.style.display = 'inline-block';
              stopBtn.disabled = false;
              
              const dot = document.getElementById('recStatusDot');
              dot.style.background = '#DC2626';
              dot.style.boxShadow = '0 0 8px #DC2626';
              document.getElementById('recStatusText').innerText = 'Recording Candidate Voice...';
              
              const timerEl = document.getElementById('recTimer');
              timerEl.style.display = 'inline-block';
              seconds = 0;
              timerInterval = setInterval(() => {{
                seconds++;
                const mins = String(Math.floor(seconds / 60)).padStart(2, '0');
                const secs = String(seconds % 60).padStart(2, '0');
                timerEl.innerText = mins + ':' + secs;
              }}, 1000);

            }} catch(err) {{
              alert('Microphone access denied or unavailable: ' + err.message);
            }}
          }}

          function stopRecording() {{
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
              mediaRecorder.stop();
              mediaRecorder.stream.getTracks().forEach(t => t.stop());
            }}
            if (recognition) {{
              try {{ recognition.stop(); }} catch(err) {{}}
            }}
            clearInterval(timerInterval);

            // Update UI
            document.getElementById('startRecBtn').style.display = 'inline-block';
            document.getElementById('stopRecBtn').style.display = 'none';
            const dot = document.getElementById('recStatusDot');
            dot.style.background = '#16A34A';
            dot.style.boxShadow = 'none';
            document.getElementById('recStatusText').innerText = 'Audio Captured & Transcribed';
          }}

          function copyTranscript() {{
            const text = document.getElementById('recognizedText').innerText || fullTranscript;
            if (text.trim()) {{
              navigator.clipboard.writeText(text.trim()).then(() => {{
                const conf = document.getElementById('copyConfirm');
                conf.style.display = 'inline-block';
                setTimeout(() => conf.style.display = 'none', 3000);
              }});
            }} else {{
              alert('No transcription available yet. Start speaking to generate text.');
            }}
          }}
        </script>
        """
        components.html(html_code, height=140)
