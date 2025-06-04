from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client

app = Flask(__name__)

# --- Twilio Credentials ---
account_sid = 'ACe3080e7c3670d0bd8cc38bf5bd0924d2'  # Replace with your actual SID
auth_token = '466b9357c94236c196edc785e15d7a84'     # Replace with your actual token
client = Client(account_sid, auth_token)

# --- Home Route ---
@app.route("/", methods=["GET"])
def home():
    return "Zomato Voicebot is running!"

# --- Initiate a Call ---
@app.route("/initiate-call", methods=["GET"])
def initiate_call():
    try:
        call = client.calls.create(
            url='https://twilio-voice-bot-ng91.onrender.com/voicebot',  # Replace with your deployed endpoint
            to='+917715040157',       # Verified recipient number
            from_='+19159952952'      # Your Twilio number with voice capability
        )
        return f"✅ Call initiated. Call SID: {call.sid}"
    except Exception as e:
        return f"❌ Error initiating call: {str(e)}"

# --- Main Voicebot Route ---
@app.route("/voicebot", methods=['POST'])
def voicebot():
    response = VoiceResponse()
    gather = Gather(
        input='speech dtmf',
        timeout=5,
        num_digits=1,
        action='/handle-selection',
        method='POST'
    )
    gather.say("Hi! Welcome to Zomato Clone. "
               "Press 1 to place an order. "
               "Press 2 to check your order status. "
               "Press 3 to register a complaint. "
               "Press 0 to talk to an agent. "
               "You can also speak your choice.")
    response.append(gather)
    response.say("We didn't catch that. Redirecting you to a support agent.")
    response.redirect('/connect-agent')
    return Response(str(response), mimetype='text/xml')

# --- Handle User Selection ---
@app.route("/handle-selection", methods=['POST'])
def handle_selection():
    digit = request.values.get('Digits')
    speech = request.values.get('SpeechResult', '').lower()
    response = VoiceResponse()

    if digit == '1' or 'order' in speech:
        response.say("Sure! Please tell me your order after the beep.")
        response.record(timeout=5, max_length=60, transcribe=True, action='/thanks', method='POST')

    elif digit == '2' or 'status' in speech:
        response.say("Checking your order status. Please wait...")
        response.redirect('/check-status')

    elif digit == '3' or 'complaint' in speech or 'issue' in speech or 'problem' in speech:
        response.say("Please describe your complaint after the beep.")
        response.record(timeout=5, max_length=60, transcribe=True, action='/thanks', method='POST')

    elif digit == '0' or 'agent' in speech:
        response.say("Connecting you to a support agent.")
        response.redirect('/connect-agent')

    else:
        response.say("Sorry, I didn’t get that. Redirecting you to an agent.")
        response.redirect('/connect-agent')

    return Response(str(response), mimetype='text/xml')

# --- Check Order Status ---
@app.route("/check-status", methods=['POST'])
def check_status():
    response = VoiceResponse()
    response.say("Your order is being prepared and will be delivered in 20 minutes. Thank you for your patience.")
    return Response(str(response), mimetype='text/xml')

# --- Thank You After Recording ---
@app.route("/thanks", methods=['POST'])
def thanks():
    response = VoiceResponse()
    response.say("Thank you! Your message has been recorded. We'll get back to you soon.")
    return Response(str(response), mimetype='text/xml')

# --- Connect to Support Agent ---
@app.route("/connect-agent", methods=['POST'])
def connect_agent():
    response = VoiceResponse()
    response.say("Please wait while we connect you to a support agent.")
    dial = response.dial(timeout=10)
    dial.number("+918530894722")  # Your support agent's verified number
    response.say("Sorry, we couldn’t connect you to the agent at this time.")
    return Response(str(response), mimetype='text/xml')

# --- Run App ---
if __name__ == "__main__":
    app.run(debug=True)
