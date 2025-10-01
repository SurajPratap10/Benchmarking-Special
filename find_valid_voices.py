#!/usr/bin/env python3
"""
Script to find valid Murf AI voice IDs by testing common patterns
"""
import os
import asyncio
import aiohttp
import json

# Common voice name patterns to test
VOICE_PATTERNS = [
    # Female voices
    "en-US-natalie",  # We know this works
    "en-US-hazel",
    "en-US-lisa", 
    "en-US-emma",
    "en-US-sarah",
    "en-US-olivia",
    "en-US-sophia",
    "en-US-emily",
    "en-US-rachel",
    "en-US-anna",
    
    # Male voices  
    "en-US-james",
    "en-US-david",
    "en-US-alex",
    "en-US-mike",
    "en-US-john",
    "en-US-robert",
    "en-US-william",
    "en-US-daniel",
    "en-US-michael",
    "en-US-chris",
    
    # UK voices
    "en-UK-hazel",
    "en-UK-james",
    "en-UK-david",
    "en-UK-emma"
]

async def test_voice_id(session, api_key, voice_id):
    """Test if a voice ID is valid"""
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": "Test",
        "voiceId": voice_id,
        "audioFormat": "mp3"
    }
    
    try:
        async with session.post(
            "https://api.murf.ai/v1/speech/generate",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 200:
                return True, "✅ Valid"
            else:
                error_text = await response.text()
                if "Invalid voice_id" in error_text:
                    return False, "❌ Invalid voice_id"
                else:
                    return False, f"❌ Error {response.status}"
    except Exception as e:
        return False, f"❌ Exception: {str(e)}"

async def find_valid_voices():
    """Find valid voice IDs from common patterns"""
    api_key = os.getenv("MURF_API_KEY")
    if not api_key:
        print("❌ MURF_API_KEY not set. Please run:")
        print("   export MURF_API_KEY=your_actual_api_key")
        print("   ./venv/bin/python find_valid_voices.py")
        return
    
    print("🔍 Testing common voice ID patterns...")
    print("This may take a moment as we test each voice ID...\n")
    
    valid_voices = []
    invalid_voices = []
    
    async with aiohttp.ClientSession() as session:
        for voice_id in VOICE_PATTERNS:
            print(f"Testing {voice_id}...", end=" ")
            is_valid, status = await test_voice_id(session, api_key, voice_id)
            print(status)
            
            if is_valid:
                valid_voices.append(voice_id)
            else:
                invalid_voices.append((voice_id, status))
            
            # Small delay to be nice to the API
            await asyncio.sleep(0.5)
    
    print(f"\n📊 Results:")
    print(f"✅ Valid voices ({len(valid_voices)}):")
    for voice in valid_voices:
        print(f"   - {voice}")
    
    print(f"\n❌ Invalid voices ({len(invalid_voices)}):")
    for voice, reason in invalid_voices[:5]:  # Show first 5
        print(f"   - {voice}: {reason}")
    if len(invalid_voices) > 5:
        print(f"   ... and {len(invalid_voices) - 5} more")
    
    if valid_voices:
        print(f"\n🔧 To update your config.py, use:")
        print(f'supported_voices={valid_voices}')
        
        # Auto-update config if more than one valid voice found
        if len(valid_voices) > 1:
            try:
                with open('config.py', 'r') as f:
                    content = f.read()
                
                old_line = 'supported_voices=["en-US-natalie"]'
                new_line = f'supported_voices={valid_voices}'
                
                if old_line in content:
                    updated_content = content.replace(old_line, new_line)
                    with open('config.py', 'w') as f:
                        f.write(updated_content)
                    print(f"✅ Automatically updated config.py with {len(valid_voices)} valid voices!")
                
            except Exception as e:
                print(f"⚠️  Could not auto-update config.py: {e}")

if __name__ == "__main__":
    asyncio.run(find_valid_voices())
