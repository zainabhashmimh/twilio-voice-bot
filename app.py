from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from twilio.rest import Client
import google.generativeai as genai
import os

app = Flask(__name__)

# ── Twilio credentials ──
account_sid = "ACe3080e7c3670d0bd8cc38bf5bd0924d2"
auth_token = "96849b488f0a8355791227462684aba0"
client = Client(account_sid, auth_token)

# ── Gemini setup ──
genai.configure(api_key="AIzaSyBVnNNltQB39PuUqxo8lO7nT8XldMBGoUI")
gemini_model = genai.GenerativeModel("gemini-pro")

# ── Generate Gemini response ──
def generate_reply(user_input):
    response = gemini_model.generate_content(
        f"You are a helpful food delivery assistant. The user said: '{user_input}'. Please reply politely and concisely."
    )
    return response.text.strip()

# ── Health check ──
@app.route("/", methods=["GET"])
def home():
    return "✅ Promatic AI Voicebot is live."

# ── Initiate call ──
@app.route("/initiate-call", methods=["GET"])
def initiate_call():
    try:
        call = client.calls.create(
            url="https://twilio-voice-bot-dr96.onrender.com/voicebot",
            to="+917715040157",
            from_="+19159952952"
        )
        return f"✅ Call initiated. SID: {call.sid}"
    except Exception as e:
        return f"❌ Failed to initiate call: {str(e)}"

# ── First prompt ──
@app.route("/voicebot", methods=["POST"])
def voicebot():
    vr = VoiceResponse()
    g = Gather(input="speech", action="/conversation", method="POST", timeout=5)
    g.say("Hi! This is Proma from Promatic AI. How may I assist you today?", voice="alice")
    vr.append(g)
    vr.say("I didn't catch that. Please try again or say 'talk to agent'.")
    vr.redirect("/voicebot")
    return Response(str(vr), mimetype="text/xml")

# ── Continuous interaction ─
@app.route("/conversation", methods=["POST"])
def conversation():
    speech_text = request.values.get("SpeechResult", "")
    vr = VoiceResponse()

    if not speech_text:
        vr.say("Sorry, I didn't get that. Let's try again.", voice="alice")
        vr.redirect("/voicebot")
        return Response(str(vr), mimetype="text/xml")

    if "agent" in speech_text.lower():
        vr.redirect("/connect-agent")
        return Response(str(vr), mimetype="text/xml")

    reply = generate_reply(speech_text)
    vr.say(reply, voice="alice")

    # Continue conversation
    g = Gather(input="speech", action="/conversation", method="POST", timeout=5)
    g.say("Do you have any more questions?", voice="alice")
    vr.append(g)
    vr.say("Still there? Redirecting you to an agent.", voice="alice")
    vr.redirect("/connect-agent")
    return Response(str(vr), mimetype="text/xml")

# ── Connect agent ─
@app.route("/connect-agent", methods=["POST"])
def connect_agent():
    vr = VoiceResponse()
    vr.say("Connecting you to a live agent now.", voice="alice")
    dial = Dial()
    dial.number("+918530894722")
    vr.append(dial)
    vr.say("Sorry, agent is unavailable. Please try again later.", voice="alice")
    return Response(str(vr), mimetype="text/xml")

# ── Run ─
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
