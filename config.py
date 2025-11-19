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
    "murf_falcon_oct23": TTSConfig(
        name="Murf Falcon",
        api_key_env="MURF_API_KEY",
        base_url="https://global.api.murf.ai/v1/speech/stream",
        supported_voices=[
            "Alicia",      # Tamil (ta-IN)
            "Murali",      # Tamil (ta-IN)
            "Josie",       # Telugu (te-IN)
            "Ronnie",      # Telugu (te-IN)
            "Julia",       # Kannada (kn-IN)
            "Maverick",    # Kannada (kn-IN)
            "Rajesh"       # Kannada (kn-IN)
        ],
        max_chars=5000,  # Increased to support longer multilingual text
        supports_streaming=True,
        model_name="FALCON"
    ),
    "elevenlabs": TTSConfig(
        name="ElevenLabs Flash",
        api_key_env="ELEVENLABS_API_KEY",
        base_url="https://api.elevenlabs.io/v1/text-to-speech",
        supported_voices=["Rachel", "Domi", "Bella", "Antoni", "Elli", "Josh", "Arnold", "Adam", "Sam"],
        max_chars=5000,
        supports_streaming=True,
        model_name="eleven_flash_v2_5"
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
