# Deploying Wissero-Piper

This guide explains how to deploy the Piper TTS server with streaming support using Docker.

## Prerequisites

- **Docker** installed on your server.
- Git (to clone the repository).

## Deployment with Coolify

Coolify can build directly from the Dockerfile in this repository.

1. **Add a new service** in Coolify pointing to this Git repository.
2. **Set environment variables** in Coolify's service settings:
   - `PIPER_API_KEY`: Your secret API key (optional, but recommended for security).
3. **Configure the start command** (if needed):
   ```
   server -m /data/de_DE-thorsten-medium.onnx
   ```
4. **Mount a persistent volume** at `/data` to store voice models.
5. **Download a voice** before first use:
   ```bash
   docker exec <container_id> python3 -m piper.download_voices --data-dir /data de_DE-thorsten-medium
   ```

## Manual Docker Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/imeysam-sh/wissero-piper.git
cd wissero-piper
```

### 2. Build the Docker Image

```bash
docker build -t piper .
```

### 3. Download Voice Models

Create a directory for voice data and download a model:

```bash
mkdir piper_data
docker run --rm -v $(pwd)/piper_data:/data piper download de_DE-thorsten-medium
```

### 4. Run the Server

**Without API key (open access):**
```bash
docker run -d -p 5000:5000 -v $(pwd)/piper_data:/data --name piper_server piper server -m /data/de_DE-thorsten-medium.onnx
```

**With API key (recommended for production):**
```bash
docker run -d -p 5000:5000 \
  -e PIPER_API_KEY="your-secret-key-here" \
  -v $(pwd)/piper_data:/data \
  --name piper_server \
  piper server -m /data/de_DE-thorsten-medium.onnx
```

## API Authentication

When `PIPER_API_KEY` is set, all requests must include the key using one of these methods:

1. **Authorization header (recommended):**
   ```bash
   curl -H "Authorization: Bearer your-secret-key-here" \
     -X POST -d '{"text": "Hello"}' http://localhost:5000/
   ```

2. **X-API-Key header:**
   ```bash
   curl -H "X-API-Key: your-secret-key-here" \
     -X POST -d '{"text": "Hello"}' http://localhost:5000/
   ```

3. **Query parameter:**
   ```bash
   curl -X POST -d '{"text": "Hello"}' "http://localhost:5000/?api_key=your-secret-key-here"
   ```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/` | Synthesize speech (supports streaming) |
| `GET` | `/voices` | List downloaded voices |
| `POST` | `/download` | Download a new voice |

## Request Parameters

```json
{
  "text": "Text to synthesize",
  "output_raw": false,
  "length_scale": 1.0,
  "noise_scale": 0.667,
  "noise_w_scale": 0.8,
  "voice": "de_DE-thorsten-medium",
  "speaker_id": 0
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | string | required | Text to synthesize |
| `output_raw` | boolean | false | Return raw PCM instead of WAV |
| `length_scale` | float | 1.0 | Speech speed (higher = slower) |
| `noise_scale` | float | 0.667 | Voice variability |
| `noise_w_scale` | float | 0.8 | Phoneme width variability |
| `voice` | string | default | Voice model to use |
| `speaker_id` | int | 0 | Speaker ID for multi-speaker models |
