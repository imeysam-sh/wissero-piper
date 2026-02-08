# Deploying Wissero-Piper

This guide explains how to deploy the Piper TTS server with streaming support using Docker.

## Prerequisites

- **Docker** and **Docker Compose** installed on your server.
- Git (to clone the repository).

## 1. Clone the Repository

```bash
git clone https://github.com/imeysam-sh/wissero-piper.git
cd wissero-piper
```

## 2. Build the Docker Image

Build the container image directly on your server:

```bash
docker-compose build
```

## 3. Download Voice Models

Before starting the server, you need to download at least one voice model. The models are stored in the `./piper_data` directory, which is mounted to `/data` inside the container.

To download a voice (e.g., `de_DE-thorsten-medium`), run:

```bash
docker-compose run --rm piper download de_DE-thorsten-medium
```

Wait for the download to complete. You can verify the file exists locally in your `piper_data` folder.

## 4. configure and Start the Server

By default, the `docker-compose.yml` is configured to use `de_DE-thorsten-medium.onnx`. Usually, you don't need to change anything if you downloaded that specific voice.

Start the server in detached mode (background):

```bash
docker-compose up -d
```

The server will be available at `http://localhost:5000`.

## 5. Using the API with Streaming

You can now generate speech, including streaming support!

**Basic Request (WAV with header):**
```bash
curl -X POST -d '{"text": "Hallo Welt"}' http://localhost:5000/ -o output.wav
```

**Streaming Request (Raw PCM):**
```bash
curl -X POST -d '{"text": "Dies ist ein Streaming Test", "output_raw": true}' http://localhost:5000/ --no-buffer -o stream.pcm
```

## Changing the Voice

If you want to use a different voice:
1.  Download it: `docker-compose run --rm piper download <new-voice-name>`
2.  Update `docker-compose.yml` command line: `command: server -m /data/<new-voice-name>.onnx`
3.  Restart: `docker-compose up -d`
