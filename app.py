import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PORT = int(os.getenv('PORT', 10000))

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please set it in environment variables.")

SYSTEM_MESSAGE = (
    "You are a helpful and bubbly AI assistant who loves to chat about "
    "anything the user is interested in and is prepared to offer them facts. "
    "You have a penchant for dad jokes, owl jokes, and rickrolling – subtly. "
    "Always stay positive, but work in a joke when appropriate."
)

LOG_EVENT_TYPES = [
    'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]

@app.get("/", response_class=JSONResponse)
async def root():
    return {"message": "Twilio AI Voice Assistant is live!"}

@app.api_route("/incoming-call", methods=["GET", "POST"])
async def incoming_call(request: Request):
    response = VoiceResponse()
    response.say("Connecting you to our AI assistant.")
    response.pause(length=1)
    response.say("You can begin talking now.")

    host = request.url.hostname or "your-app-name.onrender.com"
    connect = Connect()
    connect.stream(
        url=f"wss://{host}/media-stream",
        track="both_tracks",
        audio_config={"codec": "mulaw", "sample_rate": 8000}
    )
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")

@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected from Twilio")

    async with websockets.connect(
        'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:

        await openai_ws.send(json.dumps({
            "type": "session.create",
            "messages": [
                {"role": "system", "content": SYSTEM_MESSAGE}
            ]
        }))

        stream_sid = None

        async def from_twilio():
            nonlocal stream_sid
            try:
                async for message in websocket.iter_text():
                    print("📡 Incoming Twilio message:", message)
                    data = json.loads(message)
                    if data['event'] == 'media' and openai_ws.open:
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }))
                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        print(f"Stream started: {stream_sid}")
            except WebSocketDisconnect:
                print("Twilio disconnected WebSocket")

        async def to_twilio():
            try:
                async for message in openai_ws:
                    print("🧠 OpenAI response:", message)
                    data = json.loads(message)
                    if data.get("type") == "response.audio.delta" and data.get("delta"):
                        audio_base64 = base64.b64encode(
                            base64.b64decode(data["delta"])
                        ).decode('utf-8')
                        await websocket.send_json({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": audio_base64}
                        })
                    elif data.get("type") in LOG_EVENT_TYPES:
                        print(f"[OpenAI Event] {data['type']}")
            except Exception as e:
                print(f"Error sending to Twilio: {e}")

        await asyncio.gather(from_twilio(), to_twilio())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
