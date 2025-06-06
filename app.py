from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
import google.generativeai as genai

app = Flask(__name__)

# --- Twilio Credentials (Use environment variables in production) ---
account_sid = 'ACe3080e7c3670d0bd8cc38bf5bd0924d2'
auth_token = '96849b488f0a8355791227462684aba0'
client = Client(account_sid, auth_token)

# --- Gemini API Setup ---
genai.configure(api_key="AIzaSyBVnNNltQB39PuUqxo8lO7nT8XldMBGoUI")
model = genai.GenerativeModel("gemini-pro")

# --- Gemini Reply Helper ---
def generate_reply(user_input):
    response = model.generate_content(f"Act like a friendly support bot. The user said: '{user_input}'. Respond politely.")
    return response.text.strip()

# --- Home Route ---
@app.route("/", methods=["GET"])
def home():
    return "✅ Gemini-Twilio Real-Time Voicebot is running."

# --- Initiate Outbound Call ---
@app.route("/initiate-call", methods=["GET"])
def initiate_call():
    try:
        call = client.calls.create(
            url='https://your-deployed-url.com/voicebot',  # Replace with your actual ngrok or deployed URL
            to='+917715040157',   # Verified destination number
            from_='+19159952952'  # Your Twilio number
        )
        return f"✅ Outbound call initiated: {call.sid}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

# --- Voicebot Main Entry with Speech Recognition ---
@app.route("/voicebot", methods=["POST"])
def voicebot():
    response = VoiceResponse()
    gather = Gather(
        input='speech',
        timeout=3,
        speechTimeout='auto',
        action='/handle-speech',
        method='POST'
    )
    gather.say("Hi, I'm Proma from Promatic AI. How can I help you today?", voice='alice')
    response.append(gather)

    # Fallback if nothing is said
    response.say("Sorry, I didn't catch that. Let's try again.")
    response.redirect('/voicebot')
    return Response(str(response), mimetype='text/xml')

# --- Speech Handler: Process and Reply with Gemini ---
@app.route("/handle-speech", methods=["POST"])
def handle_speech():
    user_input = request.form.get("SpeechResult", "")
    print("User said:", user_input)

    response = VoiceResponse()

    # If user wants human agent
    if "not satisfied" in user_input.lower() or "agent" in user_input.lower():
        response.say("Sure. Connecting you to a live agent.")
        response.dial("+918530894722")  # Replace with your agent number
        return Response(str(response), mimetype='text/xml')

    # Generate Gemini AI reply
    gemini_reply = generate_reply(user_input)
    response.say(gemini_reply, voice='alice')

    # Loop back for more conversation
    response.redirect('/voicebot')
    return Response(str(response), mimetype='text/xml')

# --- Run App ---
if __name__ == "__main__":
    app.run(debug=True)
