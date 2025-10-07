# TTS Benchmarking Tool

Production-ready benchmarking tool for comparing Text-to-Speech (TTS) providers with comprehensive metrics and analysis.

## Features

- **Multi-Provider Support**: OpenAI, Murf AI, Deepgram, ElevenLabs, Cartesia
- **Comprehensive Metrics**: Latency, success rates, file sizes, quality analysis
- **ELO Rating System**: Chess-style rankings for objective provider comparison
- **Interactive Visualizations**: Real-time charts and analytics
- **Blind Testing**: Unbiased audio quality comparison
- **Batch Testing**: Comprehensive benchmarks across diverse datasets
- **Persistent Storage**: SQLite database for historical data
- **Export Options**: JSON, CSV, Excel, and comprehensive report packages

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
# Required: At least one provider API key
OPENAI_API_KEY=your_openai_api_key_here
MURF_API_KEY=your_murf_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
CARTESIA_API_KEY=your_cartesia_api_key_here
```

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

### Quick Test
1. Enter text prompt
2. Select providers and voices
3. Click "Generate & Compare"
4. View side-by-side results with audio playback

### Blind Test
1. Generate audio from all configured providers
2. Listen to randomized samples (labeled A, B, C, etc.)
3. Vote for your favorite
4. Providers revealed after voting

### Batch Benchmark
1. Configure test parameters (samples, categories, lengths)
2. Prepare test dataset
3. Run comprehensive benchmark
4. Analyze detailed results and export data

### Results Analysis
- Filter by provider, category, or success status
- View latency distributions and performance metrics
- Analyze error patterns
- Export results in multiple formats

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
- Input validation and sanitization
- Rate limiting (60 requests/minute per session)
- Secure session management
- No permanent audio storage

## Database

- SQLite database (`benchmark_data.db`) stores:
  - Benchmark results with geolocation
  - ELO ratings and game history
  - Provider statistics
  - User voting data

## Export Formats

- **JSON**: Raw results with metadata
- **CSV**: Flattened results for analysis
- **Excel**: Multi-sheet workbook with summaries
- **Comprehensive Report**: Full analysis with comparisons
- **ZIP Package**: All formats bundled together

## Performance

- Async processing for concurrent requests
- Rate limiting to prevent API abuse
- Database caching for historical data
- Optimized for production workloads

## License

MIT License - see LICENSE file for details

## Support

For issues or questions, please open a GitHub issue.

---

**Built for production TTS benchmarking**