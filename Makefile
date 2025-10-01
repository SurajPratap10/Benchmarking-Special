# TTS Benchmarking Tool - Makefile

.PHONY: dev start demo install setup clean help

# Default target
help:
	@echo "🎙️  TTS Benchmarking Tool Commands:"
	@echo ""
	@echo "  make dev     - Start development server (like npm run dev)"
	@echo "  make start   - Start production server"
	@echo "  make demo    - Run demo script"
	@echo "  make install - Install dependencies"
	@echo "  make setup   - Complete setup (install + create venv)"
	@echo "  make clean   - Clean up generated files"
	@echo ""

# Start development server (equivalent to npm run dev)
dev:
	@echo "🚀 Starting TTS Benchmarking Tool..."
	@source .env 2>/dev/null || echo "⚠️  No .env file found"; \
	source venv/bin/activate && streamlit run app.py --server.headless=true

# Start production server
start:
	@echo "🚀 Starting TTS Benchmarking Tool (Production)..."
	@source .env 2>/dev/null || echo "⚠️  No .env file found"; \
	source venv/bin/activate && streamlit run app.py --server.port=8501 --server.address=0.0.0.0

# Run demo
demo:
	@echo "🎬 Running demo..."
	@source .env 2>/dev/null || echo "⚠️  No .env file found"; \
	source venv/bin/activate && python demo.py

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@source venv/bin/activate && pip install -r requirements.txt

# Complete setup
setup:
	@echo "🔧 Setting up TTS Benchmarking Tool..."
	@python3 -m venv venv
	@source venv/bin/activate && pip install -r requirements.txt
	@echo "✅ Setup complete!"
	@echo "📝 Next steps:"
	@echo "   1. Add your API keys to .env file"
	@echo "   2. Run 'make dev' to start the application"

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	@rm -f *.json *.csv benchmark_* demo_*
	@echo "✅ Cleaned up generated files"
