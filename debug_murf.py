#!/usr/bin/env python3
"""
Debug script to test the updated Murf AI implementation
"""
import os
import asyncio
from tts_providers import TTSProviderFactory
from tts_providers import TTSRequest

async def test_murf_provider():
    """Test the updated Murf AI provider"""
    
    # Check if API key is available
    api_key = os.getenv("MURF_API_KEY")
    if not api_key:
        print("❌ MURF_API_KEY not set. Please set it to test:")
        print("   export MURF_API_KEY=your_key_here")
        return
    
    print("🧪 Testing updated Murf AI provider...")
    
    try:
        # Create provider
        provider = TTSProviderFactory.create_provider("murf")
        print(f"✅ Provider created: {provider.provider_id}")
        
        # Get available voices
        voices = provider.get_available_voices()
        print(f"🎙️ Available voices: {voices}")
        
        # Create test request
        test_request = TTSRequest(
            text="Hello, this is a test of the updated Murf AI integration.",
            voice=voices[0] if voices else "en-US-sarah",
            speed=1.0,
            format="mp3"
        )
        
        print(f"📤 Testing with voice: {test_request.voice}")
        
        # Generate speech
        result = await provider.generate_speech(test_request)
        
        if result.success:
            print(f"✅ Success! Generated {result.file_size_bytes} bytes in {result.latency_ms:.1f}ms")
            print(f"   Metadata: {result.metadata}")
            
            # Save audio file for verification
            if result.audio_data:
                filename = f"test_murf_output.{test_request.format}"
                with open(filename, 'wb') as f:
                    f.write(result.audio_data)
                print(f"💾 Audio saved as {filename}")
        else:
            print(f"❌ Failed: {result.error_message}")
            if result.metadata:
                print(f"   Debug info: {result.metadata}")
                
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_murf_provider())
