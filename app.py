"""
TTS Benchmarking Tool - Streamlit Application
"""
import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
from datetime import datetime
from typing import Dict, List, Any

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Import our modules
from config import TTS_PROVIDERS, UI_CONFIG, validate_config
from dataset import DatasetGenerator, TestSample
from benchmarking_engine import BenchmarkEngine, BenchmarkResult
from tts_providers import TTSProviderFactory, TTSRequest
import visualizations
from security import session_manager
from geolocation import geo_service

# Page configuration
st.set_page_config(
    page_title=UI_CONFIG["page_title"],
    page_icon=UI_CONFIG["page_icon"],
    layout=UI_CONFIG["layout"],
    initial_sidebar_state="expanded"
)

# Load external CSS
def load_css():
    with open('styles.css', 'r') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Apply custom styles
load_css()

# Initialize session state
if "benchmark_engine" not in st.session_state:
    st.session_state.benchmark_engine = BenchmarkEngine()

if "dataset_generator" not in st.session_state:
    st.session_state.dataset_generator = DatasetGenerator()

if "results" not in st.session_state:
    st.session_state.results = []

if "config_valid" not in st.session_state:
    st.session_state.config_valid = False

if "navigate_to" not in st.session_state:
    st.session_state.navigate_to = None

def get_model_name(provider: str) -> str:
    """Helper function to get model name from config"""
    return TTS_PROVIDERS.get(provider).model_name if provider in TTS_PROVIDERS else provider

def get_location_display(result: BenchmarkResult = None, country: str = None, city: str = None) -> str:
    """Helper function to format location display with flag"""
    if result:
        country = result.location_country
        city = result.location_city
    
    if not country or country == 'Unknown':
        return '🌍 Unknown'
    
    # Get country flag
    flag = geo_service.get_country_flag(getattr(result, 'location_country', None) if result else None)
    
    # Format location string
    if city and city != 'Unknown':
        return f"{flag} {city}, {country}"
    return f"{flag} {country}"

def check_configuration():
    """Check if API keys are configured"""
    config_status = validate_config()
    st.session_state.config_valid = config_status["valid"]
    return config_status

def main():
    """Main application function"""
    
    # Header
    st.title("TTS Benchmarking Tool")
    st.markdown("Compare Text-to-Speech providers with comprehensive metrics and analysis")
    
    # Sidebar for navigation and configuration
    with st.sidebar:
        # Navigation - moved to top
        # Check if there's a navigation request from a button
        if "navigate_to" in st.session_state and st.session_state.navigate_to:
            default_page = st.session_state.navigate_to
            st.session_state.navigate_to = None  # Clear after using
        else:
            default_page = "Quick Test"
        
        st.subheader("Navigate to:")
        
        pages = ["Quick Test", "Blind Test", "Batch Benchmark", "Results Analysis", "Leaderboard"]
        default_index = pages.index(default_page) if default_page in pages else 0
        
        page = st.selectbox(
            "",
            pages,
            index=default_index,
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Configuration
        st.subheader("Configuration")
        
        # Check API configuration
        config_status = check_configuration()
        
        if config_status["valid"]:
            # Show status for each provider
            for provider_id, status in config_status["providers"].items():
                provider_name = TTS_PROVIDERS[provider_id].name
                if status["configured"]:
                    st.write(f"🟢 {provider_name}")
                else:
                    st.write(f"🔴 {provider_name}")
        else:
            st.error("❌ No API keys configured")
            st.markdown("**Set at least one API key:**")
            for provider_id, status in config_status["providers"].items():
                if not status["configured"]:
                    env_var = TTS_PROVIDERS[provider_id].api_key_env
                    provider_name = TTS_PROVIDERS[provider_id].name
                    st.code(f"export {env_var}=your_api_key_here")
                    st.caption(f"For {provider_name}")
    
    # Main content based on selected page
    if page == "Quick Test":
        quick_test_page()
    elif page == "Blind Test":
        blind_test_page()
    elif page == "Batch Benchmark":
        batch_benchmark_page()
    elif page == "Results Analysis":
        results_analysis_page()
    elif page == "Leaderboard":
        leaderboard_page()

def quick_test_page():
    """Quick test page for single TTS comparisons"""
    
    st.header("🚀 Quick Test")
    st.markdown("Test a single text prompt across multiple TTS providers")
    
    # Initialize session state for quick test results
    if "quick_test_results" not in st.session_state:
        st.session_state.quick_test_results = None
    
    # Get configuration status
    config_status = check_configuration()
    
    if not st.session_state.config_valid:
        st.warning("Please configure at least one API key in the sidebar first.")
        return
    
    # Get only configured providers
    configured_providers = [
        provider_id for provider_id, status in config_status["providers"].items() 
        if status["configured"]
    ]
    
    if not configured_providers:
        st.error("No providers are configured. Please set API keys in the sidebar.")
        return
    
    # Text input (full width)
    text_input = st.text_area(
        "Enter text to synthesize:",
        value="Hello, this is a test of the text-to-speech system. How does it sound?",
        height=100,
        max_chars=1000
    )
    
    word_count = len(text_input.split())
    st.caption(f"Word count: {word_count}")
    
    # Provider selection - only show configured providers
    selected_providers = st.multiselect(
        "Select providers:",
        configured_providers,
        default=configured_providers,
        help=f"Available providers: {', '.join([TTS_PROVIDERS[p].name for p in configured_providers])}"
    )
    
    # Voice selection - display in rows of 4 columns
    voice_options = {}
    if selected_providers:
        st.markdown("**Voice Selection:**")
        
        # Create rows of 4 columns each
        for i in range(0, len(selected_providers), 4):
            cols = st.columns(4)
            for j, provider in enumerate(selected_providers[i:i+4]):
                with cols[j]:
                    voices = TTS_PROVIDERS[provider].supported_voices
                    voice_options[provider] = st.selectbox(
                        f"{provider.title()} voice:",
                        voices,
                        key=f"voice_{provider}"
                    )
    
    # Test button
    if st.button("Generate & Compare", type="primary"):
        if text_input and selected_providers:
            # Validate input with security checks
            valid, error_msg = session_manager.validate_request(text_input)
            if valid:
                run_quick_test(text_input, selected_providers, voice_options)
            else:
                st.error(f"❌ {error_msg}")
        else:
            st.error("Please enter text and select at least one provider.")
    
    # Display results BELOW the input section (outside button context)
    if st.session_state.quick_test_results is not None:
        st.markdown("---")  # Separator line
        display_quick_test_results(st.session_state.quick_test_results)

def run_quick_test(text: str, providers: List[str], voice_options: Dict[str, str]):
    """Run quick test for selected providers"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    
    async def test_provider(provider_id: str, voice: str):
        try:
            provider = TTSProviderFactory.create_provider(provider_id)
            
            # Create test sample
            sample = TestSample(
                id="quick_test",
                text=text,
                word_count=len(text.split()),
                category="user_input",
                length_category="custom",
                complexity_score=0.5
            )
            
            result = await st.session_state.benchmark_engine.run_single_test(
                provider, sample, voice
            )
            return result
            
        except Exception as e:
            st.error(f"Error testing {provider_id}: {str(e)}")
            return None
    
    # Run tests
    for i, provider_id in enumerate(providers):
        status_text.text(f"Testing {provider_id}...")
        
        voice = voice_options[provider_id]
        result = asyncio.run(test_provider(provider_id, voice))
        
        if result:
            results.append(result)
        
        progress_bar.progress((i + 1) / len(providers))
    
    status_text.text("✅ Tests completed!")
    
    # Clean up progress indicators after a moment
    import time
    time.sleep(0.5)
    progress_bar.empty()
    status_text.empty()
    
    # Store results in session state for display
    if results:
        st.session_state.quick_test_results = results
    else:
        st.error("No successful results to display.")
        st.session_state.quick_test_results = None

def display_quick_test_results(results: List[BenchmarkResult]):
    """Display quick test results"""
    
    st.subheader("📊 Test Results")
    
    # Create results table
    data = []
    for result in results:
        data.append({
            "Provider": result.provider.title(),
            "Model": result.model_name,
            "Location": get_location_display(result),
            "Success": "✅" if result.success else "❌",
            "Latency (ms)": f"{result.latency_ms:.1f}" if result.success else "N/A",
            "File Size (KB)": f"{result.file_size_bytes / 1024:.1f}" if result.success else "N/A",
            "Voice": result.voice,
            "Error": result.error_message if not result.success else ""
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    
    # Visualizations for successful results
    successful_results = [r for r in results if r.success]
    
    if len(successful_results) > 1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Latency comparison
            fig_latency = px.bar(
                x=[r.provider.title() for r in successful_results],
                y=[r.latency_ms for r in successful_results],
                title="Latency Comparison",
                labels={"x": "Provider", "y": "Latency (ms)"}
            )
            st.plotly_chart(fig_latency, use_container_width=True)
        
        with col2:
            # File size comparison
            fig_size = px.bar(
                x=[r.provider.title() for r in successful_results],
                y=[r.file_size_bytes / 1024 for r in successful_results],
                title="File Size Comparison",
                labels={"x": "Provider", "y": "File Size (KB)"}
            )
            st.plotly_chart(fig_size, use_container_width=True)
    
    # Audio playback
    st.subheader("Audio Playback")
    
    if len(successful_results) >= 1:
        st.markdown("**Listen to the audio samples:**")
        
        # Display audio players in rows of 4
        for i in range(0, len(successful_results), 4):
            cols = st.columns(4)
            for j, result in enumerate(successful_results[i:i+4]):
                with cols[j]:
                    st.markdown(f"**{result.provider.title()}**")
                    st.caption(f"Model: {result.model_name}")
                    
                    if result.audio_data:
                        # Audio player
                        st.audio(result.audio_data, format="audio/mp3")
                        st.caption(f"Latency: {result.latency_ms:.1f}ms")
                        st.caption(f"Size: {result.file_size_bytes/1024:.1f} KB")

def blind_test_page():
    """Blind test page for unbiased audio quality comparison"""
    
    st.header("🎭 Blind Test")
    st.markdown("Compare TTS audio quality without knowing which provider generated each sample")
    
    # Get configuration status
    config_status = check_configuration()
    
    if not st.session_state.config_valid:
        st.warning("Please configure at least one API key in the sidebar first.")
        return
    
    # Get only configured providers
    configured_providers = [
        provider_id for provider_id, status in config_status["providers"].items() 
        if status["configured"]
    ]
    
    if len(configured_providers) < 2:
        st.warning("⚠️ Blind test requires at least 2 configured providers. Please configure more API keys.")
        return
    
    # Initialize blind test state
    if "blind_test_samples" not in st.session_state:
        st.session_state.blind_test_samples = []
    
    if "blind_test_results" not in st.session_state:
        st.session_state.blind_test_results = []
    
    if "blind_test_voted" not in st.session_state:
        st.session_state.blind_test_voted = False
    
    if "blind_test_vote_choice" not in st.session_state:
        st.session_state.blind_test_vote_choice = None
    
    # Test setup section
    st.subheader("🔧 Test Setup")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Text input
        text_input = st.text_area(
            "Enter text to test:",
            value="The quick brown fox jumps over the lazy dog. This is a test of speech synthesis quality.",
            height=100,
            max_chars=500
        )
        
        word_count = len(text_input.split())
        st.caption(f"Word count: {word_count}")
    
    with col2:
        st.markdown("""
        **How Blind Testing Works:**
        1. Enter text to synthesize
        2. Audio generated from all providers
        3. Samples randomized (labeled A, B, etc.)
        4. Listen and vote for your favorite
        5. Results revealed after voting
        """)
    
    # Generate blind test samples
    if st.button("Generate Blind Test", type="primary"):
        if text_input and len(configured_providers) >= 2:
            # Validate input
            valid, error_msg = session_manager.validate_request(text_input)
            if valid:
                generate_blind_test_samples(text_input, configured_providers)
            else:
                st.error(f"❌ {error_msg}")
        else:
            st.error("Please enter text. At least 2 providers must be configured.")
    
    # Display blind test samples if available
    if st.session_state.blind_test_samples:
        display_blind_test_samples()

def generate_blind_test_samples(text: str, providers: List[str]):
    """Generate audio samples for blind testing"""
    
    import random
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    
    async def test_provider(provider_id: str):
        try:
            provider = TTSProviderFactory.create_provider(provider_id)
            
            # Use first available voice for each provider
            voices = TTS_PROVIDERS[provider_id].supported_voices
            voice = voices[0] if voices else "default"
            
            # Create test sample
            sample = TestSample(
                id="blind_test",
                text=text,
                word_count=len(text.split()),
                category="blind_test",
                length_category="custom",
                complexity_score=0.5
            )
            
            result = await st.session_state.benchmark_engine.run_single_test(
                provider, sample, voice
            )
            return result
            
        except Exception as e:
            st.error(f"Error testing provider: {str(e)}")
            return None
    
    # Run tests
    for i, provider_id in enumerate(providers):
        status_text.text(f"Generating sample {i+1}/{len(providers)}...")
        
        result = asyncio.run(test_provider(provider_id))
        
        if result and result.success:
            results.append(result)
        
        progress_bar.progress((i + 1) / len(providers))
    
    status_text.text("Samples generated!")
    
    if len(results) < 2:
        st.error("❌ Not enough successful samples generated. Please try again.")
        st.session_state.blind_test_samples = []
        return
    
    # Randomize the order of samples
    random.shuffle(results)
    
    # Assign anonymous labels (A, B, C, etc.)
    labels = ['A', 'B', 'C', 'D', 'E', 'F']
    for i, result in enumerate(results):
        result.blind_label = labels[i]
    
    # Store samples in session state
    st.session_state.blind_test_samples = results
    st.session_state.blind_test_voted = False
    st.session_state.blind_test_vote_choice = None
    
    st.success(f"✅ Generated {len(results)} blind test samples!")
    st.rerun()

def display_blind_test_samples():
    """Display blind test samples for voting"""
    
    samples = st.session_state.blind_test_samples
    
    if not st.session_state.blind_test_voted:
        # Voting phase - don't reveal providers
        st.subheader("🔊 Listen and Vote")
        st.markdown("**Listen to each sample and vote for the one with the best quality:**")
        
        # Display samples in rows of 4
        for i in range(0, len(samples), 4):
            cols = st.columns(4)
            for j, result in enumerate(samples[i:i+4]):
                with cols[j]:
                    st.markdown(f"### Sample {result.blind_label}")
                    
                    if result.audio_data:
                        # Audio player
                        st.audio(result.audio_data, format="audio/mp3")
                        st.caption(f"Sample {result.blind_label}")
        
        st.divider()
        
        # Voting section
        st.markdown("### 🗳️ Cast Your Vote")
        
        vote_options = [f"Sample {r.blind_label}" for r in samples]
        selected_sample = st.radio(
            "Which sample sounds best to you?",
            vote_options,
            key="blind_vote_radio"
        )
        
        if st.button("Submit Vote", type="primary"):
            # Record vote
            selected_label = selected_sample.split()[1]  # Extract label (A, B, C, etc.)
            st.session_state.blind_test_vote_choice = selected_label
            st.session_state.blind_test_voted = True
            
            # Find the winning sample
            winner_result = next(r for r in samples if r.blind_label == selected_label)
            
            # Update ELO ratings - winner beats all others
            for result in samples:
                if result.blind_label != selected_label:
                    handle_blind_test_vote(winner_result, result)
            
            st.rerun()
    
    else:
        # Results phase - reveal providers
        st.subheader("🎉 Results Revealed!")
        
        # Show which sample the user voted for
        voted_sample = next(r for r in samples if r.blind_label == st.session_state.blind_test_vote_choice)
        
        st.success(f"**You voted for Sample {st.session_state.blind_test_vote_choice}**")
        st.info(f"**Sample {st.session_state.blind_test_vote_choice} was generated by: {voted_sample.provider.title()} ({voted_sample.model_name})**")
        
        st.divider()
        
        # Show all samples with revealed providers
        st.subheader("🔓 All Samples Revealed")
        
        # Create comparison table
        comparison_data = []
        for result in sorted(samples, key=lambda r: r.blind_label):
            is_winner = result.blind_label == st.session_state.blind_test_vote_choice
            comparison_data.append({
                "Sample": result.blind_label,
                "Provider": result.provider.title(),
                "Model": result.model_name,
                "Location": get_location_display(result),
                "Latency (ms)": f"{result.latency_ms:.1f}",
                "File Size (KB)": f"{result.file_size_bytes / 1024:.1f}",
                "Your Choice": "🏆 Winner" if is_winner else ""
            })
        
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Show audio samples with labels
        st.subheader("🔊 Listen Again (with provider names)")
        
        # Display audio players in rows of 4
        sorted_samples = sorted(samples, key=lambda r: r.blind_label)
        for i in range(0, len(sorted_samples), 4):
            cols = st.columns(4)
            for j, result in enumerate(sorted_samples[i:i+4]):
                with cols[j]:
                    is_winner = result.blind_label == st.session_state.blind_test_vote_choice
                    if is_winner:
                        st.markdown(f"### 🏆 Sample {result.blind_label}")
                    else:
                        st.markdown(f"### Sample {result.blind_label}")
                    
                    st.markdown(f"**{result.provider.title()}**")
                    st.caption(result.model_name)
                    
                    if result.audio_data:
                        st.audio(result.audio_data, format="audio/mp3")
                        st.caption(f"{result.latency_ms:.1f}ms | {result.file_size_bytes/1024:.1f}KB")
        
        st.divider()
        
        # Action buttons
    col1, col2 = st.columns(2)
        
    with col1:
            if st.button("Start New Blind Test", type="primary", use_container_width=True):
                st.session_state.blind_test_samples = []
                st.session_state.blind_test_voted = False
                st.session_state.blind_test_vote_choice = None
                st.rerun()
        
    with col2:
            if st.button("View Leaderboard", use_container_width=True):
                # Navigate to leaderboard by setting session state
                st.session_state.navigate_to = "Leaderboard"
                st.rerun()

def handle_blind_test_vote(winner_result: BenchmarkResult, loser_result: BenchmarkResult):
    """Handle blind test vote and update ELO ratings"""
    
    from database import db
    
    try:
        # Get current ratings
        winner_rating_before = db.get_elo_rating(winner_result.provider)
        loser_rating_before = db.get_elo_rating(loser_result.provider)
        
        # Update ratings
        new_winner_rating, new_loser_rating = db.update_elo_ratings(
            winner_result.provider, loser_result.provider, k_factor=32
        )
        
        # Save the vote in database
        db.save_user_vote(
            winner_result.provider, 
            loser_result.provider, 
            winner_result.text[:100] + "..." if len(winner_result.text) > 100 else winner_result.text,
            session_id="blind_test_session"
        )
        
    except Exception as e:
        st.error(f"Error updating ratings: {e}")

def batch_benchmark_page():
    """Batch benchmark page for comprehensive testing"""
    
    st.header("📈 Batch Benchmark")
    st.markdown("Run comprehensive benchmarks across multiple samples and providers")
    
    # Get configuration status
    config_status = check_configuration()
    
    if not st.session_state.config_valid:
        st.warning("Please configure at least one API key in the sidebar first.")
        return
    
    # Get only configured providers
    configured_providers = [
        provider_id for provider_id, status in config_status["providers"].items() 
        if status["configured"]
    ]
    
    if not configured_providers:
        st.error("No providers are configured. Please set API keys in the sidebar.")
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Test Configuration")
        
        # Provider selection - only show configured providers
        selected_providers = st.multiselect(
            "Select providers:",
            configured_providers,
            default=configured_providers,
            help=f"Available providers: {', '.join([TTS_PROVIDERS[p].name for p in configured_providers])}"
        )
        
        # Sample selection
        sample_count = st.slider("Number of samples:", 5, 50, 20)
        
        # Category filter
        categories = ["news", "literature", "conversation", "technical", "narrative"]
        selected_categories = st.multiselect(
            "Categories:",
            categories,
            default=categories
        )
        
        # Length categories
        length_categories = ["short", "medium", "long", "very_long"]
        selected_lengths = st.multiselect(
            "Length categories:",
            length_categories,
            default=length_categories
        )
        
        iterations = st.slider("Iterations per test:", 1, 5, 3)
    
    with col2:
        st.subheader("Voice Configuration")
        
        voice_config = {}
        for provider in selected_providers:
            voices = TTS_PROVIDERS[provider].supported_voices
            voice_config[provider] = st.multiselect(
                f"{provider.title()} voices:",
                voices,
                default=[voices[0]] if voices else [],
                key=f"batch_voices_{provider}"
            )
    
    # Run benchmark button
    if st.button("Run Benchmark", type="primary"):
        if selected_providers:
            # Generate test samples automatically
            prepare_test_dataset(sample_count, selected_categories, selected_lengths)
            run_batch_benchmark(selected_providers, voice_config, iterations)
        else:
            st.error("Please select at least one provider first.")

def prepare_test_dataset(sample_count: int, categories: List[str], lengths: List[str]):
    """Prepare test dataset for batch benchmarking"""
    
    with st.spinner("Preparing test dataset..."):
        final_samples = []
        
        # Generate more samples to ensure we have enough after filtering
        all_samples = st.session_state.dataset_generator.generate_dataset(sample_count * 4)
        
        # Filter samples that match criteria
        matching_samples = []
        for sample in all_samples:
            if (sample.category in categories and 
                sample.length_category in lengths):
                matching_samples.append(sample)
        
        # If we don't have enough matching samples, generate more
        attempts = 0
        while len(matching_samples) < sample_count and attempts < 3:
            additional_samples = st.session_state.dataset_generator.generate_dataset(sample_count * 2)
            for sample in additional_samples:
                if (sample.category in categories and 
                    sample.length_category in lengths and 
                    len(matching_samples) < sample_count * 2):
                    matching_samples.append(sample)
            attempts += 1
        
        # Take the requested number of samples
        final_samples = matching_samples[:sample_count]
        
        st.session_state.test_samples = final_samples
    
    if final_samples:
        st.success(f"Prepared {len(final_samples)} test samples")
        
        # Display sample statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Samples", len(final_samples))
        
        with col2:
            avg_words = sum(s.word_count for s in final_samples) / len(final_samples)
            st.metric("Avg Words", f"{avg_words:.1f}")
        
        with col3:
            avg_complexity = sum(s.complexity_score for s in final_samples) / len(final_samples)
            st.metric("Avg Complexity", f"{avg_complexity:.2f}")
        
        # Show sample breakdown
        with st.expander("📋 Sample Breakdown"):
            breakdown_data = []
            category_counts = {}
            length_counts = {}
            
            for sample in final_samples:
                category_counts[sample.category] = category_counts.get(sample.category, 0) + 1
                length_counts[sample.length_category] = length_counts.get(sample.length_category, 0) + 1
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**By Category:**")
                for category, count in category_counts.items():
                    st.write(f"- {category}: {count}")
            
            with col2:
                st.write("**By Length:**")
                for length, count in length_counts.items():
                    st.write(f"- {length}: {count}")
    
    else:
        st.warning("No samples match the selected criteria. Try adjusting your filters.")

def run_batch_benchmark(providers: List[str], voice_config: Dict[str, List[str]], iterations: int):
    """Run batch benchmark"""
    
    samples = st.session_state.get("test_samples", [])
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def progress_callback(completed: int, total: int):
        progress = completed / total
        progress_bar.progress(progress)
        status_text.text(f"Progress: {completed}/{total} tests completed ({progress*100:.1f}%)")
    
    # Run benchmark
    with st.spinner("Running benchmark..."):
        results = asyncio.run(
            st.session_state.benchmark_engine.run_benchmark_suite(
                providers=providers,
                samples=samples,
                voices_per_provider=voice_config,
                iterations=iterations,
                progress_callback=progress_callback
            )
        )
    
    st.session_state.results.extend(results)
    
    # Update ELO ratings
    st.session_state.benchmark_engine.update_elo_ratings(results)
    
    st.success(f"Benchmark completed! {len(results)} tests run.")
    
    # Display summary
    display_benchmark_summary(results)

def display_benchmark_summary(results: List[BenchmarkResult]):
    """Display benchmark summary"""
    
    st.subheader("📊 Benchmark Summary")
    
    # Calculate summary statistics
    summaries = st.session_state.benchmark_engine.calculate_summary_stats(results)
    
    # Create summary table with model names
    # Get current location for display
    current_location = geo_service.get_location_string()
    
    summary_data = []
    for provider, summary in summaries.items():
        summary_data.append({
            "Provider": provider.title(),
            "Model": get_model_name(provider),
            "Location": f"{geo_service.get_country_flag()} {current_location}",
            "Success Rate": f"{summary.success_rate:.1f}%",
            "Avg Latency": f"{summary.avg_latency_ms:.1f}ms",
            "P95 Latency": f"{summary.p95_latency_ms:.1f}ms",
            "Avg File Size": f"{summary.avg_file_size_bytes/1024:.1f}KB",
            "Total Errors": summary.total_errors
        })
    
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True)

def results_analysis_page():
    """Results analysis page"""
    
    st.header("📊 Results Analysis")
    st.markdown("Analyze benchmark results with detailed metrics and comparisons")
    
    if not st.session_state.results:
        st.info("No benchmark results available. Run a benchmark first.")
        return
    
    # Filter controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        providers = list(set(r.provider for r in st.session_state.results))
        selected_providers = st.multiselect("Filter by provider:", providers, default=providers)
    
    with col2:
        categories = list(set(r.metadata.get("category", "unknown") for r in st.session_state.results))
        selected_categories = st.multiselect("Filter by category:", categories, default=categories)
    
    with col3:
        success_filter = st.selectbox("Success filter:", ["All", "Successful only", "Failed only"])
    
    # Filter results
    filtered_results = st.session_state.results
    
    if selected_providers:
        filtered_results = [r for r in filtered_results if r.provider in selected_providers]
    
    if selected_categories:
        filtered_results = [r for r in filtered_results if r.metadata.get("category") in selected_categories]
    
    if success_filter == "Successful only":
        filtered_results = [r for r in filtered_results if r.success]
    elif success_filter == "Failed only":
        filtered_results = [r for r in filtered_results if not r.success]
    
    if not filtered_results:
        st.warning("No results match the selected filters.")
        return
    
    # Display visualizations
    display_analysis_charts(filtered_results)

def display_analysis_charts(results: List[BenchmarkResult]):
    """Display analysis charts"""
    
    successful_results = [r for r in results if r.success]
    
    if not successful_results:
        st.warning("No successful results to analyze.")
        return
    
    # Latency distribution
    st.subheader("⏱️ Latency Distribution")
    fig_latency = visualizations.create_latency_distribution(successful_results)
    st.plotly_chart(fig_latency, use_container_width=True)
    
    # Success rate by provider
    st.subheader("✅ Success Rate Analysis")
    fig_success = visualizations.create_success_rate_chart(results)
    st.plotly_chart(fig_success, use_container_width=True)
    
    # Performance by category
    st.subheader("📚 Performance by Category")
    
    category_data = {}
    for result in successful_results:
        category = result.metadata.get("category", "unknown")
        if category not in category_data:
            category_data[category] = {"latencies": [], "providers": []}
        category_data[category]["latencies"].append(result.latency_ms)
        category_data[category]["providers"].append(result.provider)
    
    if category_data:
        fig_category = px.box(
            x=[provider for cat_data in category_data.values() for provider in cat_data["providers"]],
            y=[latency for cat_data in category_data.values() for latency in cat_data["latencies"]],
            color=[cat for cat, cat_data in category_data.items() for _ in cat_data["latencies"]],
            title="Latency by Category and Provider",
            labels={"x": "Provider", "y": "Latency (ms)", "color": "Category"}
        )
        st.plotly_chart(fig_category, use_container_width=True)

def leaderboard_page():
    """ELO leaderboard page with persistent data"""
    
    st.header("🏆 Leaderboard")
    st.markdown("ELO-based rankings of TTS providers (Persistent Data)")
    
    # Get persistent leaderboard data
    leaderboard = st.session_state.benchmark_engine.get_leaderboard()
    
    if not leaderboard:
        st.info("No leaderboard data available. Run benchmarks to generate rankings.")
        return
    
    # Display leaderboard chart
    try:
        fig_leaderboard = visualizations.create_leaderboard_chart(leaderboard)
        st.plotly_chart(fig_leaderboard, use_container_width=True)
    except:
        # Fallback if visualization fails
        pass
    
    # Enhanced leaderboard table with latency stats
    st.subheader("📊 Current Rankings")
    
    # Get latency statistics for each provider
    from database import db
    latency_stats = db.get_latency_stats_by_provider()
    
    # Get current location for display
    current_location = geo_service.get_location_string()
    location_display = f"{geo_service.get_country_flag()} {current_location}"
    
    df_leaderboard = pd.DataFrame(leaderboard)
    df_leaderboard["Provider"] = df_leaderboard["provider"].str.title()
    
    # Add model names, location, and latency stats
    df_leaderboard["Model"] = df_leaderboard["provider"].apply(get_model_name)
    df_leaderboard["Location"] = location_display
    df_leaderboard["Avg Latency (ms)"] = df_leaderboard["provider"].apply(
        lambda p: f"{latency_stats.get(p, {}).get('avg_latency', 0):.1f}"
    )
    df_leaderboard["P95 Latency (ms)"] = df_leaderboard["provider"].apply(
        lambda p: f"{latency_stats.get(p, {}).get('p95_latency', 0):.1f}"
    )
    
    # Format the display columns
    display_df = df_leaderboard[[
        "rank", "Provider", "Model", "Location", "elo_rating", "Avg Latency (ms)", "P95 Latency (ms)",
        "games_played", "wins", "losses", "win_rate"
    ]].copy()
    
    display_df.columns = [
        "Rank", "Provider", "Model", "Location", "ELO Rating", "Avg Latency", "P95 Latency",
        "Games", "Wins", "Losses", "Win Rate %"
    ]
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Provider statistics
    st.subheader("📈 Provider Statistics")
    
    # Import database to get provider stats
    from database import db
    provider_stats = db.get_provider_stats()
    
    if provider_stats:
        stats_data = []
        location_display = f"{geo_service.get_country_flag()} {geo_service.get_location_string()}"
        
        for provider, stats in provider_stats.items():
            stats_data.append({
                "Provider": provider.title(),
                "Model": get_model_name(provider),
                "Location": location_display,
                "Total Tests": stats['total_tests'],
                "Success Rate %": f"{stats['success_rate']:.1f}%",
                "Avg Latency (ms)": f"{stats['avg_latency']:.1f}",
                "Avg File Size (KB)": f"{stats['avg_file_size']/1024:.1f}"
            })
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
    
    # User voting statistics
    st.subheader("🗳️ User Voting Statistics")
    vote_stats = db.get_vote_statistics()
    
    if vote_stats['total_votes'] > 0:
        st.metric("Total User Votes", vote_stats['total_votes'])
        
        # Show vote wins per provider
        if vote_stats['wins']:
            vote_data = []
            location_display = f"{geo_service.get_country_flag()} {geo_service.get_location_string()}"
            
            for provider, wins in vote_stats['wins'].items():
                losses = vote_stats['losses'].get(provider, 0)
                total = wins + losses
                win_rate = (wins / total * 100) if total > 0 else 0
                
                vote_data.append({
                    "Provider": provider.title(),
                    "Model": get_model_name(provider),
                    "Location": location_display,
                    "User Votes Won": wins,
                    "User Win Rate %": f"{win_rate:.1f}%"
                })
            
            vote_df = pd.DataFrame(vote_data)
            st.dataframe(vote_df, use_container_width=True, hide_index=True)
    else:
        st.info("No user votes yet. Vote in Quick Test to start building preference data!")


if __name__ == "__main__":
    main()