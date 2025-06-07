import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
from dotenv import load_dotenv

# Load .env variables if available
load_dotenv()

# App setup
app = FastAPI()

# Constants
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PORT = int(os.getenv('PORT', 10000))  # Render sets this automatically
RENDER_DOMAIN = "twilio-voice-bot-dr96.onrender.com"  # Update with your Render URL

SYSTEM_MESSAGE = (
    "You are a helpful and cheerful AI assistant. "
    "Speak clearly and positively. Occasionally crack a dad joke."
)

LOG_EVENTS = [
    "response.content.done", "rate_limits.updated", "response.done",
    "input_audio_buffer.committed", "input_audio_buffer.speech_stopped",
    "input_audio_buffer.speech_started", "session.created"
]

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing. Set it in Render > Environment.")

# Home route
@app.get("/", response_class=JSONResponse)
async def root():
    return {"message": "Twilio OpenAI Voice Bot is running."}

# Twilio incoming call route
@app.api_route("/incoming-call", methods=["GET", "POST"])
async def incoming_call(request: Request):
    response = VoiceResponse()
    response.say("Connecting you to our AI agent.")
    response.pause(length=1)
    response.say("You can begin speaking.")

    # WSS to media-stream
    connect = Connect()
    connect.stream(url=f"wss://{RENDER_DOMAIN}/media-stream")
    response.append(connect)

    return HTMLResponse(content=str(response), media_type="application/xml")

# WebSocket handler for Twilio <Stream>
@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    print("✅ Twilio WebSocket connected")

    # Connect to OpenAI Realtime API
    async with websockets.connect(
        "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01",
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:
        await openai_ws.send(json.dumps({
            "type": "session.create",
            "messages": [{"role": "system", "content": SYSTEM_MESSAGE}]
        }))

        stream_sid = None

        async def receive_from_twilio():
            nonlocal stream_sid
            try:
                async for msg in websocket.iter_text():
                    event = json.loads(msg)

                    if event.get("event") == "start":
                        stream_sid = event["start"]["streamSid"]
                        print(f"🔄 Stream started: {stream_sid}")

                    elif event.get("event") == "media":
                        payload = event["media"]["payload"]
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": payload
                        }))
            except WebSocketDisconnect:
                print("⛔ Twilio disconnected WebSocket")
            except Exception as e:
                print(f"❌ Error receiving from Twilio: {e}")

        async def send_to_twilio():
            try:
                async for msg in openai_ws:
                    data = json.loads(msg)

                    if data.get("type") in LOG_EVENTS:
                        print(f"[OpenAI]: {data['type']}")

                    if data.get("type") == "response.audio.delta" and data.get("delta"):
                        try:
                            audio_b64 = base64.b64encode(
                                base64.b64decode(data["delta"])
                            ).decode("utf-8")
                            await websocket.send_json({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": audio_b64}
                            })
                        except Exception as e:
                            print(f"❌ Failed to send audio to Twilio: {e}")
            except Exception as e:
                print(f"❌ Error sending to Twilio: {e}")

        await asyncio.gather(receive_from_twilio(), send_to_twilio())
