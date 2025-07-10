from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import whisper
import tempfile
import asyncio
import io

app = FastAPI()

model = whisper.load_model("tiny")

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>TEST</title>
    </head>
    <body>
        <div id="container"></div>
        <div id="moji"></div>
        <script>
            // create buttons
            const start = document.createElement("button");
            const stop = document.createElement("button");
            const pause = document.createElement("button");
            const resume = document.createElement("button");
            start.innerText = "start";
            stop.innerText = "stop";
            pause.innerText = "pause";
            resume.innerText = "resume";
            start.disabled = false;
            stop.disabled = true;
            pause.disabled = true;
            resume.disabled = true;
            //
            const container = document.getElementById("moji");

            window.onload = (e) => {
                const container = document.getElementById("container");
                container.appendChild(start);
                container.appendChild(stop);
                container.appendChild(pause);
                container.appendChild(resume);
            }

            navigator.mediaDevices
                .getUserMedia({ video: false, audio: true })
                .then((stream) => {
                    let ws = null;
                    const mediaRecorder = new MediaRecorder(stream);
                    // START
                    start.onclick = (e) => {
                        ws = new WebSocket("ws://localhost:8000/ws");
                        ws.onclose = (event) => {
                            mediaRecorder.stop();
                        };
                        ws.onmessage = (event) => {
                            while(moji.firstChild) {
                                moji.removeChild(moji.firstChild);
                            }
                            const p = document.createElement("p");
                            p.innerText = event.data;
                            moji.appendChild(p);
                        };

                        e.currentTarget.disabled = true;
                        stop.disabled = false;
                        mediaRecorder.start(2000);
                        console.log("recorder started");
                    };
                    // STOP
                    stop.onclick = (e) => {
                        e.currentTarget.disabled = true;
                        start.disabled = false;
                        mediaRecorder.stop();
                        console.log("recorder stopped");
                        ws.send(new ArrayBuffer(0));
                    };
                    // PAUSE
                    pause.onclick = (e) => {
                        ;
                    };
                    // RESUME
                    resume.onclick = (e) => {
                        ;
                    };
                    mediaRecorder.ondataavailable = (e) => {
                        console.log("nodataavailable");
                        if (e.data && e.data.size > 0) {
                            e.data.arrayBuffer().then(buf => {
                                ws.send(buf);
                            });
                        }
                    };
                    mediaRecorder.onstop = (e) => {
                        if (e.data && e.data.size > 0) {
                            e.data.arrayBuffer().then(buf => {
                                ws.send(buf);
                            });
                        }
                    };
                })
                .catch((err) => {
                    console.error(`you got an error: ${err}`);
                });
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    buffer = bytearray()
    last_transcribe = asyncio.get_event_loop().time()
    with tempfile.NamedTemporaryFile(suffix=".webm") as tmp:
        try:
            while True:
                data = await websocket.receive_bytes()
                if len(data) == 0:
                    output = await transcribe(tmp, buffer)
                    await websocket.send_text(output)
                    print(output)
                    buffer = bytearray()
                else:
                    buffer.extend(data)
                now = asyncio.get_event_loop().time()
                if now - last_transcribe > 30 and len(buffer) > 0:
                    last_transcribe = now
                    output = await transcribe(tmp, buffer)
                    await websocket.send_text(output)
                    print(output)
        except WebSocketDisconnect:
            print("disconnected!")

async def transcribe(file, data):
    file.write(data)
    file.flush()
    result = model.transcribe(file.name, language="ja")
    lines = []
    for segment in result['segments']:
        lines.append(f"[{segment['start']}-{segment['end']}]\t{segment["text"]}")
    return "\n".join(lines)
