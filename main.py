import os
import base64
import json
import tempfile
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
import whisper
from transformers import AutoModelForCausalLM, AutoTokenizer
from TTS.api import TTS
import soundfile as sf
import numpy as np

# Load environment variables
load_dotenv()
TWILIO_ACCOUNT_SID = "ACe3080e7c3670d0bd8cc38bf5bd0924d2"
TWILIO_AUTH_TOKEN = "5888201f8aca6f08c09dcd9dd6a794df"
RENDER_DOMAIN = "https://twilio-voice-bot-dr96.onrender.com""

# Initialize FastAPI App
app = FastAPI()

# Load Models on Startup
print("⏳ Loading Whisper STT...")
whisper_model = whisper.load_model("base")

print("⏳ Loading TinyLlama...")
tokenizer = AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
llm = AutoModelForCausalLM.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")

print("⏳ Loading Coqui TTS...")
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

# Utilities
def transcribe_audio(file_path):
    return whisper_model.transcribe(file_path)["text"]

def generate_response(prompt):
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = llm.generate(**inputs, max_new_tokens=100)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

def synthesize_speech(text):
    audio_array = tts.tts(text)
    return audio_array, tts.synthesizer.output_sample_rate

# Health Check for Render
@app.get("/")
async def health_check():
    return {"status": "ok"}

# Twilio Voice Webhook
@app.post("/voicebot", response_class=PlainTextResponse)
async def voicebot(request: Request):
    ws_url = f"wss://{RENDER_DOMAIN}/ws"
    response = VoiceResponse()
    connect = Connect()
    connect.stream(url=ws_url)
    response.append(connect)
    response.say("Connecting you to the Promatic AI assistant.", voice="alice")
    return str(response)

# WebSocket Handler
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    stream_sid = ""

    while True:
        try:
            msg = await websocket.receive_text()
            data = json.loads(msg)

            if data["event"] == "start":
                stream_sid = data["start"]["streamSid"]
                print(f"🔴 Stream started: {stream_sid}")

            elif data["event"] == "media":
                audio_b64 = data["media"]["payload"]
                audio_bytes = base64.b64decode(audio_b64)

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                    tmp_wav.write(audio_bytes)
                    tmp_wav.flush()
                    transcript = transcribe_audio(tmp_wav.name)

                print(f"🗣️ User said: {transcript}")

                dissatisfied_phrases = ["not helpful", "human", "bad", "transfer"]
                if any(p in transcript.lower() for p in dissatisfied_phrases):
                    print("⚠️ Detected dissatisfaction. Transferring to human agent...")
                    transfer_twiml = VoiceResponse()
                    transfer_twiml.say("Transferring your call to a human agent. Please hold.", voice="alice")
                    transfer_twiml.dial("+918530894722")  # replace with real number
                    await websocket.send_text(json.dumps({"event": "stop"}))
                    await websocket.close()
                    return

                reply = generate_response(transcript)
                print(f"🤖 Bot reply: {reply}")

                audio_array, sample_rate = synthesize_speech(reply)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as bot_wav:
                    sf.write(bot_wav.name, np.array(audio_array), sample_rate, subtype='PCM_16')
                    with open(bot_wav.name, "rb") as f:
                        encoded_audio = base64.b64encode(f.read()).decode("utf-8")

                response_packet = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": encoded_audio}
                }

                await websocket.send_text(json.dumps(response_packet))
                print("✅ Response sent to user.")

            elif data["event"] == "stop":
                print("🛑 Call ended.")
                break

        except Exception as e:
            print(f"⚠️ WebSocket error: {e}")
            break

    await websocket.close()
