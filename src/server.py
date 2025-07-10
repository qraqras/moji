from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import whisper
import tempfile

app = FastAPI()

model = whisper.load_model("base")

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>TEST</title>
    </head>
    <body>
        <div id="container"></div>
        <script>
            const record = document.createElement("button");
            record.innerText = "record";
            const stop = document.createElement("button");
            stop.innerText = "stop";
            stop.disabled = true;

            window.onload = (e) => {
                const container = document.getElementById("container");
                container.appendChild(record);
                container.appendChild(stop);
            }

            navigator.mediaDevices
                .getUserMedia({ video: false, audio: true })
                .then((stream) => {
                    const ws = new WebSocket("ws://localhost:8000/ws");
                    const context = new AudioContext();
                    const mediaRecorder = new MediaRecorder(stream);
                    let chunks = [];
                    record.onclick = (e) => {
                        e.currentTarget.disabled = true;
                        stop.disabled = false;
                        mediaRecorder.start();
                        console.log(mediaRecorder.state);
                        console.log("recorder started");
                    };
                    stop.onclick = (e) => {
                        e.currentTarget.disabled = true;
                        record.disabled = false;
                        mediaRecorder.stop();
                        console.log(mediaRecorder.state);
                        console.log("recorder stopped");
                    };
                    mediaRecorder.ondataavailable = (e) => {
                        chunks.push(e.data);
                    };
                    mediaRecorder.onstop = (e) => {
                        const blob = new Blob(chunks, { type: "audio/webm" });
                        blob.arrayBuffer().then(buf => {
                            ws.send(buf);
                            chunks = [];
                        });
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
    while True:
        data = await websocket.receive_bytes()
        with tempfile.NamedTemporaryFile(suffix=".webm") as tmp:
            tmp.write(data)
            tmp.flush()
            result = model.transcribe(tmp.name)
            print("********************************")
            print(result["text"])
            print("********************************")
        await websocket.send_text(f"Message text was: {data}")
