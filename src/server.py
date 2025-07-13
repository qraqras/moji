from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
import whisper
import tempfile
import asyncio

app = FastAPI()

model = whisper.load_model("base", device="cpu")

html_mic = """
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

html_capture = """
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
                .getDisplayMedia({ video: true, audio: true, systemAudio: "include" }) // video: true を指定
                .then((stream) => {
                    const audioTracks = stream.getAudioTracks();
                    const audioStream = new MediaStream(audioTracks);

                    let ws = null;
                    const mediaRecorder = new MediaRecorder(audioStream);
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
async def get_mic():
    return HTMLResponse(html_mic)


@app.get("/capture")
async def get_capture():
    return HTMLResponse(html_capture)


@app.get("/download")
async def download(filename = None):
    return FileResponse(filename, filename="recorded.webm", media_type="video/webm")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    with tempfile.NamedTemporaryFile(suffix=".webm") as tmp:
        await websocket.send_text(tmp.name)
        try:
            buffer = bytearray()
            last_transcribe = asyncio.get_event_loop().time()
            next_clip_timestamps = 0
            while True:
                data = await websocket.receive_bytes()
                if len(data) > 0:
                    buffer.extend(data)
                now = asyncio.get_event_loop().time()
                if now - last_transcribe > 60 or len(data) == 0:
                    last_transcribe = now
                    if len(buffer) > 0:
                        tmp.write(buffer)
                        tmp.flush()
                        buffer = bytearray()
                    result = await transcribe(tmp, str(next_clip_timestamps))
                    if len(result["segments"]) > 0:
                        next_clip_timestamps = result["segments"][-1]["start"]
                    await websocket.send_text(format_transcription(result))
                if len(data) == 0:
                    await websocket.close()
                    break
        except WebSocketDisconnect:
            print("disconnected!")


async def transcribe(file, clip_timestamps = "0"):
    return model.transcribe(file.name, language="ja", clip_timestamps=str(clip_timestamps))


def format_transcription(result):
    lines = []
    for segment in result["segments"]:
        line = f"[{segment["start"]:08.2f}-{segment["end"]:08.2f}]\t{segment["text"]}"
        lines.append(line)
    print("********************************")
    print("\n".join(lines))
    print("********************************")
    return "\n".join(lines) or "No transcription available."
