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

load_dotenv()

app = FastAPI()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PORT = int(os.getenv('PORT', 10000))

SYSTEM_MESSAGE = (
    "You are a helpful, bubbly AI assistant. You love answering questions, "
    "telling jokes, and helping people. Be friendly and engaging!"
)

LOG_EVENT_TYPES = [
    'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created'
]

if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY. Set it as an environment variable.")

@app.get("/", response_class=JSONResponse)
async def home():
    return {"status": "Voice bot is live and listening!"}

@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """TwiML response to connect Twilio MediaStream to our WebSocket."""
    host = request.url.hostname
    response = VoiceResponse()
    response.say("Connecting you to the AI assistant.")
    connect = Connect()
    connect.stream(
        url=f"wss://{host}/media-stream",
        track="inbound_track",  # Only caller's voice
        audio_config={"codec": "mulaw", "sample_rate": 8000}
    )
    response.append(connect)
    return HTMLResponse(str(response), media_type="application/xml")

@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    print("📞 Twilio WebSocket connected.")

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

        async def from_twilio():
            nonlocal stream_sid
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    print("📡 Twilio Event:", data['event'])

                    if data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        print("🔗 Stream started:", stream_sid)

                    elif data['event'] == 'media' and openai_ws.open:
                        payload = data['media']['payload']
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": payload
                        }))
                        print("🔊 Sent audio to OpenAI (length):", len(payload))

            except WebSocketDisconnect:
                print("🚫 Twilio WebSocket disconnected.")
            except Exception as e:
                print("❌ Error from_twilio:", e)

        async def to_twilio():
            try:
                async for message in openai_ws:
                    data = json.loads(message)
                    if data.get("type") in LOG_EVENT_TYPES:
                        print("🧠 OpenAI Event:", data['type'])

                    elif data.get("type") == "response.audio.delta" and data.get("delta"):
                        try:
                            audio_payload = base64.b64encode(
                                base64.b64decode(data["delta"])
                            ).decode("utf-8")

                            await websocket.send_json({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": audio_payload}
                            })
                            print("🔈 Sent audio response to Twilio.")

                        except Exception as e:
                            print("❌ Error decoding/sending audio:", e)

            except Exception as e:
                print("❌ Error to_twilio:", e)

        await asyncio.gather(from_twilio(), to_twilio())
