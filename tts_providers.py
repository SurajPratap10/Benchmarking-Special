"""
TTS Provider implementations for benchmarking
"""
import time
import asyncio
import aiohttp
import requests
import ssl
from typing import Dict, Any, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass
from abc import ABC, abstractmethod
import io
import json
from config import get_api_key, TTS_PROVIDERS

@dataclass
class TTSResult:
    """Result from TTS generation"""
    success: bool
    audio_data: Optional[bytes]
    latency_ms: float
    file_size_bytes: int
    error_message: Optional[str]
    metadata: Dict[str, Any]
    latency_1: float = 0.0  # Network latency (pure RTT) without TTS processing

@dataclass
class TTSRequest:
    """TTS generation request"""
    text: str
    voice: str
    provider: str
    model: Optional[str] = None
    speed: float = 1.0
    format: str = "mp3"

class TTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        self.config = TTS_PROVIDERS[provider_id]
        self.api_key = get_api_key(provider_id)
    
    @abstractmethod
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech from text"""
        pass
    
    @abstractmethod
    def get_available_voices(self) -> list:
        """Get list of available voices"""
        pass
    
    def validate_request(self, request: TTSRequest) -> Tuple[bool, str]:
        """Validate TTS request"""
        if len(request.text) > self.config.max_chars:
            return False, f"Text exceeds maximum length of {self.config.max_chars} characters"
        
        if request.voice not in self.config.supported_voices:
            return False, f"Voice '{request.voice}' not supported. Available: {self.config.supported_voices}"
        
        return True, ""
    
    async def measure_ping_latency(self) -> float:
        """Measure pure network latency (RTT) without TTS processing"""
        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                # Send a minimal HEAD or OPTIONS request to measure pure network latency
                async with session.head(
                    self.config.base_url,
                    headers={"api-key": self.api_key} if "murf" in self.provider_id else {"Authorization": f"Token {self.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    return latency_ms
        except:
            # If HEAD doesn't work, fallback to minimal GET/POST
            try:
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        self.config.base_url.replace("/v1/speech/", "/").replace("turbo-stream", "").replace("stream", "").rstrip("/"),
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        latency_ms = (time.time() - start_time) * 1000
                        return latency_ms
            except:
                return 0.0  # Return 0 if ping fails

class MurfAITTSProvider(TTSProvider):
    """Murf AI TTS provider implementation"""
    
    def __init__(self):
        super().__init__("murf")
    
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech using Murf AI API"""
        start_time = time.time()
        
        # Validate request
        is_valid, error_msg = self.validate_request(request)
        if not is_valid:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=0,
                file_size_bytes=0,
                error_message=error_msg,
                metadata={}
            )
        
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Murf AI API payload structure
        payload = {
            "text": request.text,
            "voiceId": request.voice,
            "audioFormat": request.format or "mp3"
        }
        
        # Add speed/rate if specified
        if request.speed and request.speed != 1.0:
            payload["rate"] = request.speed
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.base_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    end_time = time.time()
                    latency_ms = (end_time - start_time) * 1000
                    
                    if response.status == 200:
                        # Check content type to determine response format
                        content_type = response.headers.get('content-type', '').lower()
                        
                        if 'application/json' in content_type:
                            # JSON response - might contain audio URL or data
                            response_data = await response.json()
                            
                            if "audioFile" in response_data:
                                # Murf AI returns audio URL in audioFile field
                                audio_url = response_data["audioFile"]
                                async with session.get(audio_url) as audio_response:
                                    if audio_response.status == 200:
                                        audio_data = await audio_response.read()
                                        return TTSResult(
                                            success=True,
                                            audio_data=audio_data,
                                            latency_ms=latency_ms,
                                            file_size_bytes=len(audio_data),
                                            error_message=None,
                                            metadata={
                                                "voice": request.voice,
                                                "speed": request.speed,
                                                "format": request.format,
                                                "provider": self.provider_id,
                                                "audio_url": audio_url
                                            }
                                        )
                                    else:
                                        return TTSResult(
                                            success=False,
                                            audio_data=None,
                                            latency_ms=latency_ms,
                                            file_size_bytes=0,
                                            error_message=f"Failed to download audio from URL: {audio_response.status}",
                                            metadata={"provider": self.provider_id}
                                        )
                            elif "audio" in response_data:
                                # Base64 encoded audio data
                                import base64
                                audio_data = base64.b64decode(response_data["audio"])
                                return TTSResult(
                                    success=True,
                                    audio_data=audio_data,
                                    latency_ms=latency_ms,
                                    file_size_bytes=len(audio_data),
                                    error_message=None,
                                    metadata={
                                        "voice": request.voice,
                                        "speed": request.speed,
                                        "format": request.format,
                                        "provider": self.provider_id
                                    }
                                )
                            else:
                                return TTSResult(
                                    success=False,
                                    audio_data=None,
                                    latency_ms=latency_ms,
                                    file_size_bytes=0,
                                    error_message=f"Unexpected JSON response format: {list(response_data.keys())}",
                                    metadata={"provider": self.provider_id, "response": response_data}
                                )
                        else:
                            # Direct audio data response
                            audio_data = await response.read()
                            return TTSResult(
                                success=True,
                                audio_data=audio_data,
                                latency_ms=latency_ms,
                                file_size_bytes=len(audio_data),
                                error_message=None,
                                metadata={
                                    "voice": request.voice,
                                    "speed": request.speed,
                                    "format": request.format,
                                    "provider": self.provider_id,
                                    "content_type": content_type
                                }
                            )
                    else:
                        error_text = await response.text()
                        return TTSResult(
                            success=False,
                            audio_data=None,
                            latency_ms=latency_ms,
                            file_size_bytes=0,
                            error_message=f"API Error {response.status}: {error_text}",
                            metadata={"provider": self.provider_id}
                        )
        
        except asyncio.TimeoutError:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message="Request timeout",
                metadata={"provider": self.provider_id}
            )
        except Exception as e:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message=f"Error: {str(e)}",
                metadata={"provider": self.provider_id}
            )
    
    def get_available_voices(self) -> list:
        """Get available Murf AI voices"""
        return self.config.supported_voices

class MurfFalconTTSProvider(TTSProvider):
    """Murf Falcon TTS provider implementation (Turbo Stream)"""
    
    def __init__(self):
        super().__init__("murf_falcon")
    
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech using Murf Falcon API (Turbo Stream)"""
        start_time = time.time()
        
        # Validate request
        is_valid, error_msg = self.validate_request(request)
        if not is_valid:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=0,
                file_size_bytes=0,
                error_message=error_msg,
                metadata={}
            )
        
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Murf Falcon API payload structure
        payload = {
            "text": request.text,
            "voiceId": request.voice,
            "audioFormat": request.format or "mp3"
        }
        
        # Add speed/rate if specified
        if request.speed and request.speed != 1.0:
            payload["rate"] = request.speed
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.base_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    end_time = time.time()
                    latency_ms = (end_time - start_time) * 1000
                    
                    if response.status == 200:
                        # Check content type to determine response format
                        content_type = response.headers.get('content-type', '').lower()
                        
                        if 'application/json' in content_type:
                            # JSON response - might contain audio URL or data
                            response_data = await response.json()
                            
                            if "audioFile" in response_data:
                                # Murf Falcon returns audio URL in audioFile field
                                audio_url = response_data["audioFile"]
                                async with session.get(audio_url) as audio_response:
                                    if audio_response.status == 200:
                                        audio_data = await audio_response.read()
                                        return TTSResult(
                                            success=True,
                                            audio_data=audio_data,
                                            latency_ms=latency_ms,
                                            file_size_bytes=len(audio_data),
                                            error_message=None,
                                            metadata={
                                                "voice": request.voice,
                                                "speed": request.speed,
                                                "format": request.format,
                                                "provider": self.provider_id,
                                                "model": "falcon-turbo",
                                                "audio_url": audio_url
                                            }
                                        )
                                    else:
                                        return TTSResult(
                                            success=False,
                                            audio_data=None,
                                            latency_ms=latency_ms,
                                            file_size_bytes=0,
                                            error_message=f"Failed to download audio from URL: {audio_response.status}",
                                            metadata={"provider": self.provider_id}
                                        )
                            elif "audio" in response_data:
                                # Base64 encoded audio data
                                import base64
                                audio_data = base64.b64decode(response_data["audio"])
                                return TTSResult(
                                    success=True,
                                    audio_data=audio_data,
                                    latency_ms=latency_ms,
                                    file_size_bytes=len(audio_data),
                                    error_message=None,
                                    metadata={
                                        "voice": request.voice,
                                        "speed": request.speed,
                                        "format": request.format,
                                        "provider": self.provider_id,
                                        "model": "falcon-turbo"
                                    }
                                )
                            else:
                                return TTSResult(
                                    success=False,
                                    audio_data=None,
                                    latency_ms=latency_ms,
                                    file_size_bytes=0,
                                    error_message=f"Unexpected JSON response format: {list(response_data.keys())}",
                                    metadata={"provider": self.provider_id, "response": response_data}
                                )
                        else:
                            # Direct audio data response (streaming)
                            audio_data = await response.read()
                            return TTSResult(
                                success=True,
                                audio_data=audio_data,
                                latency_ms=latency_ms,
                                file_size_bytes=len(audio_data),
                                error_message=None,
                                metadata={
                                    "voice": request.voice,
                                    "speed": request.speed,
                                    "format": request.format,
                                    "provider": self.provider_id,
                                    "model": "falcon-turbo",
                                    "content_type": content_type
                                }
                            )
                    else:
                        error_text = await response.text()
                        return TTSResult(
                            success=False,
                            audio_data=None,
                            latency_ms=latency_ms,
                            file_size_bytes=0,
                            error_message=f"API Error {response.status}: {error_text}",
                            metadata={"provider": self.provider_id}
                        )
        
        except asyncio.TimeoutError:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message="Request timeout",
                metadata={"provider": self.provider_id}
            )
        except Exception as e:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message=f"Error: {str(e)}",
                metadata={"provider": self.provider_id}
            )
    
    def get_available_voices(self) -> list:
        """Get available Murf Falcon voices"""
        return self.config.supported_voices

class MurfFalconOct13TTSProvider(TTSProvider):
    """Murf Falcon Oct 13 TTS provider implementation (New Stream Endpoint)"""
    
    def __init__(self):
        super().__init__("murf_falcon_oct13")
    
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech using Murf Falcon Oct 13 API (Stream)"""
        start_time = time.time()
        
        # Validate request
        is_valid, error_msg = self.validate_request(request)
        if not is_valid:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=0,
                file_size_bytes=0,
                error_message=error_msg,
                metadata={}
            )
        
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Murf Falcon Oct 13 API payload structure
        payload = {
            "text": request.text,
            "voiceId": request.voice,
            "audioFormat": request.format or "mp3",
            "model": "FALCON"
        }
        
        # Add speed/rate if specified
        if request.speed and request.speed != 1.0:
            payload["rate"] = request.speed
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.base_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        audio_data = await response.read()
                        file_size = len(audio_data)
                        
                        return TTSResult(
                            success=True,
                            audio_data=audio_data,
                            latency_ms=latency_ms,
                            file_size_bytes=file_size,
                            error_message=None,
                            metadata={
                                "provider": self.provider_id,
                                "model": "FALCON",
                                "voice": request.voice,
                                "format": request.format or "mp3"
                            }
                        )
                    else:
                        error_text = await response.text()
                        return TTSResult(
                            success=False,
                            audio_data=None,
                            latency_ms=latency_ms,
                            file_size_bytes=0,
                            error_message=f"API Error {response.status}: {error_text}",
                            metadata={"provider": self.provider_id}
                        )
        
        except asyncio.TimeoutError:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message="Request timeout",
                metadata={"provider": self.provider_id}
            )
        except Exception as e:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message=f"Error: {str(e)}",
                metadata={"provider": self.provider_id}
            )
    
    def get_available_voices(self) -> list:
        """Get available Murf Falcon Oct 13 voices"""
        return self.config.supported_voices

class MurfFalconOct23TTSProvider(TTSProvider):
    """Murf Falcon Oct 23 TTS provider implementation (Global Stream Endpoint)"""
    
    def __init__(self):
        super().__init__("murf_falcon_oct23")
    
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech using Murf Falcon Oct 23 API (Global Stream)"""
        start_time = time.time()
        
        # Validate request
        is_valid, error_msg = self.validate_request(request)
        if not is_valid:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=0,
                file_size_bytes=0,
                error_message=error_msg,
                metadata={}
            )
        
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Murf Falcon Oct 23 API payload structure
        payload = {
            "text": request.text,
            "voiceId": request.voice,
            "audioFormat": request.format or "mp3",
            "model": "FALCON"
        }
        
        # Add speed/rate if specified
        if request.speed and request.speed != 1.0:
            payload["rate"] = request.speed
        
        try:
            # Create SSL context that doesn't verify certificates (for global endpoint)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    self.config.base_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        audio_data = await response.read()
                        file_size = len(audio_data)
                        
                        return TTSResult(
                            success=True,
                            audio_data=audio_data,
                            latency_ms=latency_ms,
                            file_size_bytes=file_size,
                            error_message=None,
                            metadata={
                                "provider": self.provider_id,
                                "model": "FALCON",
                                "voice": request.voice,
                                "format": request.format or "mp3"
                            }
                        )
                    else:
                        error_text = await response.text()
                        return TTSResult(
                            success=False,
                            audio_data=None,
                            latency_ms=latency_ms,
                            file_size_bytes=0,
                            error_message=f"API Error {response.status}: {error_text}",
                            metadata={"provider": self.provider_id}
                        )
        
        except asyncio.TimeoutError:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message="Request timeout",
                metadata={"provider": self.provider_id}
            )
        except Exception as e:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message=f"Error: {str(e)}",
                metadata={"provider": self.provider_id}
            )
    
    def get_available_voices(self) -> list:
        """Get available Murf Falcon Oct 23 voices"""
        return self.config.supported_voices

class DeepgramTTSProvider(TTSProvider):
    """Deepgram Aura 1 TTS provider implementation"""
    
    def __init__(self):
        super().__init__("deepgram")
    
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech using Deepgram TTS API"""
        start_time = time.time()
        
        # Validate request
        is_valid, error_msg = self.validate_request(request)
        if not is_valid:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=0,
                file_size_bytes=0,
                error_message=error_msg,
                metadata={}
            )
        
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Deepgram TTS API payload structure
        payload = {
            "text": request.text
        }
        
        # Add query parameters to URL
        params = {
            "model": request.voice,
            "encoding": "mp3" if request.format == "mp3" else "linear16"
        }
        
        # Only add sample_rate for non-MP3 formats
        if request.format != "mp3":
            params["sample_rate"] = "24000"
        
        # Build URL with parameters
        url_with_params = f"{self.config.base_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url_with_params,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    end_time = time.time()
                    latency_ms = (end_time - start_time) * 1000
                    
                    if response.status == 200:
                        # Deepgram returns audio data directly
                        audio_data = await response.read()
                        return TTSResult(
                            success=True,
                            audio_data=audio_data,
                            latency_ms=latency_ms,
                            file_size_bytes=len(audio_data),
                            error_message=None,
                            metadata={
                                "voice": request.voice,
                                "speed": request.speed,
                                "format": request.format,
                                "provider": self.provider_id,
                                "model": request.voice,
                                "sample_rate": 24000
                            }
                        )
                    else:
                        error_text = await response.text()
                        return TTSResult(
                            success=False,
                            audio_data=None,
                            latency_ms=latency_ms,
                            file_size_bytes=0,
                            error_message=f"API Error {response.status}: {error_text}",
                            metadata={"provider": self.provider_id}
                        )
        
        except asyncio.TimeoutError:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message="Request timeout",
                metadata={"provider": self.provider_id}
            )
        except Exception as e:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message=f"Error: {str(e)}",
                metadata={"provider": self.provider_id}
            )
    
    def get_available_voices(self) -> list:
        """Get available Deepgram voices"""
        return self.config.supported_voices

class DeepgramAura2TTSProvider(TTSProvider):
    """Deepgram Aura 2 TTS provider implementation"""
    
    def __init__(self):
        super().__init__("deepgram_aura2")
    
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech using Deepgram Aura 2 TTS API"""
        start_time = time.time()
        
        # Validate request
        is_valid, error_msg = self.validate_request(request)
        if not is_valid:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=0,
                file_size_bytes=0,
                error_message=error_msg,
                metadata={}
            )
        
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Deepgram Aura 2 TTS API payload structure
        payload = {
            "text": request.text
        }
        
        # Add query parameters to URL
        params = {
            "model": request.voice,
            "encoding": "mp3" if request.format == "mp3" else "linear16"
        }
        
        # Only add sample_rate for non-MP3 formats
        if request.format != "mp3":
            params["sample_rate"] = "24000"
        
        # Build URL with parameters
        url_with_params = f"{self.config.base_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url_with_params,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    end_time = time.time()
                    latency_ms = (end_time - start_time) * 1000
                    
                    if response.status == 200:
                        # Deepgram returns audio data directly
                        audio_data = await response.read()
                        return TTSResult(
                            success=True,
                            audio_data=audio_data,
                            latency_ms=latency_ms,
                            file_size_bytes=len(audio_data),
                            error_message=None,
                            metadata={
                                "voice": request.voice,
                                "speed": request.speed,
                                "format": request.format,
                                "provider": self.provider_id,
                                "model": request.voice,
                                "sample_rate": 24000
                            }
                        )
                    else:
                        error_text = await response.text()
                        return TTSResult(
                            success=False,
                            audio_data=None,
                            latency_ms=latency_ms,
                            file_size_bytes=0,
                            error_message=f"API Error {response.status}: {error_text}",
                            metadata={"provider": self.provider_id}
                        )
        
        except asyncio.TimeoutError:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message="Request timeout",
                metadata={"provider": self.provider_id}
            )
        except Exception as e:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message=f"Error: {str(e)}",
                metadata={"provider": self.provider_id}
            )
    
    def get_available_voices(self) -> list:
        """Get available Deepgram Aura 2 voices"""
        return self.config.supported_voices

class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs TTS provider implementation"""
    
    def __init__(self):
        super().__init__("elevenlabs")
        # Map friendly voice names to voice IDs
        self.voice_id_map = {
            "Rachel": "21m00Tcm4TlvDq8ikWAM",
            "Domi": "AZnzlk1XvdvUeBnXmlld",
            "Bella": "EXAVITQu4vr4xnSDxMaL",
            "Antoni": "ErXwobaYiN019PkySvjV",
            "Elli": "MF3mGyEYCl7XYWbV9V6O",
            "Josh": "TxGEqnHWrfWFTfGW9XjX",
            "Arnold": "VR6AewLTigWG4xSOukaG",
            "Adam": "pNInz6obpgDQGcFmaJgB",
            "Sam": "yoZ06aMxZJJ28mfd3POQ"
        }
    
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech using ElevenLabs TTS API"""
        start_time = time.time()
        
        # Validate request
        is_valid, error_msg = self.validate_request(request)
        if not is_valid:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=0,
                file_size_bytes=0,
                error_message=error_msg,
                metadata={}
            )
        
        # Get voice ID from friendly name
        voice_id = self.voice_id_map.get(request.voice, request.voice)
        
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # ElevenLabs API payload structure
        payload = {
            "text": request.text,
            "model_id": "eleven_flash_v2_5",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        # Build URL with voice ID
        url = f"{self.config.base_url}/{voice_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    end_time = time.time()
                    latency_ms = (end_time - start_time) * 1000
                    
                    if response.status == 200:
                        # ElevenLabs returns audio data directly
                        audio_data = await response.read()
                        return TTSResult(
                            success=True,
                            audio_data=audio_data,
                            latency_ms=latency_ms,
                            file_size_bytes=len(audio_data),
                            error_message=None,
                            metadata={
                                "voice": request.voice,
                                "voice_id": voice_id,
                                "model": "eleven_flash_v2_5",
                                "provider": self.provider_id,
                                "format": "mp3_44100_128"
                            }
                        )
                    else:
                        error_text = await response.text()
                        return TTSResult(
                            success=False,
                            audio_data=None,
                            latency_ms=latency_ms,
                            file_size_bytes=0,
                            error_message=f"API Error {response.status}: {error_text}",
                            metadata={"provider": self.provider_id}
                        )
        
        except asyncio.TimeoutError:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message="Request timeout",
                metadata={"provider": self.provider_id}
            )
        except Exception as e:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message=f"Error: {str(e)}",
                metadata={"provider": self.provider_id}
            )
    
    def get_available_voices(self) -> list:
        """Get available ElevenLabs voices"""
        return self.config.supported_voices

class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS provider implementation"""
    
    def __init__(self):
        super().__init__("openai")
    
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech using OpenAI TTS API"""
        start_time = time.time()
        
        # Validate request
        is_valid, error_msg = self.validate_request(request)
        if not is_valid:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=0,
                file_size_bytes=0,
                error_message=error_msg,
                metadata={}
            )
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # OpenAI TTS API payload structure
        payload = {
            "model": "gpt-4o-mini-tts",  # GPT-4o Mini TTS model
            "input": request.text,
            "voice": request.voice.lower(),  # alloy, echo, fable, onyx, nova, shimmer
            "response_format": "mp3",
            "speed": request.speed if request.speed else 1.0
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.base_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    end_time = time.time()
                    latency_ms = (end_time - start_time) * 1000
                    
                    if response.status == 200:
                        # OpenAI returns audio data directly
                        audio_data = await response.read()
                        return TTSResult(
                            success=True,
                            audio_data=audio_data,
                            latency_ms=latency_ms,
                            file_size_bytes=len(audio_data),
                            error_message=None,
                            metadata={
                                "voice": request.voice,
                                "model": "tts-1-hd",
                                "provider": self.provider_id,
                                "format": "mp3",
                                "speed": payload["speed"]
                            }
                        )
                    else:
                        error_text = await response.text()
                        return TTSResult(
                            success=False,
                            audio_data=None,
                            latency_ms=latency_ms,
                            file_size_bytes=0,
                            error_message=f"API Error {response.status}: {error_text}",
                            metadata={"provider": self.provider_id}
                        )
        
        except asyncio.TimeoutError:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message="Request timeout",
                metadata={"provider": self.provider_id}
            )
        except Exception as e:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message=f"Error: {str(e)}",
                metadata={"provider": self.provider_id}
            )
    
    def get_available_voices(self) -> list:
        """Get available OpenAI voices"""
        return self.config.supported_voices

class CartesiaTTSProvider(TTSProvider):
    """Base class for Cartesia TTS providers"""
    
    def __init__(self, provider_id: str, model_id: str):
        super().__init__(provider_id)
        self.model_id = model_id
        # Map friendly voice names to Cartesia voice IDs
        self.voice_id_map = {
            "British Lady": "79a125e8-cd45-4c13-8a67-188112f4dd22",
            "Conversational Lady": "a0e99841-438c-4a64-b679-ae501e7d6091",
            "Classy British Man": "63ff761f-c1e8-414b-b969-d1833d1c870c",
            "Friendly Reading Man": "5619d38c-cf51-4d8e-9575-48f61a280413",
            "Midwestern Woman": "a3520a8f-226a-428d-9fcd-b0a4711a6829",
            "Professional Man": "41534e16-2966-4c6b-9670-111411def906",
            "Newsman": "daf747c6-6bc2-45c9-b3e6-d99d48c6697e"
        }
    
    async def generate_speech(self, request: TTSRequest) -> TTSResult:
        """Generate speech using Cartesia TTS API"""
        start_time = time.time()
        
        # Validate request
        is_valid, error_msg = self.validate_request(request)
        if not is_valid:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=0,
                file_size_bytes=0,
                error_message=error_msg,
                metadata={}
            )
        
        # Get voice ID from friendly name
        voice_id = self.voice_id_map.get(request.voice, self.voice_id_map["Conversational Lady"])
        
        headers = {
            "X-API-Key": self.api_key,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json"
        }
        
        # Cartesia API payload structure
        payload = {
            "model_id": self.model_id,
            "transcript": request.text,
            "voice": {
                "mode": "id",
                "id": voice_id
            },
            "language": "en",
            "output_format": {
                "container": "mp3",
                "encoding": "mp3",
                "sample_rate": 44100
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.base_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    end_time = time.time()
                    latency_ms = (end_time - start_time) * 1000
                    
                    if response.status == 200:
                        # Cartesia returns audio data directly
                        audio_data = await response.read()
                        return TTSResult(
                            success=True,
                            audio_data=audio_data,
                            latency_ms=latency_ms,
                            file_size_bytes=len(audio_data),
                            error_message=None,
                            metadata={
                                "voice": request.voice,
                                "voice_id": voice_id,
                                "model": self.model_id,
                                "provider": self.provider_id,
                                "format": "mp3",
                                "sample_rate": 44100
                            }
                        )
                    else:
                        error_text = await response.text()
                        return TTSResult(
                            success=False,
                            audio_data=None,
                            latency_ms=latency_ms,
                            file_size_bytes=0,
                            error_message=f"API Error {response.status}: {error_text}",
                            metadata={"provider": self.provider_id}
                        )
        
        except asyncio.TimeoutError:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message="Request timeout",
                metadata={"provider": self.provider_id}
            )
        except Exception as e:
            return TTSResult(
                success=False,
                audio_data=None,
                latency_ms=(time.time() - start_time) * 1000,
                file_size_bytes=0,
                error_message=f"Error: {str(e)}",
                metadata={"provider": self.provider_id}
            )
    
    def get_available_voices(self) -> list:
        """Get available Cartesia voices"""
        return self.config.supported_voices

class CartesiaSonic2Provider(CartesiaTTSProvider):
    """Cartesia Sonic 2.0 TTS provider"""
    
    def __init__(self):
        super().__init__("cartesia_sonic2", "sonic-2")

class CartesiaTurboProvider(CartesiaTTSProvider):
    """Cartesia Sonic Turbo TTS provider"""
    
    def __init__(self):
        super().__init__("cartesia_turbo", "sonic-turbo")

class TTSProviderFactory:
    """Factory for creating TTS providers"""
    
    @staticmethod
    def create_provider(provider_id: str) -> TTSProvider:
        """Create a TTS provider instance"""
        if provider_id == "murf":
            return MurfAITTSProvider()
        elif provider_id == "murf_falcon":
            return MurfFalconTTSProvider()
        elif provider_id == "murf_falcon_oct13":
            return MurfFalconOct13TTSProvider()
        elif provider_id == "murf_falcon_oct23":
            return MurfFalconOct23TTSProvider()
        elif provider_id == "deepgram":
            return DeepgramTTSProvider()
        elif provider_id == "deepgram_aura2":
            return DeepgramAura2TTSProvider()
        elif provider_id == "elevenlabs":
            return ElevenLabsTTSProvider()
        elif provider_id == "openai":
            return OpenAITTSProvider()
        elif provider_id == "cartesia_sonic2":
            return CartesiaSonic2Provider()
        elif provider_id == "cartesia_turbo":
            return CartesiaTurboProvider()
        else:
            raise ValueError(f"Unknown provider: {provider_id}")
    
    @staticmethod
    def get_available_providers() -> list:
        """Get list of available provider IDs"""
        return list(TTS_PROVIDERS.keys())
    
    @staticmethod
    def create_all_providers() -> Dict[str, TTSProvider]:
        """Create instances of all available providers"""
        providers = {}
        for provider_id in TTSProviderFactory.get_available_providers():
            try:
                providers[provider_id] = TTSProviderFactory.create_provider(provider_id)
            except Exception as e:
                print(f"Failed to create provider {provider_id}: {e}")
        return providers
