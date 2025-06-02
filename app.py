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
        response.say("You selected Services. We offer AI, data science, chatbot, and analytics services.")
    elif digit == "2":
        response.say("Our pricing starts from ninety-nine dollars per month. Please visit our website for more details.")
    elif digit == "3":
        response.say("Please hold while we connect you to a support executive.")
        # Optionally: <Dial> action here
    else:
        response.say("Invalid input. Please try again.")
    return str(response)

if __name__ == "__main__":
    app.run()
