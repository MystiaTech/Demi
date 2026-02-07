#!/bin/bash
# Setup script for Demi's Goddess Voice (High-quality TTS with divine enhancement)

set -e

echo "🔮 Setting up Demi's Goddess Voice..."
echo ""

# Install Coqui TTS (best quality backend)
echo "📦 Installing Coqui TTS (XTTS-v2)..."
pip install TTS torch torchaudio

# Install audio processing libraries for goddess voice enhancement
echo "🎵 Installing audio processing libraries..."
pip install librosa soundfile scipy pyloudnorm

# Install optional: accelerator for faster inference
echo "⚡ Installing optional acceleration..."
pip install accelerate  # For faster Coqui inference on GPU

echo ""
echo "✨ Goddess Voice setup complete!"
echo ""
echo "Configuration options in .env:"
echo "  TTS_BACKEND=coqui           # Use Coqui XTTS-v2 for best quality"
echo "  TTS_DEVICE=cuda             # Use GPU if available (cuda/cpu/mps)"
echo "  COQUI_SPEAKER_WAV=<path>    # Optional: reference voice for voice cloning"
echo ""
echo "Next steps:"
echo "  1. Find a reference voice audio (10-30s of goddess-like feminine voice)"
echo "  2. Convert to WAV format: ffmpeg -i input.mp3 reference.wav"
echo "  3. Set COQUI_SPEAKER_WAV=reference.wav in .env"
echo "  4. Restart Demi to use the reference voice"
echo ""
echo "Reference voice options:"
echo "  - Download from YouTube/audio libraries (use youtube-dl or similar)"
echo "  - Record yourself with a feminine, ethereal voice"
echo "  - Use character voice samples (check licensing)"
echo ""
