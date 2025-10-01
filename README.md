# 🎙️ TTS Benchmarking Tool

A comprehensive, production-ready benchmarking tool for comparing Text-to-Speech (TTS) providers. Built with Streamlit for easy deployment and interactive analysis.

## 🌟 Features

### Core Functionality
- **Multi-Provider Support**: Compare OpenAI TTS and Murf AI (easily extensible)
- **Custom Text Upload**: Support for TXT, CSV, JSON, MD, PY, JS, HTML files
- **Comprehensive Metrics**: Latency, success rates, file sizes, and quality analysis
- **ELO Rating System**: Chess-style rankings for objective provider comparison
- **Interactive Visualizations**: Charts, heatmaps, and real-time analytics
- **Batch Testing**: Run comprehensive benchmarks across diverse datasets

### Advanced Analytics
- **Statistical Analysis**: Percentile distributions, confidence intervals
- **Category-based Testing**: Performance across different text types (news, literature, technical, etc.)
- **Length Analysis**: How providers perform with varying text lengths (10-200 words)
- **Error Analysis**: Detailed failure mode analysis and debugging
- **Export Options**: JSON, CSV, Excel, and comprehensive report packages

### Production Features
- **Secure API Key Management**: Environment-based configuration
- **Scalable Architecture**: Async processing and rate limiting
- **Real-world Testing**: Network overhead, cold starts, multiple iterations
- **Deployment Ready**: Docker, Hugging Face Spaces compatible

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- API keys for TTS providers

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd BenchMarking_Tool
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API keys**
   ```bash
   cp env_example.txt .env
   # Edit .env with your API keys
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

### Environment Variables

Create a `.env` file with your API credentials:

```bash
# Required API Keys
OPENAI_API_KEY=your_openai_api_key_here
MURF_API_KEY=your_murf_api_key_here

# Optional Configuration
STREAMLIT_SERVER_PORT=8501
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT_SECONDS=30
```

## 📊 Usage Guide

### Quick Test
1. Navigate to "Quick Test" in the sidebar
2. Enter your text prompt
3. Select providers and voices
4. Click "Generate & Compare" to see real-time results

### Upload Custom Text
1. Go to "Upload Custom Text"
2. Upload text files (TXT, CSV, JSON, MD, PY, JS, HTML) or enter text manually
3. Configure processing options (auto-categorization, sample limits)
4. Process files to extract text samples
5. Use samples for benchmarking or export for later use

### Batch Benchmark
1. Go to "Batch Benchmark"
2. Configure test parameters:
   - Number of samples (5-50)
   - Text categories (news, literature, technical, etc.)
   - Length categories (short, medium, long, very long)
   - Number of iterations per test
3. Choose dataset source:
   - Generate new dataset
   - Use uploaded samples
   - Combine both sources
4. Prepare test dataset
5. Run comprehensive benchmark
6. View detailed analytics and comparisons

### Results Analysis
- Filter results by provider, category, or success status
- View latency distributions and performance heatmaps
- Analyze error patterns and failure modes
- Export results in multiple formats

### Leaderboard
- View ELO-based rankings
- Understand relative provider performance
- Track performance changes over time

## 🏗️ Architecture

### Core Components

```
├── app.py                 # Main Streamlit application
├── config.py             # Configuration and settings
├── tts_providers.py      # TTS provider implementations
├── benchmarking_engine.py # Core benchmarking logic
├── dataset.py            # Test dataset generation
├── visualizations.py     # Chart and graph generation
├── export_utils.py       # Export functionality
└── requirements.txt      # Python dependencies
```

### Key Classes

- **`TTSProvider`**: Abstract base for TTS implementations
- **`BenchmarkEngine`**: Orchestrates testing and analysis
- **`DatasetGenerator`**: Creates diverse test datasets
- **`ExportManager`**: Handles result exports and reporting

## 🔧 Extending the Tool

### Adding New TTS Providers

1. **Create provider class**:
   ```python
   class NewTTSProvider(TTSProvider):
       def __init__(self):
           super().__init__("new_provider")
       
       async def generate_speech(self, request: TTSRequest) -> TTSResult:
           # Implementation here
           pass
   ```

2. **Update configuration**:
   ```python
   # In config.py
   TTS_PROVIDERS["new_provider"] = TTSConfig(
       name="New Provider",
       api_key_env="NEW_PROVIDER_API_KEY",
       base_url="https://api.newprovider.com/tts",
       supported_voices=["voice1", "voice2"],
       max_chars=5000,
       supports_streaming=True
   )
   ```

3. **Register in factory**:
   ```python
   # In tts_providers.py
   @staticmethod
   def create_provider(provider_id: str) -> TTSProvider:
       if provider_id == "new_provider":
           return NewTTSProvider()
       # ... existing providers
   ```

### Custom Metrics

Add new metrics by extending the `BenchmarkResult` class and updating the analysis functions in `benchmarking_engine.py`.

### Custom Visualizations

Create new charts in `visualizations.py` following the existing patterns with Plotly.

## 🚢 Deployment

### Hugging Face Spaces

1. **Create new Space** on Hugging Face
2. **Upload files** to your Space repository
3. **Set secrets** for API keys in Space settings
4. **Deploy** - the app will automatically start

### Docker Deployment

```bash
# Build image
docker build -t tts-benchmark .

# Run container
docker run -p 8501:8501 \
  -e OPENAI_API_KEY=your_key \
  -e MURF_API_KEY=your_key \
  tts-benchmark
```

### Local Development

```bash
# Install in development mode
pip install -e .

# Run with hot reload
streamlit run app.py --server.runOnSave=true
```

## 📈 Benchmarking Methodology

### Test Dataset
- **100 diverse samples** across 5 categories
- **4 length categories**: 10-30, 31-80, 81-150, 151-200 words
- **Real-world content**: News, literature, conversation, technical, narrative
- **Complexity scoring**: Based on word length, sentence structure, punctuation

### Metrics Collected
- **Latency**: End-to-end response time including network overhead
- **Success Rate**: Percentage of successful generations
- **File Size**: Audio output size as quality proxy
- **Error Analysis**: Categorized failure modes
- **Consistency**: Performance variance across iterations

### Statistical Analysis
- **ELO Ratings**: Head-to-head comparisons for objective ranking
- **Percentile Analysis**: P50, P90, P95, P99 latency distributions
- **Confidence Intervals**: Statistical significance testing
- **Category Performance**: Specialized analysis by content type

## 🔒 Security & Privacy

- **API Key Security**: Environment-based configuration, no hardcoded keys
- **Rate Limiting**: Configurable request throttling
- **Data Privacy**: No audio data stored permanently
- **Error Handling**: Graceful failure management
- **Input Validation**: Text length and content validation

## 📋 API Reference

### Core Classes

#### `TTSRequest`
```python
@dataclass
class TTSRequest:
    text: str
    voice: str
    provider: str
    model: Optional[str] = None
    speed: float = 1.0
    format: str = "mp3"
```

#### `TTSResult`
```python
@dataclass
class TTSResult:
    success: bool
    audio_data: Optional[bytes]
    latency_ms: float
    file_size_bytes: int
    error_message: Optional[str]
    metadata: Dict[str, Any]
```

#### `BenchmarkResult`
```python
@dataclass
class BenchmarkResult:
    test_id: str
    provider: str
    sample_id: str
    text: str
    voice: str
    success: bool
    latency_ms: float
    file_size_bytes: int
    error_message: Optional[str]
    timestamp: str
    metadata: Dict[str, Any]
    iteration: int
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

### Development Guidelines
- Follow PEP 8 style guidelines
- Add type hints for all functions
- Include docstrings for public methods
- Write tests for new functionality
- Update documentation for API changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Artificial Analysis** - Inspiration for objective metrics and leaderboards
- **Hugging Face TTS Arena** - User-driven quality comparison concepts
- **Streamlit** - Excellent framework for rapid prototyping
- **Plotly** - Interactive visualization capabilities

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Documentation**: [Wiki](https://github.com/your-repo/wiki)

## 🗺️ Roadmap

### Upcoming Features
- [ ] **More TTS Providers**: ElevenLabs, Azure Cognitive Services, Google Cloud TTS
- [ ] **Audio Quality Metrics**: PESQ, STOI, MOS scoring
- [ ] **Real-time Streaming**: WebSocket-based live comparison
- [ ] **A/B Testing Framework**: Statistical significance testing
- [ ] **Custom Voice Training**: Provider-specific voice fine-tuning analysis
- [ ] **Multi-language Support**: International TTS provider comparison
- [ ] **API Endpoints**: REST API for programmatic access
- [ ] **Automated Reporting**: Scheduled benchmark runs and email reports

### Version History
- **v1.0.0**: Initial release with OpenAI and Murf AI support
- **v1.1.0**: Enhanced visualizations and export options
- **v1.2.0**: ELO rating system and statistical analysis
- **v2.0.0**: Multi-provider architecture and extensibility

---

**Built with ❤️ for the TTS community**
