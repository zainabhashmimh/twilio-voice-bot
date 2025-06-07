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

def generate_reply(user_input):
    response = gemini_model.generate_content(
        f"You are a friendly support bot for a food delivery app. The user said: '{user_input}'. Respond politely and briefly."
    )
    return response.text.strip()

# ── Health check ──
@app.route("/", methods=["GET"])
def home():
    return "✅ Promatic AI Voicebot is running."

# ── Initiate outbound call ──
@app.route("/initiate-call", methods=["GET"])
def initiate_call():
    try:
        call = client.calls.create(
            url="https://twilio-voice-bot-dr96.onrender.com/voicebot", 
            to="+917715040157",
            from_="+19159952952"
        )
        return f"✅ Call initiated. Call SID: {call.sid}"
    except Exception as e:
        return f"❌ Error initiating call: {str(e)}"

# ── Main Voicebot Route ──
@app.route("/voicebot", methods=["POST"])
def voicebot():
    vr = VoiceResponse()
    g = Gather(
        input="speech",
        timeout=5,
        action="/handle-speech",
        method="POST"
    )
    g.say(
        "Hi! This is Proma from Promatic AI food support. How can I help you today? You can say things like 'place an order', 'check my order status', or 'talk to an agent'.",
        voice="alice"
    )
    vr.append(g)
    vr.say("Sorry, I didn’t catch that. Connecting you to an agent.")
    vr.redirect("/connect-agent")
    return Response(str(vr), mimetype="text/xml")

# ── Handle User's Speech Input ──
@app.route("/handle-speech", methods=["POST"])
def handle_speech():
    speech_text = request.values.get("SpeechResult", "").lower()
    vr = VoiceResponse()

    if not speech_text:
        vr.say("Sorry, I didn't catch that. Please try again.", voice="alice")
        vr.redirect("/voicebot")
        return Response(str(vr), mimetype="text/xml")

    if "agent" in speech_text or "talk to someone" in speech_text:
        vr.say("Connecting you to a live support agent now.", voice="alice")
        vr.redirect("/connect-agent")
        return Response(str(vr), mimetype="text/xml")

    elif "order" in speech_text and "status" in speech_text:
        vr.say("Checking your order status. Please wait.", voice="alice")
        vr.redirect("/check-status")
        return Response(str(vr), mimetype="text/xml")

    elif "place" in speech_text or "order" in speech_text:
        vr.say("Great! Please tell me what you’d like to order after the beep.", voice="alice")
        vr.record(timeout=5, max_length=60, transcribe=True, action="/thanks", method="POST")
        return Response(str(vr), mimetype="text/xml")

    elif any(keyword in speech_text for keyword in ["complaint", "issue", "problem"]):
        vr.say("I'm sorry to hear that. Please describe your issue after the beep.", voice="alice")
        vr.record(timeout=5, max_length=60, transcribe=True, action="/thanks", method="POST")
        return Response(str(vr), mimetype="text/xml")

    else:
        reply = generate_reply(speech_text)
        vr.say(reply, voice="alice")
        vr.say("If you're not satisfied, just say 'talk to agent' and I’ll connect you.")
        vr.redirect("/voicebot")
        return Response(str(vr), mimetype="text/xml")

# ── Order Status ──
@app.route("/check-status", methods=["POST"])
def check_status():
    vr = VoiceResponse()
    vr.say("Your order is being prepared and will be delivered in 20 minutes. Thank you for choosing us!", voice="alice")
    return Response(str(vr), mimetype="text/xml")

# ── Recording Response ──
@app.route("/thanks", methods=["POST"])
def thanks():
    transcript = request.form.get("TranscriptionText", "")
    reply = generate_reply(transcript)
    vr = VoiceResponse()
    vr.say("Thanks for the details. Here's a summary:", voice="alice")
    vr.say(reply, voice="alice")
    vr.say("If you need more help, just say 'talk to agent' next time.")
    return Response(str(vr), mimetype="text/xml")

# ── Connect to Live Agent ──
@app.route("/connect-agent", methods=["POST"])
def connect_agent():
    vr = VoiceResponse()
    vr.say("Please hold while I connect you to a support agent.", voice="alice")
    dial = Dial(timeout=10)
    dial.number("+918530894722")  # Replace with actual agent number
    vr.append(dial)
    vr.say("Sorry, we couldn’t connect you at this time. Please try again later.", voice="alice")
    return Response(str(vr), mimetype="text/xml")

# ── Main Execution ──
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
