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

# Generate Gemini reply
def generate_reply(user_input):
    response = model.generate_content(f"Act like a friendly support bot. The user said: '{user_input}'. Respond politely.")
    return response.text.strip()

# 1. Initiate outbound call
@app.route("/initiate-call", methods=["GET"])
def initiate_call():
    try:
        call = client.calls.create(
            url='https://your-render-url.onrender.com/voicebot',  # ✅ Update with your actual Render URL
            to='+917715040157',   # Verified customer number
            from_='+19159952952'  # Your Twilio number
        )
        return f"✅ Outbound call initiated: {call.sid}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

# 2. Handle incoming call
@app.route("/voicebot", methods=['POST'])
def voicebot():
    response = VoiceResponse()
    response.say("Hi, I'm Proma from Promatic AI. Please tell me your issue after the beep. I’m here to help.", voice='alice')
    response.record(
        timeout=5,
        transcribe=True,
        max_length=30,
        action='/handle-transcription',
        method='POST'
    )
    return Response(str(response), mimetype='text/xml')

# 3. Process transcription & respond with Gemini
@app.route("/handle-transcription", methods=['POST'])
def handle_transcription():
    user_input = request.form.get("TranscriptionText", "")
    response = VoiceResponse()

    if "not satisfied" in user_input.lower() or "talk to agent" in user_input.lower():
        response.say("I understand. Connecting you to a live agent now.")
        response.dial("+918530894722")  # Agent number
        return Response(str(response), mimetype='text/xml')

    gemini_reply = generate_reply(user_input)
    response.say(gemini_reply, voice="alice")
    response.say("If you still need help, just say you're not satisfied and I will connect you to an agent.")
    response.redirect('/voicebot')
    return Response(str(response), mimetype='text/xml')

# 4. Health check or root
@app.route("/", methods=["GET"])
def home():
    return "✅ Gemini-Twilio Voice Bot is running."

if __name__ == "__main__":
    app.run(debug=True)
