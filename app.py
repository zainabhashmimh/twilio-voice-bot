from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import google.generativeai as genai

app = Flask(__name__)

# Twilio Credentials
account_sid = 'ACe3080e7c3670d0bd8cc38bf5bd0924d2'
auth_token = '96849b488f0a8355791227462684aba0'
client = Client(account_sid, auth_token)

# Gemini Config
genai.configure(api_key="AIzaSyBVnNNltQB39PuUqxo8lO7nT8XldMBGoUI")
model = genai.GenerativeModel("gemini-pro")

# --- Gemini Response ---
def generate_reply(user_input):
    response = model.generate_content(f"Act like a friendly support bot. The user said: '{user_input}'. Respond politely.")
    return response.text.strip()

# --- Initiate Outbound Call ---
@app.route("/initiate-call", methods=["GET"])
def initiate_call():
    try:
        call = client.calls.create(
            url='https://your-render-url.onrender.com/voicebot',  # UPDATE THIS
            to='+917715040157',
            from_='+19159952952'
        )
        return f"✅ Call initiated: {call.sid}"
    except Exception as e:
        return f"❌ Error initiating call: {str(e)}"

# --- Voicebot Entry ---
@app.route("/voicebot", methods=['POST'])
def voicebot():
    response = VoiceResponse()
    response.say("Hi, I'm Proma from Promatic AI. Please describe your problem after the beep.", voice='alice')
    response.record(
        timeout=5,
        transcribe=True,
        max_length=30,
        action='/handle-transcription',
        method='POST'
    )
    return Response(str(response), mimetype='text/xml')

# --- Handle Transcription ---
@app.route("/handle-transcription", methods=['POST'])
def handle_transcription():
    user_input = request.form.get("TranscriptionText", "")
    print("📞 User said:", user_input)

    response = VoiceResponse()

    if not user_input:
        response.say("Sorry, I couldn't hear you. Let's try again.")
        response.redirect('/voicebot')
        return Response(str(response), mimetype='text/xml')

    if "not satisfied" in user_input.lower() or "agent" in user_input.lower():
        response.say("I understand. Connecting you to a live agent now.", voice='alice')
        response.dial("+918530894722")
        return Response(str(response), mimetype='text/xml')

    gemini_reply = generate_reply(user_input)
    print("🤖 Gemini says:", gemini_reply)

    response.say(gemini_reply, voice='alice')
    response.say("If you still need help, just say 'I'm not satisfied' and I will connect you to an agent.")
    response.redirect('/voicebot')
    return Response(str(response), mimetype='text/xml')

# --- Health Check ---
@app.route("/", methods=["GET"])
def home():
    return "✅ Gemini-Twilio Bot is Running!"

if __name__ == "__main__":
    app.run(debug=True)
