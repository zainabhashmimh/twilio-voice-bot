import torch
from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import google.generativeai as genai
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import requests
import soundfile as sf
import io

app = Flask(__name__)

# --- Twilio Credentials ---
account_sid = 'ACe3080e7c3670d0bd8cc38bf5bd0924d2'
auth_token = '96849b488f0a8355791227462684aba0'
client = Client(account_sid, auth_token)

# --- Gemini API Setup ---
genai.configure(api_key="AIzaSyBVnNNltQB39PuUqxo8lO7nT8XldMBGoUI")
gemini_model = genai.GenerativeModel("gemini-pro")

def generate_reply(user_input):
    response = gemini_model.generate_content(f"Act like a friendly support bot. The user said: '{user_input}'. Respond politely.")
    return response.text.strip()

# --- Whisper Model Setup ---
device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
whisper_model_id = "openai/whisper-large-v3"

asr_model = AutoModelForSpeechSeq2Seq.from_pretrained(
    whisper_model_id,
    torch_dtype=torch_dtype,
    low_cpu_mem_usage=True,
    use_safetensors=True
).to(device)

processor = AutoProcessor.from_pretrained(whisper_model_id)

whisper_pipe = pipeline(
    "automatic-speech-recognition",
    model=asr_model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    torch_dtype=torch_dtype,
    device=device,
)

# --- Routes ---

@app.route("/", methods=["GET"])
def home():
    return "✅ Twilio + Whisper + Gemini voicebot is running."

@app.route("/initiate-call", methods=["GET"])
def initiate_call():
    try:
        call = client.calls.create(
            url='https://your-ngrok-or-deployed-url.com/voicebot',
            to='+917715040157',     # Replace with verified recipient number
            from_='+19159952952'    # Your Twilio number
        )
        return f"✅ Outbound call initiated: {call.sid}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route("/voicebot", methods=["POST"])
def voicebot():
    response = VoiceResponse()
    response.say("Hi, I'm Proma from Promatic AI. Please speak after the beep. I will reply shortly.", voice='alice')
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
    recording_url = request.form.get("RecordingUrl")
    print("📥 Recording URL:", recording_url)

    try:
        # Download audio from Twilio
        audio_response = requests.get(recording_url)
        audio_bytes = io.BytesIO(audio_response.content)

        # Transcribe with Whisper
        result = whisper_pipe(audio_bytes)
        user_input = result["text"]
        print("🗣 Whisper Transcript:", user_input)
    except Exception as e:
        print("❌ Whisper failed:", str(e))
        user_input = ""

    # Prepare Twilio response
    response = VoiceResponse()

    if "agent" in user_input.lower() or "not satisfied" in user_input.lower():
        response.say("I understand. Connecting you to a live agent now.", voice='alice')
        response.dial("+918530894722")  # Replace with your live agent number
    elif user_input:
        reply = generate_reply(user_input)
        response.say(reply, voice='alice')
        response.say("If you still need help, say 'talk to agent' next time.", voice='alice')
        response.redirect('/voicebot')
    else:
        response.say("Sorry, I couldn't hear you. Let's try again.", voice='alice')
        response.redirect('/voicebot')

    return Response(str(response), mimetype='text/xml')

# --- Run App ---
if __name__ == "__main__":
    app.run(debug=True)
