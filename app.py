from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import google.generativeai as genai

app = Flask(__name__)

# --- Twilio Credentials ---
account_sid = 'ACe3080e7c3670d0bd8cc38bf5bd0924d2'
auth_token = '96849b488f0a8355791227462684aba0'
client = Client(account_sid, auth_token)

# --- Gemini API Setup ---
genai.configure(api_key="AIzaSyBVnNNltQB39PuUqxo8lO7nT8XldMBGoUI")
model = genai.GenerativeModel("gemini-pro")

# --- Helper to Get Gemini Reply ---
def generate_reply(user_input):
    response = model.generate_content(f"Act like a friendly support bot. The user said: '{user_input}'. Respond politely.")
    return response.text.strip()

# --- Route: Home ---
@app.route("/", methods=["GET"])
def home():
    return "✅ Gemini-Twilio Voice Bot is running."

# --- Route: Initiate Outbound Call ---
@app.route("/initiate-call", methods=["GET"])
def initiate_call():
    try:
        call = client.calls.create(
            url='https://your-render-url.onrender.com/voicebot',  # Replace with actual Render URL
            to='+917715040157',   # Verified customer number
            from_='+19159952952'  # Your Twilio number
        )
        return f"✅ Outbound call initiated: {call.sid}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

# --- Route: Main Voicebot Entry ---
@app.route("/voicebot", methods=["POST"])
def voicebot():
    response = VoiceResponse()
    response.say("Hi, I'm Proma from Promatic AI. Tell me your issue after the beep.", voice='alice')
    
    response.record(
        timeout=5,
        max_length=30,
        transcribe=True,
        transcribe_callback='/handle-transcription',
        method='POST'
    )

    return Response(str(response), mimetype='text/xml')

# --- Route: Handle Transcription with Gemini ---
@app.route("/handle-transcription", methods=["POST"])
def handle_transcription():
    user_input = request.form.get("TranscriptionText", "")
    print("Transcription Received:", user_input)
    response = VoiceResponse()

    if "not satisfied" in user_input.lower() or "talk to agent" in user_input.lower():
        response.say("I understand. Connecting you to a live agent now.")
        response.dial("+918530894722")  # Agent number
        return Response(str(response), mimetype='text/xml')

    gemini_reply = generate_reply(user_input)
    response.say(gemini_reply, voice='alice')
    response.say("If you still need help, just say you're not satisfied and I will connect you to an agent.")
    response.redirect('/voicebot')
    return Response(str(response), mimetype='text/xml')

# --- Optional: Handle Recording if Transcription Fails ---
@app.route("/handle-recording", methods=["POST"])
def handle_recording():
    recording_url = request.form.get("RecordingUrl", "")
    print("Recording fallback URL:", recording_url)

    response = VoiceResponse()
    response.say("Thanks for your message. We’ll get back to you soon.")
    return Response(str(response), mimetype='text/xml')

# --- Main Entry ---
if __name__ == "__main__":
    app.run(debug=True)
