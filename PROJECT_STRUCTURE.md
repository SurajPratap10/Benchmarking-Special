# TTS Benchmarking Tool - Project Structure

## Core Application Files

### Main Application
- `app.py` - Main Streamlit application (Blind Test & Leaderboard)
- `run.py` - Application launcher script
- `config.py` - Configuration for TTS providers and settings
- `tts_providers.py` - TTS provider implementations (Murf Falcon & ElevenLabs)

### Supporting Modules
- `benchmarking_engine.py` - Benchmark execution engine
- `database.py` - Database management for results
- `dataset.py` - Test sample datasets
- `security.py` - Input validation and security
- `export_utils.py` - Data export utilities
- `visualizations.py` - Charts and visualizations
- `geolocation.py` - Location detection

### Data & Assets
- `benchmark_data.db` - SQLite database with test results
- `styles.css` - Custom styling
- `.env.example` - API key template (copy to .env and add your keys)

## Documentation
- `README.md` - Main documentation
- `SETUP_GUIDE.md` - Quick start guide

## Deployment
- `requirements.txt` - Python dependencies
- `Dockerfile` - Docker containerization
- `start.sh` - Shell script for deployment

## Environment
- `venv/` - Python virtual environment

---

## Quick Start

1. **Setup API Keys:**
   ```bash
   cp .env.example .env
   nano .env  # Add your API keys
   ```

2. **Run Application:**
   ```bash
   python run.py
   ```

3. **Access:**
   - Open browser to http://localhost:8501
   - Use "Blind Test" to compare TTS quality
   - View "Leaderboard" for rankings

---

## Supported Languages
- Tamil (தமிழ்) - Murf voices: Alicia, Murali
- Telugu (తెలుగు) - Murf voices: Josie, Ronnie
- Kannada (ಕನ್ನಡ) - Murf voices: Julia, Maverick, Rajesh
- English - Both Murf and ElevenLabs
- Hindi (हिंदी) - Murf voices

---

## TTS Providers
1. **Murf Falcon** - Supports all 5 languages with native voices
2. **ElevenLabs Flash** - Primarily English, can attempt other languages

---

*Last updated: November 2025*

