import base64
import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import PlainTextResponse, HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.rest import Client
import google.generativeai as genai

# Load environment variables
load_dotenv()

# --- Configurations ---
app = FastAPI()

# Twilio credentials from .env or inline (for testing only)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID") or "ACe3080e7c3670d0bd8cc38bf5bd0924d2"
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN") or "96849b488f0a8355791227462684aba0"
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyBVnNNltQB39PuUqxo8lO7nT8XldMBGoUI"
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-pro")


# --- AI Functions ---

def speech_to_text(audio_chunk_b64):
    # Dummy STT: Replace with Whisper or real service
    print("STT received audio chunk")
    return "Hello, what is the weather in Mumbai?"


def get_llm_response(text: str) -> str:
    print(f"LLM Request: {text}")
    try:
        prompt = f"You are a friendly assistant. The user asked: '{text}'. Reply shortly."
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return "Sorry, I am having trouble thinking right now."


def text_to_speech(text: str) -> bytes:
    # Dummy TTS: Returns base64 encoded silent/hello audio
    print(f"TTS converting: {text}")
    dummy_audio_b64 = "//u/9/7//P/7//v/8//n/8//j/9//r/+f/1/+v/5//X/6//n/9f/p/+f/z/+//4//f/8//v/8//j/+f/5//f/6//f/8/A="
    return base64.b64decode(dummy_audio_b64)


# --- Routes ---

@app.get("/")
def index():
    return HTMLResponse("<h1>✅ Gemini Voice Assistant Running</h1>")


@app.post("/voice", response_class=PlainTextResponse)
async def voice_handler(request: Request):
    print("📞 Incoming voice call")
    # Fixed ngrok domain (edit below)
    ws_url = "https://twilio-voice-bot-dr96.onrender.com/voicebot"

    response = VoiceResponse()
    connect = Connect()
    connect.stream(url=ws_url)
    response.append(connect)
    response.say(voice="alice", message="Connecting you to the Gemini assistant.")

    return str(response)


@app.websocket("/ws")
async def websocket_handler(websocket: WebSocket):
    await websocket.accept()
    print("🌐 WebSocket connected")

    try:
        stream_sid = ""
        while True:
            message = await websocket.receive_text()
            packet = json.loads(message)

            if packet['event'] == 'start':
                stream_sid = packet['start']['streamSid']
                print(f"🎤 Stream started (SID: {stream_sid})")

            elif packet['event'] == 'media':
                audio_chunk = packet['media']['payload']
                user_text = speech_to_text(audio_chunk)

                if user_text:
                    reply = get_llm_response(user_text)
                    bot_audio = text_to_speech(reply)
                    response_packet = {
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {"payload": base64.b64encode(bot_audio).decode("utf-8")}
                    }
                    await websocket.send_text(json.dumps(response_packet))
                    print("🗣️ Sent Gemini response")

            elif packet['event'] == 'stop':
                print("🛑 Call ended")
                break

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print("🔌 WebSocket closed")
