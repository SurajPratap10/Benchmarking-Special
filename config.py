"""
Configuration settings for the TTS Benchmarking Tool
"""
import os
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class TTSConfig:
    """Configuration for TTS providers"""
    name: str
    api_key_env: str
    base_url: str
    supported_voices: List[str]
    max_chars: int
    supports_streaming: bool
    model_name: str = ""  # Full model name for display

# TTS Provider Configurations
TTS_PROVIDERS = {
    "murf": TTSConfig(
        name="Murf AI",
        api_key_env="MURF_API_KEY", 
        base_url="https://api.murf.ai/v1/speech/generate",
        supported_voices=["en-US-natalie", "en-US-miles", "en-US-amara", "en-US-maverick", "en-US-ken", "en-US-terrell"],
        max_chars=3000,
        supports_streaming=False,
        model_name="Murf AI TTS v1"
    ),
    "deepgram": TTSConfig(
        name="Deepgram",
        api_key_env="DEEPGRAM_API_KEY",
        base_url="https://api.deepgram.com/v1/speak",
        supported_voices=["aura-asteria-en", "aura-luna-en", "aura-stella-en", "aura-athena-en", "aura-hera-en", "aura-orion-en"],
        max_chars=2000,
        supports_streaming=True,
        model_name="Deepgram Aura (v1 API)"
    ),
    "elevenlabs": TTSConfig(
        name="ElevenLabs",
        api_key_env="ELEVENLABS_API_KEY",
        base_url="https://api.elevenlabs.io/v1/text-to-speech",
        supported_voices=["Rachel", "Domi", "Bella", "Antoni", "Elli", "Josh", "Arnold", "Adam", "Sam"],
        max_chars=5000,
        supports_streaming=True,
        model_name="ElevenLabs Multilingual v2"
    ),
    "openai": TTSConfig(
        name="OpenAI",
        api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1/audio/speech",
        supported_voices=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        max_chars=4096,
        supports_streaming=True,
        model_name="OpenAI TTS HD (tts-1-hd)"
    )
}

# Benchmarking Configuration
BENCHMARK_CONFIG = {
    "default_iterations": 3,
    "timeout_seconds": 30,
    "quality_metrics": ["duration", "file_size", "sample_rate"],
    "latency_percentiles": [50, 90, 95, 99],
    "elo_k_factor": 32,
    "initial_elo_rating": 1500
}

# Test Dataset Configuration  
DATASET_CONFIG = {
    "sentence_lengths": {
        "short": (10, 30),    # 10-30 words
        "medium": (31, 80),   # 31-80 words  
        "long": (81, 150),    # 81-150 words
        "very_long": (151, 200) # 151-200 words
    },
    "categories": ["news", "literature", "conversation", "technical", "narrative"],
    "total_samples": 100
}

# UI Configuration
UI_CONFIG = {
    "page_title": "TTS Benchmarking Tool",
    "page_icon": None,
    "layout": "wide",
    "sidebar_width": 300,
    "chart_height": 400,
    "max_file_size_mb": 10
}

def get_api_key(provider: str) -> str:
    """Get API key for a provider from environment variables"""
    if provider not in TTS_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    
    env_var = TTS_PROVIDERS[provider].api_key_env
    api_key = os.getenv(env_var)
    
    if not api_key:
        raise ValueError(f"API key not found for {provider}. Please set {env_var} environment variable.")
    
    return api_key

def validate_config() -> Dict[str, Any]:
    """Validate configuration and return status"""
    status = {
        "providers": {},
        "valid": False,
        "errors": [],
        "configured_count": 0
    }
    
    for provider_id, config in TTS_PROVIDERS.items():
        try:
            api_key = get_api_key(provider_id)
            status["providers"][provider_id] = {
                "configured": True,
                "api_key_length": len(api_key) if api_key else 0
            }
            status["configured_count"] += 1
        except ValueError as e:
            status["providers"][provider_id] = {
                "configured": False,
                "error": str(e)
            }
            status["errors"].append(str(e))
    
    # Consider valid if at least one provider is configured
    status["valid"] = status["configured_count"] > 0
    
    return status
