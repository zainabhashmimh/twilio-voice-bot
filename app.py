from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import os

app = Flask(__name__)

# --- Twilio Credentials (Use environment variables for safety) ---
account_sid = userdata.get('Twilio_SID')  #ACe3080e7c3670d0bd8cc38bf5bd0924d2'
auth_token = userdata.get('Twilio_Auth_Token')  # f7e94c88b8b6bd3dd5f67803abdbf3d1
client = Client(account_sid, auth_token)

# --- Initiate a Call to a Verified Number ---
@app.route("/initiate-call", methods=["GET"])
def initiate_call():
    try:
        call = client.calls.create(
            url='https://twilio-voice-bot-ng91.onrender.com/voicebot',  # Your deployed /voicebot endpoint
            to='+917715040157',  # Verified number (e.g., your own)
            from_='+19159952952'  # Your Twilio number
        )
        return f"Call initiated with SID: {call.sid}"
    except Exception as e:
        return f"Error initiating call: {str(e)}"

# --- VoiceBot Entry Point ---
@app.route("/voicebot", methods=['POST'])
def voicebot():
    response = VoiceResponse()

    gather = Gather(input='speech dtmf', timeout=5, num_digits=1, action='/handle-selection', method="POST")
    gather.say("Hi there! Welcome to Zomato Clone. Press 1 to place an order, 2 to check order status, or 3 to file a complaint. "
               "You can also say 'agent' to speak with a human.")
    
    response.append(gather)
    response.say("No input received. Connecting you to a support agent.")
    response.redirect('/connect-agent')

    return Response(str(response), mimetype='text/xml')

# --- Handle User Input ---
@app.route("/handle-selection", methods=['POST'])
def handle_selection():
    digit = request.values.get('Digits', '')
    speech = request.values.get('SpeechResult', '').lower()
    response = VoiceResponse()

    if digit == '1' or 'order' in speech:
        response.say("Great! Please tell me what you would like to order.")
        response.record(timeout=10, maxLength=60, action='/thanks', method='POST')
    elif digit == '2' or 'status' in speech:
        response.say("Checking your order status. One moment please.")
        response.redirect('/check-status')
    elif digit == '3' or 'complaint' in speech:
        response.say("Sorry to hear that. Please describe your issue after the beep.")
        response.record(timeout=10, maxLength=60, action='/thanks', method='POST')
    elif 'agent' in speech:
        response.redirect('/connect-agent')
    else:
        response.say("Sorry, I didn’t understand. Connecting you to an agent now.")
        response.redirect('/connect-agent')

    return Response(str(response), mimetype='text/xml')

# --- Order Status Placeholder ---
@app.route("/check-status", methods=['POST'])
def check_status():
    response = VoiceResponse()
    response.say("Your order is being prepared and will arrive in 20 minutes. Thank you!")
    return Response(str(response), mimetype='text/xml')

# --- Thank You for Complaint or Order ---
@app.route("/thanks", methods=['POST'])
def thanks():
    response = VoiceResponse()
    response.say("Thank you! We've recorded your message. We’ll get back to you shortly.")
    return Response(str(response), mimetype='text/xml')

# --- Redirect to Human Agent ---
@app.route("/connect-agent", methods=['POST'])
def connect_agent():
    response = VoiceResponse()
    response.say("Connecting you to a live agent. Please hold...")
    response.dial("+918530894722")  # Replace with actual support number
    return Response(str(response), mimetype='text/xml')

# --- Main Run ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)
