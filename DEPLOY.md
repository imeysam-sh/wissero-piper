# Deploying Wissero-Piper

This guide explains how to deploy the Piper TTS server with streaming support using Docker.

## Prerequisites

- **Docker** installed on your server.
- Git access to this repository.

---

## Deployment with Coolify

Coolify can build directly from the Dockerfile in this repository.

### 1. Create New Service

1. In Coolify, create a new **Docker** service
2. Point it to: `https://github.com/imeysam-sh/wissero-piper.git`
3. Build path: `/` (root)

### 2. Configure Environment Variables

| Variable | Value | Required |
|----------|-------|----------|
| `PIPER_API_KEY` | `your-secret-api-key` | Recommended |

### 3. Add Volume Mount

| Field | Value |
|-------|-------|
| **Name** | `piper-data` |
| **Source Path** | (leave empty or custom path) |
| **Destination Path** | `/data` |

### 4. Set Start Command

In Coolify's configuration, find **"Custom Start Command"** or **"Docker Command"** and set:

```
server -m /data/de_DE-thorsten-medium.onnx
```

### 5. Deploy

Click **Deploy**. The container will:
1. Start up
2. **Automatically download** the voice model if it doesn't exist
3. Start the API server

**No SSH or manual steps required!**

---

## API Authentication

When `PIPER_API_KEY` is set, **all requests must include the key**.

### Your Client (Wissero) Must Send:

```javascript
// Example: calling from your Next.js app
const response = await fetch('https://your-piper-server.com/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_API_KEY_HERE'
  },
  body: JSON.stringify({ 
    text: 'Hello world',
    length_scale: 1.3,
    output_raw: true
  })
});
```

### Supported Authentication Methods:

| Method | Header/Param |
|--------|--------------|
| Bearer Token | `Authorization: Bearer <key>` |
| API Key Header | `X-API-Key: <key>` |
| Query Parameter | `?api_key=<key>` |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/` | Synthesize speech |
| `GET` | `/voices` | List available voices |
| `POST` | `/download` | Download a new voice |

---

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
| `output_raw` | boolean | false | Return raw PCM (no WAV header) |
| `length_scale` | float | 1.0 | Speech speed (higher = slower) |

---

## Changing Voice Models

To use a different voice:

1. Update the start command: `server -m /data/<voice-name>.onnx`
2. Redeploy - the new voice will be auto-downloaded

Available voices: https://huggingface.co/rhasspy/piper-voices
