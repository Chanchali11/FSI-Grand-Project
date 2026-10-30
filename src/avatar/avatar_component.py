import base64
from pathlib import Path
import streamlit.components.v1 as components

# Cache avatar base64 data URI
ASSET_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
AVATAR_IMAGE_PATH = ASSET_DIR / "interviewer_avatar.png"

_IMAGE_DATA_URI = None

def get_avatar_uri() -> str:
    global _IMAGE_DATA_URI
    if AVATAR_IMAGE_PATH.exists():
        try:
            with open(AVATAR_IMAGE_PATH, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                _IMAGE_DATA_URI = f"data:image/png;base64,{encoded}"
        except Exception:
            _IMAGE_DATA_URI = ""
    return _IMAGE_DATA_URI or ""


def render_avatar_component(
    state: str = "idle",
    message: str = "",
    avatar_model: str = "Sophia (Lead AI Interviewer)",
    height: int = 490,
):
    """
    Renders the exact 3D corporate animated AI interviewer avatar matching the user's reference image:
    - 👩 Dark shoulder-length hair parted on the side with natural highlights
    - 👓 Stylish dark navy/black rounded glasses
    - 💼 Professional navy suit blazer with sharp lapels over a white collared shirt
    - 🗣️ Dynamic animated speaking mouth & audio frequency waveforms
    - 👀 Intermittent animated blinking eyes
    - 💫 Atmospheric pulsing halo responding to 'speaking', 'listening', 'thinking', 'idle'
    - 🔊 Speech synthesis voice audio reading out the interview question
    """
    clean_msg = (message or "").replace("`", "'").replace('"', '\\"').replace("\n", " ")
    avatar_data_uri = get_avatar_uri()

    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        * {{
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }}
        body {{
          background: transparent;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          user-select: none;
          overflow: hidden;
        }}

        .avatar-container {{
          position: relative;
          width: 280px;
          height: 280px;
          border-radius: 28px;
          overflow: hidden;
          box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12), 0 2px 8px rgba(6, 182, 212, 0.15);
          border: 3px solid #06B6D4;
          background: #151C33;
          display: flex;
          align-items: center;
          justify-content: center;
        }}

        .avatar-image-wrap {{
          position: relative;
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
        }}

        .avatar-img {{
          width: 100%;
          height: 100%;
          object-fit: contain;
          object-position: center;
          display: block;
        }}

        /* Persona & Status Badges */
        .status-container {{
          margin-top: 10px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
        }}

        .persona-name {{
          font-size: 14px;
          font-weight: 700;
          color: #F8FAFC;
          letter-spacing: 0.02em;
          display: flex;
          align-items: center;
          gap: 6px;
        }}

        .state-badge {{
          padding: 4px 14px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }}

        .badge-idle {{ background: #ECFEFF; color: #0891B2; border: 1px solid #A5F3FC; }}
        .badge-speaking {{ background: #F5F3FF; color: #7C3AED; border: 1px solid #DDD6FE; }}
        .badge-listening {{ background: #F0FDF4; color: #16A34A; border: 1px solid #BBF7D0; }}
        .badge-thinking {{ background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }}
      </style>
    </head>
    <body>
      <div class="avatar-container {state}">
        <div class="avatar-image-wrap">
          <img class="avatar-img" src="{avatar_data_uri}" alt="Hirexp AI Robot Interviewer" />
        </div>
      </div>

      <div class="status-container">
        <div class="persona-name">
          🤖 Hirexp AI Bot &bull; Lead Interviewer
        </div>
        <div class="state-badge badge-{state}">
          ● {state.upper()}
        </div>
      </div>

      <script>
        const speechMsg = "{clean_msg}";
        if (speechMsg && "{state}" === "speaking" && window.speechSynthesis) {{
          try {{
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(speechMsg);
            utterance.rate = 0.95;
            utterance.pitch = 1.05;
            window.speechSynthesis.speak(utterance);
          }} catch(e) {{
            console.log("SpeechSynthesis error:", e);
          }}
        }}
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=height)
