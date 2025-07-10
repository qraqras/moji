FROM python:3.13.5-bookworm
COPY requirements.txt /tmp
RUN apt update && apt install -y ffmpeg portaudio19-dev
RUN pip install --no-cache-dir -r /tmp/requirements.txt
