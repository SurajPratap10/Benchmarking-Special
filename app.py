"""
TTS Benchmarking Tool - Streamlit Application
"""
import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import time
from datetime import datetime
import os
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
from export_utils import ExportManager
from security import session_manager, secure_api_key_input, create_security_dashboard
from text_parser import TextParser

# Page configuration
st.set_page_config(
    page_title=UI_CONFIG["page_title"],
    page_icon=UI_CONFIG["page_icon"],
    layout=UI_CONFIG["layout"],
    initial_sidebar_state="expanded"
)

# Initialize session state
if "benchmark_engine" not in st.session_state:
    st.session_state.benchmark_engine = BenchmarkEngine()

if "dataset_generator" not in st.session_state:
    st.session_state.dataset_generator = DatasetGenerator()

if "results" not in st.session_state:
    st.session_state.results = []

if "config_valid" not in st.session_state:
    st.session_state.config_valid = False

if "text_parser" not in st.session_state:
    st.session_state.text_parser = TextParser()

if "uploaded_samples" not in st.session_state:
    st.session_state.uploaded_samples = []

def check_configuration():
    """Check if API keys are configured"""
    config_status = validate_config()
    st.session_state.config_valid = config_status["valid"]
    return config_status

def main():
    """Main application function"""
    
    # Header
    st.title("🎙️ TTS Benchmarking Tool")
    st.markdown("Compare Text-to-Speech providers with comprehensive metrics and analysis")
    
    # Sidebar for configuration and navigation
    with st.sidebar:
        st.header("Configuration")
        
        # Check API configuration
        config_status = check_configuration()
        
        if config_status["valid"]:
            configured_count = config_status.get("configured_count", 0)
            total_count = len(TTS_PROVIDERS)
            if configured_count == total_count:
                st.success(f"✅ All {total_count} providers configured")
            else:
                st.success(f"✅ {configured_count}/{total_count} providers configured")
            
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
        
        st.divider()
        
        # Navigation
        page = st.selectbox(
            "Navigate to:",
            ["Quick Test", "Batch Benchmark", "Upload Custom Text", "Results Analysis", "Leaderboard", "Dataset Management", "Export Results", "Security"]
        )
    
    # Main content based on selected page
    if page == "Quick Test":
        quick_test_page()
    elif page == "Batch Benchmark":
        batch_benchmark_page()
    elif page == "Upload Custom Text":
        upload_custom_text_page()
    elif page == "Results Analysis":
        results_analysis_page()
    elif page == "Leaderboard":
        leaderboard_page()
    elif page == "Dataset Management":
        dataset_management_page()
    elif page == "Export Results":
        export_results_page()
    elif page == "Security":
        security_page()

def quick_test_page():
    """Quick test page for single TTS comparisons"""
    
    st.header("🚀 Quick Test")
    st.markdown("Test a single text prompt across multiple TTS providers")
    
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
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Text input
        text_input = st.text_area(
            "Enter text to synthesize:",
            value="Hello, this is a test of the text-to-speech system. How does it sound?",
            height=100,
            max_chars=1000
        )
        
        word_count = len(text_input.split())
        st.caption(f"Word count: {word_count}")
    
    with col2:
        # Provider selection - only show configured providers
        selected_providers = st.multiselect(
            "Select providers:",
            configured_providers,
            default=configured_providers,
            help=f"Available providers: {', '.join([TTS_PROVIDERS[p].name for p in configured_providers])}"
        )
        
        # Voice selection
        voice_options = {}
        for provider in selected_providers:
            voices = TTS_PROVIDERS[provider].supported_voices
            voice_options[provider] = st.selectbox(
                f"{provider.title()} voice:",
                voices,
                key=f"voice_{provider}"
            )
        
        # Test button
        if st.button("🎵 Generate & Compare", type="primary"):
            if text_input and selected_providers:
                # Validate input with security checks
                valid, error_msg = session_manager.validate_request(text_input)
                if valid:
                    run_quick_test(text_input, selected_providers, voice_options)
                else:
                    st.error(f"❌ {error_msg}")
            else:
                st.error("Please enter text and select at least one provider.")

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
    
    status_text.text("Tests completed!")
    
    # Display results
    if results:
        display_quick_test_results(results)
        
        # Update ELO ratings if we have multiple successful results
        successful_results = [r for r in results if r.success]
        if len(successful_results) >= 2:
            st.session_state.benchmark_engine.update_elo_ratings(results)
            st.success("🏆 ELO ratings updated based on performance comparison!")
    else:
        st.error("No successful results to display.")

def display_quick_test_results(results: List[BenchmarkResult]):
    """Display quick test results"""
    
    st.subheader("📊 Test Results")
    
    # Create results table
    data = []
    for result in results:
        data.append({
            "Provider": result.provider.title(),
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
    
    # Audio playback with voting system
    st.subheader("🔊 Audio Playback & Voting")
    
    if len(successful_results) >= 2:
        st.markdown("**Listen to both audio samples and vote for the one you prefer:**")
        
        # Create side-by-side comparison
        cols = st.columns(len(successful_results))
        
        for i, result in enumerate(successful_results):
            with cols[i]:
                st.markdown(f"**{result.provider.title()}**")
                
                if result.audio_data:
                    # Audio player
                    st.audio(result.audio_data, format="audio/mp3")
                    st.caption(f"Latency: {result.latency_ms:.1f}ms")
                    st.caption(f"Size: {result.file_size_bytes/1024:.1f} KB")
                    
                    # Voting button
                    if st.button(f"👍 Vote for {result.provider.title()}", 
                               key=f"vote_{result.provider}",
                               type="primary"):
                        handle_user_vote(successful_results, result.provider)
    
    elif len(successful_results) == 1:
        # Single result - just show audio
        result = successful_results[0]
        st.markdown(f"**{result.provider.title()}**")
        if result.audio_data:
            st.audio(result.audio_data, format="audio/mp3")
            st.caption(f"{result.provider.title()} - {result.latency_ms:.1f}ms - {result.file_size_bytes/1024:.1f} KB")

def handle_user_vote(results: List[BenchmarkResult], winner_provider: str):
    """Handle user voting for audio preference"""
    
    # Import database for vote storage
    from database import db
    
    # Find all providers in this comparison
    providers = [r.provider for r in results if r.success]
    
    if len(providers) < 2:
        st.warning("Need at least 2 providers to vote!")
        return
    
    # Show immediate feedback
    st.success(f"🏆 **{winner_provider.title()}** wins your vote!")
    
    # Update ELO ratings - winner beats all other providers
    elo_updates = []
    for provider in providers:
        if provider != winner_provider:
            try:
                # Get current ratings
                winner_rating_before = db.get_elo_rating(winner_provider)
                loser_rating_before = db.get_elo_rating(provider)
                
                # Update ratings
                new_winner_rating, new_loser_rating = db.update_elo_ratings(
                    winner_provider, provider, k_factor=32
                )
                
                # Calculate changes
                winner_change = new_winner_rating - winner_rating_before
                loser_change = new_loser_rating - loser_rating_before
                
                elo_updates.append({
                    'winner': winner_provider,
                    'loser': provider,
                    'winner_change': winner_change,
                    'loser_change': loser_change,
                    'new_winner_rating': new_winner_rating,
                    'new_loser_rating': new_loser_rating
                })
                
                # Save the vote in database
                db.save_user_vote(
                    winner_provider, 
                    provider, 
                    results[0].text[:100] + "..." if len(results[0].text) > 100 else results[0].text,
                    session_id="streamlit_session"
                )
                
            except Exception as e:
                st.error(f"Error updating ratings: {e}")
    
    # Show ELO updates
    if elo_updates:
        st.markdown("### 📈 ELO Rating Changes")
        for update in elo_updates:
            winner_change_str = f"+{update['winner_change']:.1f}" if update['winner_change'] > 0 else f"{update['winner_change']:.1f}"
            loser_change_str = f"+{update['loser_change']:.1f}" if update['loser_change'] > 0 else f"{update['loser_change']:.1f}"
            
            st.info(f"📊 {update['winner'].title()}: {winner_change_str} → {update['new_winner_rating']:.1f} ELO")
            st.info(f"📊 {update['loser'].title()}: {loser_change_str} → {update['new_loser_rating']:.1f} ELO")
    
    # Show vote statistics
    st.markdown("### 🗳️ Vote Statistics")
    vote_stats = db.get_vote_statistics()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total User Votes", vote_stats['total_votes'])
    with col2:
        if vote_stats['wins']:
            for provider, wins in vote_stats['wins'].items():
                st.metric(f"{provider.title()} Votes", wins)
    
    # Show updated ELO rankings
    st.markdown("### 🏆 Current ELO Rankings")
    leaderboard = st.session_state.benchmark_engine.get_leaderboard()
    
    if leaderboard:
        for entry in leaderboard:
            rank_emoji = ["🥇", "🥈", "🥉"][entry['rank']-1] if entry['rank'] <= 3 else f"{entry['rank']}."
            st.write(f"{rank_emoji} **{entry['provider'].title()}** - {entry['elo_rating']} ELO")
    
    st.balloons()  # Celebration animation!

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
    
    # Dataset source selection
    st.subheader("📚 Dataset Source")
    
    dataset_source = st.radio(
        "Choose dataset source:",
        ["Generate New Dataset", "Use Uploaded Samples", "Combine Both"],
        help="Select whether to use generated samples, uploaded samples, or both"
    )
    
    # Generate dataset button
    if st.button("📊 Prepare Test Dataset"):
        prepare_test_dataset(sample_count, selected_categories, selected_lengths, dataset_source)
    
    # Run benchmark button
    if st.button("🚀 Run Benchmark", type="primary"):
        if selected_providers and st.session_state.get("test_samples"):
            run_batch_benchmark(selected_providers, voice_config, iterations)
        else:
            st.error("Please generate a test dataset and select providers first.")

def prepare_test_dataset(sample_count: int, categories: List[str], lengths: List[str], dataset_source: str):
    """Prepare test dataset for batch benchmarking"""
    
    with st.spinner("Preparing test dataset..."):
        final_samples = []
        
        if dataset_source == "Generate New Dataset":
            # Generate new samples
            all_samples = st.session_state.dataset_generator.generate_dataset(sample_count * 2)
            
            # Filter samples
            for sample in all_samples:
                if (sample.category in categories and 
                    sample.length_category in lengths and 
                    len(final_samples) < sample_count):
                    final_samples.append(sample)
        
        elif dataset_source == "Use Uploaded Samples":
            # Use uploaded samples
            uploaded_samples = st.session_state.uploaded_samples
            
            if not uploaded_samples:
                st.error("No uploaded samples available. Please upload files first.")
                return
            
            # Filter uploaded samples
            for sample in uploaded_samples:
                if (sample.category in categories and 
                    sample.length_category in lengths and 
                    len(final_samples) < sample_count):
                    final_samples.append(sample)
        
        elif dataset_source == "Combine Both":
            # Combine generated and uploaded samples
            uploaded_samples = st.session_state.uploaded_samples
            
            # Use half from each source
            target_generated = sample_count // 2
            target_uploaded = sample_count - target_generated
            
            # Add generated samples
            all_samples = st.session_state.dataset_generator.generate_dataset(target_generated * 2)
            for sample in all_samples:
                if (sample.category in categories and 
                    sample.length_category in lengths and 
                    len([s for s in final_samples if s.id.startswith('sample_')]) < target_generated):
                    final_samples.append(sample)
            
            # Add uploaded samples
            for sample in uploaded_samples:
                if (sample.category in categories and 
                    sample.length_category in lengths and 
                    len([s for s in final_samples if not s.id.startswith('sample_')]) < target_uploaded):
                    final_samples.append(sample)
        
        st.session_state.test_samples = final_samples
    
    if final_samples:
        st.success(f"Prepared {len(final_samples)} test samples")
        
        # Display sample statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Samples", len(final_samples))
        
        with col2:
            avg_words = sum(s.word_count for s in final_samples) / len(final_samples)
            st.metric("Avg Words", f"{avg_words:.1f}")
        
        with col3:
            avg_complexity = sum(s.complexity_score for s in final_samples) / len(final_samples)
            st.metric("Avg Complexity", f"{avg_complexity:.2f}")
        
        with col4:
            # Count source types
            generated_count = len([s for s in final_samples if s.id.startswith('sample_')])
            uploaded_count = len(final_samples) - generated_count
            st.metric("Generated/Uploaded", f"{generated_count}/{uploaded_count}")
        
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
    
    samples = st.session_state.test_samples
    
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
    
    # Create summary table
    summary_data = []
    for provider, summary in summaries.items():
        summary_data.append({
            "Provider": provider.title(),
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
    
    # Enhanced leaderboard table
    st.subheader("📊 Current Rankings")
    
    df_leaderboard = pd.DataFrame(leaderboard)
    df_leaderboard["Provider"] = df_leaderboard["provider"].str.title()
    
    # Format the display columns
    display_df = df_leaderboard[[
        "rank", "Provider", "elo_rating", "games_played", 
        "wins", "losses", "win_rate"
    ]].copy()
    
    display_df.columns = [
        "Rank", "Provider", "ELO Rating", "Games", 
        "Wins", "Losses", "Win Rate %"
    ]
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Provider statistics
    st.subheader("📈 Provider Statistics")
    
    # Import database to get provider stats
    from database import db
    provider_stats = db.get_provider_stats()
    
    if provider_stats:
        stats_data = []
        for provider, stats in provider_stats.items():
            stats_data.append({
                "Provider": provider.title(),
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
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total User Votes", vote_stats['total_votes'])
            
            # Show vote wins per provider
            if vote_stats['wins']:
                vote_data = []
                for provider, wins in vote_stats['wins'].items():
                    losses = vote_stats['losses'].get(provider, 0)
                    total = wins + losses
                    win_rate = (wins / total * 100) if total > 0 else 0
                    
                    vote_data.append({
                        "Provider": provider.title(),
                        "User Votes Won": wins,
                        "User Win Rate %": f"{win_rate:.1f}%"
                    })
                
                vote_df = pd.DataFrame(vote_data)
                st.dataframe(vote_df, use_container_width=True, hide_index=True)
        
        with col2:
            # Recent votes
            if vote_stats['recent_votes']:
                st.write("**Recent Votes:**")
                for winner, loser, timestamp in vote_stats['recent_votes'][:5]:
                    st.write(f"🏆 {winner.title()} beat {loser.title()}")
    else:
        st.info("No user votes yet. Vote in Quick Test to start building preference data!")
    
    # Data persistence info
    st.info("💾 **Data Persistence**: All ELO ratings, statistics, and user votes are automatically saved and persist across sessions!")
    
    # ELO explanation
    with st.expander("ℹ️ About ELO Ratings & Persistence"):
        st.markdown("""
        **ELO Rating System:**
        - Similar to chess ratings, providers gain/lose points based on head-to-head comparisons
        - Lower latency wins in direct comparisons
        - Ratings start at 1500 and adjust based on performance
        - Higher ratings indicate consistently better performance
        
        **Data Persistence:**
        - All benchmark results are saved to a SQLite database
        - ELO ratings persist across app restarts and browser refreshes
        - Historical data accumulates over time for better accuracy
        - Statistics update automatically with each new test
        """)

def dataset_management_page():
    """Dataset management page"""
    
    st.header("📚 Dataset Management")
    st.markdown("Manage and analyze test datasets")
    
    # Dataset statistics
    if hasattr(st.session_state.dataset_generator, 'samples') and st.session_state.dataset_generator.samples:
        stats = st.session_state.dataset_generator.get_dataset_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Samples", stats["total_samples"])
        
        with col2:
            st.metric("Avg Words", f"{stats['word_count_stats']['avg']:.1f}")
        
        with col3:
            st.metric("Min Words", stats["word_count_stats"]["min"])
        
        with col4:
            st.metric("Max Words", stats["word_count_stats"]["max"])
        
        # Category distribution
        st.subheader("📊 Category Distribution")
        
        fig_categories = px.pie(
            values=list(stats["categories"].values()),
            names=list(stats["categories"].keys()),
            title="Samples by Category"
        )
        st.plotly_chart(fig_categories, use_container_width=True)
    
    # Dataset actions
    st.subheader("🔧 Dataset Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎲 Generate New Dataset"):
            with st.spinner("Generating dataset..."):
                st.session_state.dataset_generator.generate_dataset(100)
            st.success("New dataset generated!")
            st.rerun()
    
    with col2:
        if st.button("💾 Export Dataset"):
            filename = f"dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            st.session_state.dataset_generator.export_dataset(filename)
            st.success(f"Dataset exported to {filename}")

def upload_custom_text_page():
    """Upload custom text files page"""
    
    st.header("📁 Upload Custom Text")
    st.markdown("Upload your own text files to create custom benchmarking datasets")
    
    # File upload section
    st.subheader("📤 File Upload")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Choose text files",
            type=['txt', 'csv', 'json', 'md', 'py', 'js', 'html'],
            accept_multiple_files=True,
            help="Supported formats: TXT, CSV, JSON, Markdown, Python, JavaScript, HTML"
        )
        
        # Processing options
        st.subheader("🔧 Processing Options")
        
        auto_categorize = st.checkbox(
            "Auto-categorize content", 
            value=True,
            help="Automatically categorize text as technical, news, literature, or conversation"
        )
        
        max_samples = st.slider(
            "Maximum samples per file",
            min_value=10,
            max_value=200,
            value=50,
            help="Limit the number of text samples extracted from each file"
        )
        
        min_words = st.slider(
            "Minimum words per sample",
            min_value=5,
            max_value=50,
            value=10,
            help="Skip text samples with fewer words than this"
        )
    
    with col2:
        st.subheader("ℹ️ Upload Guidelines")
        
        st.markdown("""
        **Supported File Types:**
        - **TXT**: Plain text files
        - **CSV**: Text data in columns
        - **JSON**: String values from JSON
        - **MD**: Markdown content
        - **PY/JS**: Comments and strings
        - **HTML**: Text content from tags
        
        **Best Practices:**
        - Use files with diverse content
        - Include various text lengths
        - Ensure text is readable and meaningful
        - Avoid files with mostly code/data
        """)
        
        if st.session_state.uploaded_samples:
            st.success(f"✅ {len(st.session_state.uploaded_samples)} samples ready")
    
    # Process uploaded files
    if uploaded_files:
        if st.button("🔄 Process Files", type="primary"):
            process_uploaded_files(uploaded_files, auto_categorize, max_samples, min_words)
    
    # Display processed samples
    if st.session_state.uploaded_samples:
        display_uploaded_samples()
    
    # Manual text input section
    st.divider()
    st.subheader("✍️ Manual Text Input")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        manual_text = st.text_area(
            "Enter custom text:",
            height=150,
            placeholder="Paste your text here or enter multiple lines...",
            help="Enter text directly. Each line will be treated as a separate sample."
        )
        
        if manual_text:
            manual_category = st.selectbox(
                "Category for manual text:",
                ["uploaded", "technical", "news", "literature", "conversation", "narrative"]
            )
    
    with col2:
        st.markdown("""
        **Manual Input Tips:**
        - Each line becomes a sample
        - Minimum 10 words per line
        - Mix different text types
        - Use realistic content
        """)
    
    if manual_text and st.button("➕ Add Manual Text"):
        add_manual_text(manual_text, manual_category, min_words)

def process_uploaded_files(uploaded_files, auto_categorize: bool, max_samples: int, min_words: int):
    """Process uploaded files and extract text samples"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_samples = []
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing {uploaded_file.name}...")
        
        try:
            # Read file content
            file_content = uploaded_file.read()
            
            # Parse the file
            parsed_texts = st.session_state.text_parser.parse_uploaded_file(
                file_content, uploaded_file.name
            )
            
            # Filter by minimum words
            filtered_texts = [
                pt for pt in parsed_texts 
                if len(pt.content.split()) >= min_words
            ]
            
            # Limit samples per file
            if len(filtered_texts) > max_samples:
                filtered_texts = filtered_texts[:max_samples]
            
            # Convert to test samples
            samples = st.session_state.text_parser.create_test_samples_from_parsed(
                filtered_texts, auto_categorize
            )
            
            # Update sample IDs to include file info
            for j, sample in enumerate(samples):
                sample.id = f"upload_{uploaded_file.name}_{j+1:03d}"
            
            all_samples.extend(samples)
            
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    # Store samples
    st.session_state.uploaded_samples = all_samples
    
    status_text.text("Processing completed!")
    
    if all_samples:
        st.success(f"✅ Extracted {len(all_samples)} text samples from {len(uploaded_files)} files")
        
        # Show summary statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Samples", len(all_samples))
        
        with col2:
            avg_words = sum(s.word_count for s in all_samples) / len(all_samples)
            st.metric("Avg Words", f"{avg_words:.1f}")
        
        with col3:
            categories = set(s.category for s in all_samples)
            st.metric("Categories", len(categories))
        
        with col4:
            avg_complexity = sum(s.complexity_score for s in all_samples) / len(all_samples)
            st.metric("Avg Complexity", f"{avg_complexity:.2f}")
    else:
        st.warning("No text samples could be extracted from the uploaded files.")

def add_manual_text(text: str, category: str, min_words: int):
    """Add manually entered text as samples"""
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    new_samples = []
    
    for i, line in enumerate(lines):
        if len(line.split()) >= min_words:
            # Validate with security checks
            valid, error_msg = session_manager.validate_request(line)
            if valid:
                word_count = len(line.split())
                
                # Determine length category
                if word_count <= 30:
                    length_category = "short"
                elif word_count <= 80:
                    length_category = "medium"
                elif word_count <= 150:
                    length_category = "long"
                else:
                    length_category = "very_long"
                
                # Calculate complexity
                complexity = st.session_state.text_parser._calculate_complexity_score(line)
                
                sample = TestSample(
                    id=f"manual_{len(st.session_state.uploaded_samples) + i + 1:03d}",
                    text=line,
                    word_count=word_count,
                    category=category,
                    length_category=length_category,
                    complexity_score=complexity
                )
                
                new_samples.append(sample)
            else:
                st.warning(f"Skipped line due to validation error: {error_msg}")
    
    if new_samples:
        st.session_state.uploaded_samples.extend(new_samples)
        st.success(f"✅ Added {len(new_samples)} text samples")
    else:
        st.warning("No valid text samples could be created from the input.")

def display_uploaded_samples():
    """Display uploaded samples with management options"""
    
    st.subheader("📋 Uploaded Samples")
    
    samples = st.session_state.uploaded_samples
    
    if not samples:
        st.info("No uploaded samples available.")
        return
    
    # Sample management controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Clear All Samples"):
            st.session_state.uploaded_samples = []
            st.success("All samples cleared!")
            st.rerun()
    
    with col2:
        if st.button("🚀 Use for Benchmark"):
            # Add uploaded samples to the main test samples
            if not hasattr(st.session_state, 'test_samples'):
                st.session_state.test_samples = []
            
            st.session_state.test_samples.extend(samples)
            st.success(f"Added {len(samples)} samples to benchmark dataset!")
    
    with col3:
        if st.button("💾 Export Samples"):
            # Export as JSON
            filename = f"uploaded_samples_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            st.session_state.dataset_generator.samples = samples
            st.session_state.dataset_generator.export_dataset(filename)
            st.success(f"Exported to {filename}")
    
    # Display sample table
    st.subheader("📊 Sample Preview")
    
    # Create preview data
    preview_data = []
    for i, sample in enumerate(samples[:20]):  # Show first 20
        preview_data.append({
            "ID": sample.id,
            "Text Preview": sample.text[:80] + "..." if len(sample.text) > 80 else sample.text,
            "Words": sample.word_count,
            "Category": sample.category,
            "Length": sample.length_category,
            "Complexity": f"{sample.complexity_score:.2f}"
        })
    
    df = pd.DataFrame(preview_data)
    st.dataframe(df, use_container_width=True)
    
    if len(samples) > 20:
        st.caption(f"Showing first 20 of {len(samples)} samples")
    
    # Category distribution
    col1, col2 = st.columns(2)
    
    with col1:
        category_counts = {}
        for sample in samples:
            category_counts[sample.category] = category_counts.get(sample.category, 0) + 1
        
        if category_counts:
            fig_categories = px.pie(
                values=list(category_counts.values()),
                names=list(category_counts.keys()),
                title="Category Distribution"
            )
            st.plotly_chart(fig_categories, use_container_width=True)
    
    with col2:
        length_counts = {}
        for sample in samples:
            length_counts[sample.length_category] = length_counts.get(sample.length_category, 0) + 1
        
        if length_counts:
            fig_lengths = px.bar(
                x=list(length_counts.keys()),
                y=list(length_counts.values()),
                title="Length Distribution"
            )
            st.plotly_chart(fig_lengths, use_container_width=True)

def export_results_page():
    """Export results page"""
    
    st.header("📤 Export Results")
    st.markdown("Export benchmark results in various formats")
    
    if not st.session_state.results:
        st.info("No results available for export. Run some benchmarks first.")
        return
    
    # Initialize export manager
    export_manager = ExportManager()
    
    # Export options
    st.subheader("🔧 Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        export_formats = st.multiselect(
            "Select export formats:",
            ["JSON", "CSV", "Excel", "Comprehensive Report"],
            default=["JSON", "CSV"]
        )
        
        include_summary = st.checkbox("Include summary statistics", value=True)
        include_leaderboard = st.checkbox("Include ELO leaderboard", value=True)
    
    with col2:
        # Filter options
        st.write("**Filter Options:**")
        
        providers = list(set(r.provider for r in st.session_state.results))
        selected_providers = st.multiselect("Providers:", providers, default=providers)
        
        success_only = st.checkbox("Successful results only", value=False)
    
    # Filter results
    filtered_results = st.session_state.results
    
    if selected_providers:
        filtered_results = [r for r in filtered_results if r.provider in selected_providers]
    
    if success_only:
        filtered_results = [r for r in filtered_results if r.success]
    
    st.info(f"Exporting {len(filtered_results)} results")
    
    # Export buttons
    st.subheader("📁 Export Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Export Individual Files"):
            if filtered_results:
                files_created = []
                
                if "JSON" in export_formats:
                    json_file = export_manager.export_results_json(filtered_results)
                    files_created.append(json_file)
                
                if "CSV" in export_formats:
                    csv_file = export_manager.export_results_csv(filtered_results)
                    files_created.append(csv_file)
                
                if "Excel" in export_formats and include_summary:
                    summaries = st.session_state.benchmark_engine.calculate_summary_stats(filtered_results)
                    leaderboard = st.session_state.benchmark_engine.get_leaderboard()
                    excel_file = export_manager.export_excel_workbook(filtered_results, summaries, leaderboard)
                    files_created.append(excel_file)
                
                if "Comprehensive Report" in export_formats and include_summary:
                    summaries = st.session_state.benchmark_engine.calculate_summary_stats(filtered_results)
                    leaderboard = st.session_state.benchmark_engine.get_leaderboard()
                    report_file = export_manager.export_summary_report(filtered_results, summaries, leaderboard)
                    files_created.append(report_file)
                
                st.success(f"✅ Exported {len(files_created)} files: {', '.join(files_created)}")
    
    with col2:
        if st.button("📦 Create Export Package"):
            if filtered_results:
                summaries = st.session_state.benchmark_engine.calculate_summary_stats(filtered_results)
                leaderboard = st.session_state.benchmark_engine.get_leaderboard()
                
                format_mapping = {
                    "JSON": "json",
                    "CSV": "csv", 
                    "Excel": "excel",
                    "Comprehensive Report": "report"
                }
                
                include_formats = [format_mapping[fmt] for fmt in export_formats if fmt in format_mapping]
                
                package_file = export_manager.create_export_package(
                    filtered_results, summaries, leaderboard, include_formats
                )
                
                st.success(f"✅ Created export package: {package_file}")
    
    with col3:
        if st.button("📊 Preview Export Data"):
            if filtered_results:
                st.subheader("📋 Export Preview")
                
                # Show sample data
                df = pd.DataFrame([{
                    "Provider": r.provider,
                    "Success": r.success,
                    "Latency (ms)": r.latency_ms,
                    "File Size (KB)": r.file_size_bytes / 1024,
                    "Timestamp": r.timestamp
                } for r in filtered_results[:10]])
                
                st.dataframe(df, use_container_width=True)
                
                if len(filtered_results) > 10:
                    st.caption(f"Showing first 10 of {len(filtered_results)} results")

def security_page():
    """Security configuration and monitoring page"""
    
    st.header("🔒 Security")
    st.markdown("Security configuration and monitoring dashboard")
    
    # Security dashboard
    create_security_dashboard()
    
    # API Key Management
    st.subheader("🔑 API Key Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Murf AI API Key:**")
        murf_key = secure_api_key_input("Murf AI", "MURF_API_KEY")
        
        if murf_key:
            # Test the key
            if st.button("🧪 Test Murf Key"):
                try:
                    provider = TTSProviderFactory.create_provider("murf")
                    st.success("✅ Murf AI API key is valid")
                except Exception as e:
                    st.error(f"❌ Murf AI API key test failed: {str(e)}")
    
    with col2:
        st.write("**Deepgram API Key:**")
        deepgram_key = secure_api_key_input("Deepgram", "DEEPGRAM_API_KEY")
        
        if deepgram_key:
            # Test the key
            if st.button("🧪 Test Deepgram Key"):
                try:
                    provider = TTSProviderFactory.create_provider("deepgram")
                    st.success("✅ Deepgram API key is valid")
                except Exception as e:
                    st.error(f"❌ Deepgram API key test failed: {str(e)}")
    
    # Rate Limiting Status
    st.subheader("⚡ Rate Limiting")
    
    session_id = session_manager.get_session_id()
    st.info(f"Current session: {session_id[:8]}...")
    
    # Show current rate limit status
    allowed, error_msg = session_manager.check_rate_limit()
    if allowed:
        st.success("✅ Rate limit: OK")
    else:
        st.warning(f"⚠️ Rate limit: {error_msg}")
    
    # Security recommendations
    st.subheader("💡 Security Recommendations")
    
    recommendations = [
        "Use environment variables for API keys in production",
        "Enable HTTPS for all deployments", 
        "Monitor API usage and set up alerts",
        "Regularly rotate API keys",
        "Implement proper access controls",
        "Keep dependencies updated",
        "Use rate limiting to prevent abuse",
        "Validate all user inputs",
        "Log security events for monitoring"
    ]
    
    for i, rec in enumerate(recommendations, 1):
        st.write(f"{i}. {rec}")

if __name__ == "__main__":
    main()