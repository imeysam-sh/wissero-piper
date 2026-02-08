#!/usr/bin/env bash
VALID_COMMANDS=("speak" "download" "server")

DATA_DIR='/data'
COMMAND="$1"
shift

# Default voice model to download if none specified
DEFAULT_VOICE="${PIPER_DEFAULT_VOICE:-de_DE-thorsten-medium}"

case "${COMMAND}" in
  speak)
    exec python3 -m piper --data-dir "${DATA_DIR}" "$@"
    ;;
  download)
    exec python3 -m piper.download_voices --data-dir "${DATA_DIR}" "$@"
    ;;
  server)
    # Extract model path from arguments
    MODEL_PATH=""
    for arg in "$@"; do
      if [[ "$arg" == /data/*.onnx ]]; then
        MODEL_PATH="$arg"
        break
      fi
    done
    
    # If model path provided via -m flag, extract it
    ARGS=("$@")
    for i in "${!ARGS[@]}"; do
      if [[ "${ARGS[$i]}" == "-m" ]] && [[ -n "${ARGS[$((i+1))]}" ]]; then
        MODEL_PATH="${ARGS[$((i+1))]}"
        break
      fi
    done
    
    # Auto-download voice model if it doesn't exist
    if [[ -n "$MODEL_PATH" ]] && [[ ! -f "$MODEL_PATH" ]]; then
      # Extract voice name from path (e.g., /data/de_DE-thorsten-medium.onnx -> de_DE-thorsten-medium)
      VOICE_NAME=$(basename "$MODEL_PATH" .onnx)
      echo "Voice model not found: $MODEL_PATH"
      echo "Downloading voice: $VOICE_NAME ..."
      python3 -m piper.download_voices --data-dir "${DATA_DIR}" "$VOICE_NAME"
      echo "Download complete."
    fi
    
    exec python3 -m piper.http_api --host 0.0.0.0 --data-dir "${DATA_DIR}" "$@"
    ;;
  ""|help|-h|--help)
    echo "Usage: <command> [args...]"
    echo "Available commands:"
    echo "  speak        Synthesize audio from text"
    echo "  download     Download voices"
    echo "  server       Run HTTP server"
    echo ""
    echo "Environment variables:"
    echo "  PIPER_API_KEY         API key for authentication (optional)"
    echo "  PIPER_DEFAULT_VOICE   Default voice to download (default: de_DE-thorsten-medium)"
    exit 0
    ;;
  *)
    echo "Error: Unknown command '$COMMAND'"
    echo "Run with --help for usage."
    exit 1
    ;;
esac
