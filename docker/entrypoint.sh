#!/usr/bin/env bash
VALID_COMMANDS=("speak" "download" "server")

DATA_DIR='/data'
COMMAND="$1"
shift

# Default voice model from environment variable
DEFAULT_MODEL="${PIPER_MODEL:-/data/de_DE-thorsten-medium.onnx}"

case "${COMMAND}" in
  speak)
    exec python3 -m piper --data-dir "${DATA_DIR}" "$@"
    ;;
  download)
    exec python3 -m piper.download_voices --data-dir "${DATA_DIR}" "$@"
    ;;
  server)
    # Use model from args or default from environment
    MODEL_PATH=""
    ARGS=("$@")
    
    # Check if -m flag is provided
    for i in "${!ARGS[@]}"; do
      if [[ "${ARGS[$i]}" == "-m" ]] && [[ -n "${ARGS[$((i+1))]}" ]]; then
        MODEL_PATH="${ARGS[$((i+1))]}"
        break
      fi
    done
    
    # If no -m flag, use default model
    if [[ -z "$MODEL_PATH" ]]; then
      MODEL_PATH="$DEFAULT_MODEL"
      # Add -m flag to args
      set -- "-m" "$MODEL_PATH" "$@"
    fi
    
    # Auto-download voice model if it doesn't exist
    if [[ ! -f "$MODEL_PATH" ]]; then
      # Extract voice name from path (e.g., /data/de_DE-thorsten-medium.onnx -> de_DE-thorsten-medium)
      VOICE_NAME=$(basename "$MODEL_PATH" .onnx)
      echo "Voice model not found: $MODEL_PATH"
      echo "Downloading voice: $VOICE_NAME ..."
      python3 -m piper.download_voices --data-dir "${DATA_DIR}" "$VOICE_NAME"
      echo "Download complete."
    fi
    
    echo "Starting Piper TTS server with model: $MODEL_PATH"
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
    echo "  PIPER_API_KEY   API key for authentication (optional)"
    echo "  PIPER_MODEL     Path to voice model (default: /data/de_DE-thorsten-medium.onnx)"
    exit 0
    ;;
  *)
    echo "Error: Unknown command '$COMMAND'"
    echo "Run with --help for usage."
    exit 1
    ;;
esac
