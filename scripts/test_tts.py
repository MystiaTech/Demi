#!/usr/bin/env python3
"""
TTS Diagnostic and Test Script for Demi.

Tests Text-to-Speech functionality and reports status.
Run with: python scripts/test_tts.py

This script will:
1. Check TTS backend availability (Piper, pyttsx3)
2. List available voices
3. Synthesize test audio
4. Report any issues
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import get_logger

logger = get_logger()


def check_dependencies():
    """Check which TTS dependencies are installed."""
    print("=" * 60)
    print("TTS DEPENDENCY CHECK")
    print("=" * 60)
    
    results = {
        "piper": False,
        "pyttsx3": False,
        "onnxruntime": False,
    }
    
    # Check Piper
    try:
        from piper import PiperVoice
        results["piper"] = True
        print("✅ piper-tts: INSTALLED")
    except ImportError:
        print("❌ piper-tts: NOT INSTALLED")
        print("   Install: pip install piper-tts")
    
    # Check pyttsx3
    try:
        import pyttsx3
        results["pyttsx3"] = True
        print("✅ pyttsx3: INSTALLED")
    except ImportError:
        print("❌ pyttsx3: NOT INSTALLED")
        print("   Install: pip install pyttsx3")
    
    # Check ONNX Runtime
    try:
        import onnxruntime as ort
        results["onnxruntime"] = True
        print(f"✅ onnxruntime: INSTALLED ({ort.__version__})")
    except ImportError:
        print("❌ onnxruntime: NOT INSTALLED")
        print("   Install: pip install onnxruntime-gpu (or onnxruntime for CPU)")
    
    print()
    return results


def check_voice_files():
    """Check if Piper voice files exist."""
    print("=" * 60)
    print("PIPER VOICE FILES CHECK")
    print("=" * 60)
    
    voices_dir = Path.home() / ".demi" / "voices" / "piper"
    
    if not voices_dir.exists():
        print(f"❌ Voices directory not found: {voices_dir}")
        print("   Run: ./scripts/download_piper_voices.sh en_US-lessac-medium")
        return []
    
    # Look for .onnx files
    onnx_files = list(voices_dir.glob("*.onnx"))
    
    if not onnx_files:
        print(f"❌ No voice models found in: {voices_dir}")
        print("   Run: ./scripts/download_piper_voices.sh en_US-lessac-medium")
    else:
        print(f"✅ Found {len(onnx_files)} voice model(s):")
        for f in onnx_files:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   - {f.name} ({size_mb:.1f} MB)")
    
    print()
    return onnx_files


async def test_pyttsx3():
    """Test pyttsx3 backend."""
    print("=" * 60)
    print("PYTTSX3 BACKEND TEST")
    print("=" * 60)
    
    try:
        import pyttsx3
        
        # Initialize engine
        engine = pyttsx3.init()
        print("✅ Engine initialized")
        
        # List voices
        voices = engine.getProperty("voices")
        print(f"\n📢 Available Voices ({len(voices)}):")
        for i, voice in enumerate(voices[:10]):  # Limit to 10
            gender = "F" if any(x in voice.name.lower() for x in ["female", "woman", "zira", "hazel"]) else "M"
            print(f"   {i+1}. {voice.name} ({gender})")
        
        if len(voices) > 10:
            print(f"   ... and {len(voices) - 10} more")
        
        # Get current settings
        rate = engine.getProperty("rate")
        volume = engine.getProperty("volume")
        print(f"\n⚙️ Current Settings:")
        print(f"   Rate: {rate} WPM")
        print(f"   Volume: {volume}")
        
        # Try to synthesize
        test_text = "Hello, I am Demi."
        output_path = "/tmp/test_pyttsx3.wav"
        
        print(f"\n🎵 Synthesizing test audio...")
        engine.save_to_file(test_text, output_path)
        engine.runAndWait()
        
        if os.path.exists(output_path):
            size_kb = os.path.getsize(output_path) / 1024
            print(f"✅ Audio saved: {output_path} ({size_kb:.1f} KB)")
            os.remove(output_path)
        else:
            print("❌ Failed to save audio")
        
        engine.stop()
        print("\n✅ pyttsx3 test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ pyttsx3 test FAILED: {e}")
        return False


async def test_piper():
    """Test Piper TTS backend."""
    print("=" * 60)
    print("PIPER BACKEND TEST")
    print("=" * 60)
    
    try:
        from src.voice.piper_tts import PiperTTS, PiperTTSConfig
        
        config = PiperTTSConfig(
            voice_id="en_US-lessac-medium",
            use_gpu=False,  # Use CPU for testing
        )
        
        print("🔄 Initializing Piper TTS...")
        engine = PiperTTS(config)
        
        if engine.voice is None:
            print("❌ No voice loaded - voice files missing")
            return False
        
        print("✅ Engine initialized")
        print(f"   Voice: {engine.config.voice_id}")
        print(f"   GPU: {engine.config.use_gpu}")
        
        # List voices
        voices = engine.list_voices()
        print(f"\n📢 Available Voices ({len(voices)}):")
        for v in voices[:5]:
            print(f"   - {v.get('name', v.get('id'))}")
        
        # Try to synthesize
        test_text = "Hello, I am Demi."
        output_path = "/tmp/test_piper.wav"
        
        print(f"\n🎵 Synthesizing test audio...")
        result = await engine.speak(
            text=test_text,
            save_path=output_path,
            play_immediately=False
        )
        
        if result and os.path.exists(output_path):
            size_kb = os.path.getsize(output_path) / 1024
            print(f"✅ Audio saved: {output_path} ({size_kb:.1f} KB)")
            print(f"   Latency: {result.get('latency_ms', 'N/A')} ms")
            os.remove(output_path)
        else:
            print("❌ Failed to save audio")
        
        print("\n✅ Piper test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Piper test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tts_main():
    """Test the main TTS interface."""
    print("=" * 60)
    print("MAIN TTS INTERFACE TEST")
    print("=" * 60)
    
    try:
        from src.voice.tts import TextToSpeech, TTSConfig
        
        print("🔄 Initializing TTS with auto-detect backend...")
        tts = TextToSpeech()
        
        backend = tts.get_backend()
        if backend is None:
            print("❌ No TTS backend available!")
            return False
        
        print(f"✅ Backend: {backend}")
        
        # List voices
        voices = tts.list_voices()
        print(f"\n📢 Available Voices ({len(voices)}):")
        for v in voices[:5]:
            print(f"   - {v.get('name', v.get('id'))}")
        
        # Get stats
        stats = tts.get_stats()
        print(f"\n📊 TTS Stats:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Try to synthesize
        test_text = "Hello, I am Demi, your divine companion."
        output_path = "/tmp/test_tts_main.wav"
        
        print(f"\n🎵 Synthesizing test audio...")
        print(f"   Text: '{test_text}'")
        
        result = await tts.speak(
            text=test_text,
            save_path=output_path,
            play_immediately=False
        )
        
        if result and os.path.exists(output_path):
            size_kb = os.path.getsize(output_path) / 1024
            print(f"✅ Audio saved: {output_path} ({size_kb:.1f} KB)")
            os.remove(output_path)
        else:
            print("❌ Failed to save audio")
        
        print("\n✅ Main TTS test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Main TTS test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_recommendations(deps, voices):
    """Print recommendations based on test results."""
    print("=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    
    if not any(deps.values()):
        print("⚠️  No TTS backends installed!")
        print("   Install at least one:")
        print("   - pip install pyttsx3  (quickest, uses system voices)")
        print("   - pip install piper-tts onnxruntime  (higher quality)")
    
    elif deps["piper"] and not voices:
        print("⚠️  Piper is installed but no voice files found!")
        print("   Download a voice:")
        print("   ./scripts/download_piper_voices.sh en_US-lessac-medium")
    
    elif deps["pyttsx3"] and not deps["piper"]:
        print("ℹ️  Using pyttsx3 (fallback)")
        print("   For better quality, install Piper:")
        print("   - pip install piper-tts onnxruntime")
        print("   - ./scripts/download_piper_voices.sh en_US-lessac-medium")
    
    if deps["piper"] and voices:
        print("✅ TTS is fully configured!")
        print("   Piper with voice files is the best setup.")
    
    print()


async def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("DEMI TTS DIAGNOSTIC TOOL")
    print("=" * 60 + "\n")
    
    # Check dependencies
    deps = check_dependencies()
    
    # Check voice files
    voices = check_voice_files()
    
    results = {
        "pyttsx3": False,
        "piper": False,
        "main": False,
    }
    
    # Test pyttsx3 if available
    if deps["pyttsx3"]:
        print()
        results["pyttsx3"] = await test_pyttsx3()
    
    # Test Piper if available and voices exist
    if deps["piper"]:
        print()
        results["piper"] = await test_piper()
    
    # Test main TTS interface
    print()
    results["main"] = await test_tts_main()
    
    # Recommendations
    print()
    print_recommendations(deps, voices)
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.upper()}: {status}")
    
    if any(results.values()):
        print("\n🎉 TTS is working! Demi can speak.")
    else:
        print("\n⚠️  TTS is not working. Check errors above.")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())
