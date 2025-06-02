from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse

app = Flask(__name__)

@app.route("/voice", methods=["POST"])
def voice():
    response = VoiceResponse()
    gather = response.gather(num_digits=1, action="/handle-key", method="POST")
    gather.say("Welcome to Promatic AI. Press 1 for services, 2 for pricing, or 3 to speak with support.")
    return str(response)

@app.route("/handle-key", methods=["POST"])
def handle_key():
    digit = request.form.get("Digits")
    response = VoiceResponse()

    if digit == "1":
        response.say("You selected Services. We offer AI and analytics.")
    elif digit == "2":
        response.say("Pricing starts from ninety-nine dollars.")
    elif digit == "3":
        response.say("Connecting to a support executive.")
    else:
        response.say("Invalid input. Please try again.")
    return str(response)

if __name__ == "__main__":
    app.run()
