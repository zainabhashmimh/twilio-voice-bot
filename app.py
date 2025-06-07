from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)

@app.route("/voice", methods=['POST'])
def voice():
    resp = VoiceResponse()
    gather = Gather(input='speech', action='/process', speechTimeout='auto')
    gather.say("Hello, I am your assistant. How may I help you today?")
    resp.append(gather)
    resp.redirect('/voice')  # repeat if nothing was said
    return str(resp)

@app.route("/process", methods=['POST'])
def process():
    user_input = request.form.get("SpeechResult")

    # Sentiment check
    if detect_dissatisfaction(user_input):
        resp = VoiceResponse()
        resp.say("Let me connect you to a human agent.")
        resp.dial("+918530894722")  # Replace with human agent's number
        return str(resp)
    
    # LLM Response (use API or local inference)
    reply = query_llm(user_input)
    resp = VoiceResponse()
    resp.say(reply)
    
    # Loop back
    gather = Gather(input='speech', action='/process', speechTimeout='auto')
    resp.append(gather)
    return str(resp)

def detect_dissatisfaction(text):
    negative_keywords = ['not helpful', 'bad', 'angry', 'speak to agent', 'you are wrong', 'disappointed']
    return any(word in text.lower() for word in negative_keywords)

def query_llm(prompt):
    # You can run TinyLlama locally or on Render and call it here
    return "This is a placeholder response from the LLM."

if __name__ == "__main__":
    app.run()
