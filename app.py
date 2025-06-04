from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from twilio.rest import Client

app = Flask(__name__)

# ── Twilio credentials ──
account_sid = "ACe3080e7c3670d0bd8cc38bf5bd0924d2"   # ← replace in production
auth_token  = "466b9357c94236c196edc785e15d7a84"      # ← replace in production
client = Client(account_sid, auth_token)

# ── Health check ──
@app.route("/", methods=["GET"])
def home():
    return "Promatic AI / Zomato Voicebot is running!"

# ── Outbound dial example ──
@app.route("/initiate-call", methods=["GET"])
def initiate_call():
    try:
        call = client.calls.create(
            url="https://your-production-domain.com/voicebot",  # set to your public HTTPS URL
            to="+917715040157",      # verified destination
            from_="+19159952952"     # your Twilio voice number
        )
        return f"✅ Call initiated. Call SID: {call.sid}"
    except Exception as e:
        return f"❌ Error initiating call: {str(e)}"

# ───────────────────────────────────────
# Inbound flow ① – DTMF menu (Promatic AI)
# ───────────────────────────────────────
@app.route("/voice", methods=["GET", "POST"])
def voice():
    vr = VoiceResponse()
    g = Gather(num_digits=1, action="/gather", method="POST", timeout=5)
    g.say(
        "Welcome to Promatic A-I. "
        "Press 1 to place an order, "
        "2 to check order status, "
        "or 3 to talk to a support agent.",
        voice="alice"
    )
    vr.append(g)
    vr.redirect("/voice")        # repeat if no input
    return Response(str(vr), mimetype="text/xml")

@app.route("/gather", methods=["POST"])
def gather_digits():
    digit = request.form.get("Digits")
    vr = VoiceResponse()

    if digit == "1":
        vr.say("Please tell us your order after the beep.")
        vr.record(timeout=5, max_length=60, transcribe=True,
                  action="/thanks", method="POST")

    elif digit == "2":
        vr.say("Your order is being prepared and will be delivered in 20 minutes. Thank you for your patience.")

    elif digit == "3":
        vr.say("Connecting you to our support agent.")
        vr.dial("+918530894722")   # verified agent number

    else:
        vr.say("Invalid input. Please try again.")
        vr.redirect("/voice")

    return Response(str(vr), mimetype="text/xml")

# ───────────────────────────────────────
# Inbound/outbound flow ② – Speech + DTMF (Zomato Clone)
# ───────────────────────────────────────
@app.route("/voicebot", methods=["POST"])
def voicebot():
    vr = VoiceResponse()
    g = Gather(
        input="speech dtmf",
        timeout=5,
        num_digits=1,
        action="/handle-selection",
        method="POST"
    )
    g.say(
        "Hi! Welcome to Zomato Clone. "
        "Press 1 to place an order. "
        "Press 2 to check your order status. "
        "Press 3 to register a complaint. "
        "Press 0 to talk to an agent. "
        "You can also speak your choice."
    )
    vr.append(g)
    vr.say("We didn't catch that. Redirecting you to a support agent.")
    vr.redirect("/connect-agent")
    return Response(str(vr), mimetype="text/xml")

@app.route("/handle-selection", methods=["POST"])
def handle_selection():
    digit  = request.values.get("Digits")
    speech = request.values.get("SpeechResult", "").lower()
    vr = VoiceResponse()

    if digit == "1" or "order" in speech:
        vr.say("Sure! Please tell me your order after the beep.")
        vr.record(timeout=5, max_length=60, transcribe=True,
                  action="/thanks", method="POST")

    elif digit == "2" or "status" in speech:
        vr.say("Checking your order status. Please wait…")
        vr.redirect("/check-status")

    elif digit == "3" or any(x in speech for x in ["complaint", "issue", "problem"]):
        vr.say("Please describe your complaint after the beep.")
        vr.record(timeout=5, max_length=60, transcribe=True,
                  action="/thanks", method="POST")

    elif digit == "0" or "agent" in speech:
        vr.say("Connecting you to a support agent.")
        vr.redirect("/connect-agent")

    else:
        vr.say("Sorry, I didn’t get that. Redirecting you to an agent.")
        vr.redirect("/connect-agent")

    return Response(str(vr), mimetype="text/xml")

# ── Shared utility routes ──
@app.route("/check-status", methods=["POST"])
def check_status():
    vr = VoiceResponse()
    vr.say("Your order is being prepared and will be delivered in 20 minutes. Thank you for your patience.")
    return Response(str(vr), mimetype="text/xml")

@app.route("/thanks", methods=["POST"])
def thanks():
    vr = VoiceResponse()
    vr.say("Thank you! Your message has been recorded. We'll get back to you soon.")
    return Response(str(vr), mimetype="text/xml")

@app.route("/connect-agent", methods=["POST"])
def connect_agent():
    vr = VoiceResponse()
    vr.say("Please wait while we connect you to a support agent.")
    dial = Dial(timeout=10)
    dial.number("+918530894722")
    vr.append(dial)
    vr.say("Sorry, we couldn’t connect you to the agent at this time.")
    return Response(str(vr), mimetype="text/xml")

# ── Run server ──
if __name__ == "__main__":
    app.run(debug=True)
