# TTS Benchmarking Tool

Production-ready benchmarking tool for comparing Text-to-Speech (TTS) providers for Tamil, Telugu, and Kannada languages.

## Features

- **Multilingual Support**: Tamil (தமிழ்), Telugu (తెలుగు), Kannada (ಕನ್ನಡ), Hindi (हिंदी), and English
- **Provider Comparison**: Murf Falcon Oct 23 and ElevenLabs
- **7 Voices**: 
  - Tamil: Alicia, Murali
  - Telugu: Josie, Ronnie
  - Kannada: Julia, Maverick, Rajesh
- **ELO Rating System**: Chess-style rankings for objective provider comparison
- **Blind Testing**: Unbiased audio quality comparison
- **Leaderboard**: Track provider performance over time
- **Persistent Storage**: SQLite database for historical data
- **Security**: Input validation for multilingual text (supports Indian scripts) 
## Quick Start

### Prerequisites
- Python 3.9+
- API keys for TTS providers

### Installation

```bash
# Clone and navigate to directory
cd BenchMarking_Tool

# Install dependencies
pip install -r requirements.txt

# Configure API keys (copy and edit .env file)
cp env_example.txt .env
```

### Run Application

```bash
# Option 1: Using run.py
python run.py

# Option 2: Direct streamlit
streamlit run app.py
```

Access the app at: http://localhost:8501

## Configuration

Create a `.env` file with your API credentials:

```bash
# Required: Both provider API keys for full functionality
MURF_API_KEY=your_murf_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

**Note**: You need at least one API key to use the tool, but having both allows for proper blind testing comparison.

## Core Components

```
├── app.py                 # Main Streamlit application
├── config.py             # Configuration and settings
├── tts_providers.py      # TTS provider implementations
├── benchmarking_engine.py # Core benchmarking logic
├── database.py           # SQLite database management
├── dataset.py            # Test dataset generation
├── visualizations.py     # Chart and graph generation
├── export_utils.py       # Export functionality
├── security.py           # Security and rate limiting
├── geolocation.py        # Location tracking
└── requirements.txt      # Python dependencies
```

## Usage

The application has two main screens:

### 1. Blind Test
1. Enter text in any supported language (Tamil, Telugu, Kannada, Hindi, or English)
2. Use the sample texts provided for quick testing
3. Click "Generate Blind Test"
4. Listen to randomized audio samples (labeled A, B, etc.)
5. Vote for your favorite audio quality
6. Providers are revealed after voting
7. ELO ratings automatically updated

**Features:**
- Unbiased comparison (provider names hidden during voting)
- Support for multilingual text input
- Sample texts in all 5 languages
- Character counter (up to 5000 characters)
- Download MP3 files after results

### 2. Leaderboard
- View ELO-based rankings of TTS providers
- See provider statistics (success rate, avg TTFB, P95 TTFB)
- Track voting history and user preferences
- Location-based metrics
- Historical performance data

**Supported Languages:**
- Tamil (தமிழ்): Voices - Alicia, Murali
- Telugu (తెలుగు): Voices - Josie, Ronnie  
- Kannada (ಕನ್ನಡ): Voices - Julia, Maverick, Rajesh
- Hindi (हिंदी): All voices support
- English: All voices support

## Deployment

### Docker
```bash
docker build -t tts-benchmark .
docker run -p 8501:8501 --env-file .env tts-benchmark
```

### Heroku / Cloud Platform
1. Push code to platform
2. Set environment variables for API keys
3. Deploy and access via provided URL

## Security

- Environment-based API key configuration
- Multilingual input validation (supports Devanagari, Tamil, Telugu, Kannada scripts)
- Rate limiting (60 requests/minute per session)
- Character limit: 5000 characters per request
- Secure session management
- No permanent audio storage
- XSS and injection attack prevention

## Database

- SQLite database (`benchmark_data.db`) stores:
  - Benchmark results with geolocation
  - ELO ratings and game history
  - Provider statistics
  - User voting data

## Performance

- Async processing for concurrent requests
- Rate limiting to prevent API abuse
- Database caching for historical data
- Optimized for production workloads

## License

MIT License - see LICENSE file for details