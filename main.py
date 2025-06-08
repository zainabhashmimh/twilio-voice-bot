import os, base64, json, tempfile
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
import whisper
from transformers import AutoModelForCausalLM, AutoTokenizer
from TTS.api import TTS
import soundfile as sf
import numpy as np  # Required to handle audio arrays

# --- Load environment variables ---
load_dotenv()
TWILIO_ACCOUNT_SID = "ACe3080e7c3670d0bd8cc38bf5bd0924d2"
TWILIO_AUTH_TOKEN = "5888201f8aca6f08c09dcd9dd6a794df"
RENDER_DOMAIN = "twilio-voice-bot-dr96.onrender.com/voicebot"

# --- Initialize FastAPI App ---
app = FastAPI()

# --- Load Models at Startup ---
print("⏳ Loading Whisper STT...")
whisper_model = whisper.load_model("base")

print("⏳ Loading TinyLlama...")
tokenizer = AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
llm = AutoModelForCausalLM.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")

print("⏳ Loading Coqui TTS...")
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

# --- Helper Functions ---
def transcribe_audio(file_path):
    result = whisper_model.transcribe(file_path)
    return result["text"]

def generate_response(prompt):
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = llm.generate(**inputs, max_new_tokens=100)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

def synthesize_speech(text):
    audio_array = tts.tts(text)
    sample_rate = tts.synthesizer.output_sample_rate
    return audio_array, sample_rate

# --- HTTP Route for Twilio Voice Webhook ---
@app.get("/")
def index():
    return {"message": "✅ Promatic AI Voice Bot is running."}

@app.post("/voicebot", response_class=PlainTextResponse)
async def voicebot(request: Request):
    ws_url = f"wss://{RENDER_DOMAIN}/ws"
    response = VoiceResponse()
    connect = Connect()
    connect.stream(url=ws_url)
    response.append(connect)
    response.say("Connecting you to the Promatic AI assistant.", voice="alice")
    return str(response)

# --- WebSocket Endpoint for Audio Stream ---
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

# --- Run Locally (for development) ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
