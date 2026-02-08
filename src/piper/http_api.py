
"""FastAPI web server with HTTP API for Piper."""
import argparse
import io
import json
import logging
import os
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator
from urllib.request import urlopen

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from . import PiperVoice, SynthesisConfig
from .download_voices import VOICES_JSON, download_voice

_LOGGER = logging.getLogger(__name__)

# API Key from environment variable (optional)
API_KEY = os.environ.get("PIPER_API_KEY", "")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to check API key if PIPER_API_KEY is set."""
    
    # Endpoints that don't require authentication
    PUBLIC_PATHS = {"/health", "/healthz", "/ready"}
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for health check endpoints
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        if not API_KEY:
            # No API key configured, allow all requests
            return await call_next(request)
        
        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token == API_KEY:
                return await call_next(request)
        
        # Check api_key query parameter
        api_key_param = request.query_params.get("api_key", "")
        if api_key_param == API_KEY:
            return await call_next(request)
        
        # Check X-API-Key header
        x_api_key = request.headers.get("X-API-Key", "")
        if x_api_key == API_KEY:
            return await call_next(request)
        
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key"}
        )


def main() -> None:
    """Run HTTP server."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0", help="HTTP server host")
    parser.add_argument("--port", type=int, default=5000, help="HTTP server port")
    #
    parser.add_argument("-m", "--model", required=True, help="Path to Onnx model file")
    #
    parser.add_argument("-s", "--speaker", type=int, help="Id of speaker (default: 0)")
    parser.add_argument(
        "--length-scale", "--length_scale", type=float, help="Phoneme length"
    )
    parser.add_argument(
        "--noise-scale", "--noise_scale", type=float, help="Generator noise"
    )
    parser.add_argument(
        "--noise-w-scale",
        "--noise_w_scale",
        "--noise-w",
        "--noise_w",
        type=float,
        help="Phoneme width noise",
    )
    #
    parser.add_argument("--cuda", action="store_true", help="Use GPU")
    #
    parser.add_argument(
        "--sentence-silence",
        "--sentence_silence",
        type=float,
        default=0.0,
        help="Seconds of silence after each sentence",
    )
    #
    parser.add_argument(
        "--data-dir",
        "--data_dir",
        action="append",
        default=[str(Path.cwd())],
        help="Data directory to check for downloaded models (default: current directory)",
    )
    parser.add_argument(
        "--download-dir",
        "--download_dir",
        help="Path to download voices (default: first data dir)",
    )
    #
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG messages to console"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    _LOGGER.debug(args)

    if not args.download_dir:
        # Download voices to first data directory if not specified
        args.download_dir = args.data_dir[0]

    download_dir = Path(args.download_dir)

    # Download voice if file doesn't exist
    model_path = Path(args.model)
    if not model_path.exists():
        # Look in data directories
        voice_name = args.model
        for data_dir in args.data_dir:
            maybe_model_path = Path(data_dir) / f"{voice_name}.onnx"
            _LOGGER.debug("Checking '%s'", maybe_model_path)
            if maybe_model_path.exists():
                model_path = maybe_model_path
                break

    if not model_path.exists():
        raise ValueError(
            f"Unable to find voice: {model_path} (use piper.download_voices)"
        )

    default_model_id = model_path.name.rstrip(".onnx")

    # Load voice
    default_voice = PiperVoice.load(model_path, use_cuda=args.cuda)
    loaded_voices: Dict[str, PiperVoice] = {default_model_id: default_voice}

    # Create web server
    app = FastAPI()
    
    # Add API key middleware if PIPER_API_KEY is set
    if API_KEY:
        app.add_middleware(APIKeyMiddleware)
        _LOGGER.info("API key authentication enabled")

    @app.get("/health")
    @app.get("/healthz")
    @app.get("/ready")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint - no auth required."""
        return {
            "status": "ok",
            "model": default_model_id,
            "voices_loaded": len(loaded_voices)
        }

    @app.get("/voices")
    async def app_voices() -> Dict[str, Any]:
        """List downloaded voices."""
        voices_dict: Dict[str, Any] = {}
        config_paths: List[Path] = [Path(f"{model_path}.json")]

        for data_dir in args.data_dir:
            for onnx_path in Path(data_dir).glob("*.onnx"):
                config_path = Path(f"{onnx_path}.json")
                if config_path.exists():
                    config_paths.append(config_path)

        for config_path in config_paths:
            model_id = config_path.name.rstrip(".onnx.json")
            if model_id in voices_dict:
                continue

            with open(config_path, "r", encoding="utf-8") as config_file:
                voices_dict[model_id] = json.load(config_file)

        return voices_dict

    @app.get("/all-voices")
    async def app_all_voices() -> Dict[str, Any]:
        """List all Piper voices."""
        with urlopen(VOICES_JSON) as response:
            return json.load(response)

    @app.post("/download")
    async def app_download(request: Request) -> str:
        """Download a voice."""
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        model_id = data.get("voice")
        if not model_id:
            raise HTTPException(status_code=400, detail="voice is required")

        force_redownload = data.get("force_redownload", False)
        download_voice(model_id, download_dir, force_redownload=force_redownload)

        return model_id

    @app.post("/")
    async def app_synthesize(request: Request) -> StreamingResponse:
        """Synthesize audio from text."""
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")
            
        text = data.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")

        _LOGGER.debug(data)

        model_id = data.get("voice", default_model_id)
        voice = loaded_voices.get(model_id)
        if voice is None:
            for data_dir in args.data_dir:
                maybe_model_path = Path(data_dir) / f"{model_id}.onnx"
                if maybe_model_path.exists():
                    _LOGGER.debug("Loading voice %s", model_id)
                    voice = PiperVoice.load(maybe_model_path, use_cuda=args.cuda)
                    loaded_voices[model_id] = voice
                    break

        if voice is None:
            _LOGGER.warning("Voice not found: %s. Using default voice.", model_id)
            voice = default_voice

        speaker_id: Optional[int] = data.get("speaker_id")
        if (voice.config.num_speakers > 1) and (speaker_id is None):
            speaker = data.get("speaker")
            if speaker:
                speaker_id = voice.config.speaker_id_map.get(speaker)

            if speaker_id is None:
                _LOGGER.warning(
                    "Speaker not found: '%s' in %s",
                    speaker,
                    voice.config.speaker_id_map.keys(),
                )
                speaker_id = args.speaker or 0

        if (speaker_id is not None) and (speaker_id > voice.config.num_speakers):
            speaker_id = 0

        syn_config = SynthesisConfig(
            speaker_id=speaker_id,
            length_scale=float(
                data.get(
                    "length_scale",
                    (
                        args.length_scale
                        if args.length_scale is not None
                        else voice.config.length_scale
                    ),
                )
            ),
            noise_scale=float(
                data.get(
                    "noise_scale",
                    (
                        args.noise_scale
                        if args.noise_scale is not None
                        else voice.config.noise_scale
                    ),
                )
            ),
            noise_w_scale=float(
                data.get(
                    "noise_w_scale",
                    (
                        args.noise_w_scale
                        if args.noise_w_scale is not None
                        else voice.config.noise_w_scale
                    ),
                )
            ),
        )

        output_raw = data.get("output_raw", False)

        def audio_stream() -> Generator[bytes, None, None]:
            wav_params_set = False
            
            for i, audio_chunk in enumerate(voice.synthesize(text, syn_config)):
                if not wav_params_set:
                    if not output_raw:
                        # Construct WAV header
                        # 44 bytes
                        # RIFF <size> WAVE fmt <chunk_size> <format> <channels> <sample_rate> <byte_rate> <block_align> <bits_per_sample> data <size>
                        
                        sample_rate = audio_chunk.sample_rate
                        num_channels = audio_chunk.sample_channels
                        bits_per_sample = 16 # Int16
                        byte_rate = sample_rate * num_channels * bits_per_sample // 8
                        block_align = num_channels * bits_per_sample // 8
                        
                        # Header
                        header = b'RIFF'
                        header += (2**31 - 1).to_bytes(4, 'little') # Placeholder file size
                        header += b'WAVEfmt '
                        header += (16).to_bytes(4, 'little') # Subchunk1Size
                        header += (1).to_bytes(2, 'little') # AudioFormat (1=PCM)
                        header += num_channels.to_bytes(2, 'little')
                        header += sample_rate.to_bytes(4, 'little')
                        header += byte_rate.to_bytes(4, 'little')
                        header += block_align.to_bytes(2, 'little')
                        header += bits_per_sample.to_bytes(2, 'little')
                        header += b'data'
                        header += (2**31 - 1).to_bytes(4, 'little') # Placeholder data size
                        
                        yield header
                        
                    wav_params_set = True

                if i > 0:
                    # Silence between sentences
                    num_silence_samples = int(voice.config.sample_rate * args.sentence_silence)
                    if num_silence_samples > 0:
                        yield bytes(num_silence_samples * 2) # 2 bytes per sample (16-bit)

                yield audio_chunk.audio_int16_bytes

        media_type = "audio/pcm" if output_raw else "audio/wav"
        return StreamingResponse(audio_stream(), media_type=media_type)

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
