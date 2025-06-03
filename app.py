from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)

@app.route("/voicebot", methods=['GET', 'POST'])
def voicebot():
    response = VoiceResponse()
    gather = Gather(num_digits=1, action='/gather', method='POST', timeout=5)
    gather.say("Hey there! Welcome to Zomato clone. Press 1 to order food, 2 to check your order status, or 3 to talk to support.", voice='alice')
    response.append(gather)
    response.redirect('/voicebot')
    return str(response)

@app.route("/gather", methods=['POST'])
def gather():
    response = VoiceResponse()
    digit = request.values.get('Digits', '')

    if digit == '1':
        response.say("Great! Let's get your food order started. What would you like to have today?", voice='alice')
    elif digit == '2':
        response.say("Sure. Please wait while I fetch your order status.", voice='alice')
    elif digit == '3':
        response.say("Hold on. Let me connect you to our support executive.", voice='alice')
        response.dial('+918530894722')  # Replace with your support phone number
    else:
        response.say("Sorry, I didn't get that. Please try again.", voice='alice')
        response.redirect('/voicebot')

    return str(response)

@app.route("/")
def home():
    return "Zomato Clone Voice Bot is live!"

if __name__ == "__main__":
    app.run(debug=True)
