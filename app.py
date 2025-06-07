import os
import time
import io
import torch
import requests
import torchaudio
from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import google.generativeai as genai
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

# --- Flask App ---
app = Flask(__name__)

# --- Twilio Credentials ---
account_sid = 'ACe3080e7c3670d0bd8cc38bf5bd0924d2'  # Replace with your SID
auth_token = '96849b488f0a8355791227462684aba0'     # Replace with your Token
twilio_client = Client(account_sid, auth_token)

# --- Gemini API Key ---
genai.configure(api_key="AIzaSyBVnNNltQB39PuUqxo8lO7nT8XldMBGoUI")
gemini_model = genai.GenerativeModel("gemini-pro")

def generate_reply(text):
    response = gemini_model.generate_content(
        f"Act like a helpful and polite customer support assistant. The user said: '{text}'. Respond accordingly."
    )
    return response.text.strip()

# --- Whisper Setup ---
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if torch.cuda.is_available() else torch.float32
model_id = "openai/whisper-large-v3"

asr_model = AutoModelForSpeechSeq2Seq.from_pretrained(model_id, torch_dtype=dtype, low_cpu_mem_usage=True, use_safetensors=True).to(device)
processor = AutoProcessor.from_pretrained(model_id)
asr_pipe = pipeline("automatic-speech-recognition", model=asr_model, tokenizer=processor.tokenizer, feature_extractor=processor.feature_extractor, torch_dtype=dtype, device=0 if torch.cuda.is_available() else -1)

# --- Helper: Convert Twilio Audio ---
def convert_audio(audio_bytes):
    with open("input.wav", "wb") as f:
        f.write(audio_bytes.read())

    waveform, sr = torchaudio.load("input.wav")
    waveform = torchaudio.transforms.Resample(sr, 16000)(waveform)
    torchaudio.save("output.wav", waveform, 16000)
    return "output.wav"

# --- Routes ---
@app.route("/")
def home():
    return "✅ Voicebot with Gemini & Whisper is running."

@app.route("/initiate-call", methods=["GET"])
def initiate_call():
    try:
        call = twilio_client.calls.create(
            url='https://twilio-voice-bot-dr96.onrender.com/voicebot',  # Replace with your deployed /voicebot URL
            to='+917715040157',   # Verified user number
            from_='+19159952952'  # Your Twilio number
        )
        return f"✅ Call initiated: {call.sid}"
    except Exception as e:
        return f"❌ Error: {e}"

@app.route("/voicebot", methods=["POST"])
def voicebot():
    response = VoiceResponse()
    response.say("Hi! I am Proma from Promatic AI. Tell me your problem after the beep.", voice='alice')
    response.record(
        timeout=5,
        max_length=15,
        play_beep=True,
        action='/handle-recording',
        method='POST'
    )
    return Response(str(response), mimetype='text/xml')

@app.route("/handle-recording", methods=["POST"])
def handle_recording():
    recording_url = request.form.get("RecordingUrl", "")
    print("🎙 Recording URL:", recording_url)

    try:
        time.sleep(1)  # Ensure audio is available
        audio_response = requests.get(recording_url)
        converted_path = convert_audio(io.BytesIO(audio_response.content))
        transcript = asr_pipe(converted_path)["text"]
        print("📝 Transcript:", transcript)
    except Exception as e:
        print("❌ Whisper Error:", str(e))
        transcript = ""

    response = VoiceResponse()

    if not transcript:
        response.say("Sorry, I couldn't hear you clearly. Let's try again.", voice='alice')
        response.redirect('/voicebot')
        return Response(str(response), mimetype='text/xml')

    if "agent" in transcript.lower() or "not satisfied" in transcript.lower():
        response.say("Connecting you to a live agent now.", voice='alice')
        response.dial("+918530894722")  # Agent phone number
        return Response(str(response), mimetype='text/xml')

    gemini_response = generate_reply(transcript)
    response.say(gemini_response, voice='alice')
    response.say("If you're still not satisfied, just say 'talk to agent'.", voice='alice')
    response.redirect('/voicebot')
    return Response(str(response), mimetype='text/xml')

# --- Run locally (not needed on Render) ---
if __name__ == "__main__":
    app.run(debug=True)
