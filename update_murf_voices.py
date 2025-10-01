#!/usr/bin/env python3
"""
Utility script to update Murf AI voice configuration with actual API voices
Run this script when you have your MURF_API_KEY set up to get the real voice list
"""
import os
import asyncio
import aiohttp
import json
import re
from typing import List, Dict

async def fetch_murf_voices() -> List[Dict]:
    """Fetch available voices from Murf AI API"""
    api_key = os.getenv("MURF_API_KEY")
    if not api_key:
        print("❌ MURF_API_KEY environment variable not set")
        print("💡 Set your API key: export MURF_API_KEY=your_key_here")
        return []
    
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }
    
    voices_url = "https://api.murf.ai/v1/speech/voices"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(voices_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Successfully fetched Murf AI voices")
                    return data
                else:
                    error_text = await response.text()
                    print(f"❌ Error fetching voices: {response.status}")
                    print(f"Response: {error_text}")
                    return []
    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        return []

def update_config_file(voice_ids: List[str]):
    """Update config.py with the new voice IDs"""
    config_path = "config.py"
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Find and replace the supported_voices line for murf
        pattern = r'(supported_voices=\[)[^\]]+(\],)'
        replacement = f'\\1{voice_ids}\\2'
        
        # Look for the murf section specifically
        murf_section_pattern = r'("murf": TTSConfig\(.*?supported_voices=\[)[^\]]+(\],.*?\))'
        murf_replacement = f'\\1{voice_ids}\\2'
        
        if '"murf": TTSConfig(' in content:
            updated_content = re.sub(murf_section_pattern, murf_replacement, content, flags=re.DOTALL)
            
            with open(config_path, 'w') as f:
                f.write(updated_content)
            
            print(f"✅ Updated {config_path} with new voice IDs")
            return True
        else:
            print(f"❌ Could not find murf section in {config_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating config file: {str(e)}")
        return False

async def main():
    print("🎙️ Fetching Murf AI voices and updating configuration...")
    voices = await fetch_murf_voices()
    
    if voices:
        print(f"\n📋 Found {len(voices)} voices:")
        voice_ids = []
        
        for voice in voices:
            voice_id = voice.get('voiceId', 'Unknown')
            display_name = voice.get('displayName', 'Unknown')
            gender = voice.get('gender', 'Unknown')
            locale = voice.get('locale', 'Unknown')
            
            print(f"  - {voice_id} ({display_name}, {gender}, {locale})")
            voice_ids.append(voice_id)
        
        print(f"\n🔧 Voice IDs to use: {voice_ids}")
        
        # Update config.py
        if update_config_file(voice_ids):
            print("✅ Configuration updated successfully!")
        
        # Save full data for reference
        with open('murf_voices.json', 'w') as f:
            json.dump(voices, f, indent=2)
        print(f"💾 Full voice data saved to murf_voices.json")
        
    else:
        print("❌ No voices retrieved.")
        print("💡 Make sure your MURF_API_KEY is set and valid")
        print("💡 For now, using common voice IDs: en-US-sarah, en-US-david, en-US-ken, en-US-lisa")

if __name__ == "__main__":
    asyncio.run(main())
