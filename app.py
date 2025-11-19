"""
TTS Benchmarking Tool - Streamlit Application
"""
import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
import json
import base64
import time
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
from database import BenchmarkDatabase

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

# Initialize database
db = BenchmarkDatabase()

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
    
    # Sidebar for navigation and configuration
    with st.sidebar:
        # Navigation - moved to top
        st.subheader("Navigator")
        
        pages = ["Leaderboard", "Blind Test"]
        
        # Create navbar-style buttons
        for i, page_name in enumerate(pages):
            if st.button(page_name, key=f"nav_{page_name}", use_container_width=True):
                st.session_state.current_page = page_name
                st.rerun()
        
        # Set the current page - handle both old and new navigation systems
        if "navigate_to" in st.session_state and st.session_state.navigate_to:
            page = st.session_state.navigate_to
            st.session_state.navigate_to = None  # Clear after using
        else:
            page = st.session_state.get("current_page", "Leaderboard")
        
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
                    st.success(f"{provider_name}")
                else:
                    st.error(f"{provider_name}")
        else:
            st.error("No API keys configured")
            st.markdown("**Set at least one API key:**")
            for provider_id, status in config_status["providers"].items():
                if not status["configured"]:
                    env_var = TTS_PROVIDERS[provider_id].api_key_env
                    provider_name = TTS_PROVIDERS[provider_id].name
                    st.code(f"export {env_var}=your_api_key_here")
                    st.caption(f"For {provider_name}")
        
        st.divider()
    
    # Main content based on selected page
    if page == "Blind Test":
        blind_test_page()
    elif page == "Leaderboard":
        leaderboard_page()
    else:
        leaderboard_page()  # Default to leaderboard 

def blind_test_page():
    """Blind test page for unbiased audio quality comparison"""
    
    st.header("Blind Test")
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
    
    if len(configured_providers) < 1:
        st.warning("WARNING: Blind test requires at least 1 configured provider. Please configure API keys.")
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
    st.subheader("Test Setup")
    
    # Sample texts for each language
    sample_texts = {
        "Tamil": "வணக்கம். இது பேச்சு தொகுப்பு தரத்தின் ஒரு சோதனை. குரல் தெளிவாக உள்ளதா?",
        "Telugu": "నమస్కారం. ఇది స్పీచ్ సింథసిస్ నాణ్యత యొక్క పరీక్ష. వాయిస్ స్పష్టంగా ఉందా?",
        "Kannada": "ನಮಸ್ಕಾರ. ಇದು ಭಾಷಣ ಸಂಶ್ಲೇಷಣೆ ಗುಣಮಟ್ಟದ ಪರೀಕ್ಷೆ. ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿದೆಯೇ?",
        "Hindi": "नमस्ते। यह वाक् संश्लेषण गुणवत्ता का एक परीक्षण है। आवाज साफ है?",
        "English": "Hello. This is a test of speech synthesis quality. Is the voice clear?"
    }
    
    # Language selection with auto-update
    language = st.selectbox(
        "Select Language:",
        ["Tamil", "Telugu", "Kannada", "English", "Hindi"],
        key="language_selector"
    )
    
    # Get sample text for selected language
    default_text = sample_texts.get(language, sample_texts["Tamil"])
    
    # Initialize or update text based on language change
    if "last_language" not in st.session_state:
        st.session_state.last_language = language
        st.session_state.text_for_display = default_text
    elif st.session_state.last_language != language:
        # Language changed - update text
        st.session_state.last_language = language
        st.session_state.text_for_display = default_text
    
    st.write("")  # Add spacing
    
    # Text input with multilingual support - removed key to allow value changes
    text_input = st.text_area(
        "Enter text to test:",
        value=st.session_state.text_for_display,
        height=120,
        max_chars=5000
    )
    
    # Update session state when user types
    st.session_state.text_for_display = text_input
    
    char_count = len(text_input)
    st.caption(f"Characters: {char_count}/5000")
    
    st.write("")  # Add spacing
    
    # Generate blind test samples
    if st.button("Generate Blind Test", type="primary"):
        if text_input and len(configured_providers) >= 1:
            # Validate input
            valid, error_msg = session_manager.validate_request(text_input)
            if valid:
                generate_blind_test_samples(text_input, configured_providers, language)
            else:
                st.error(f"ERROR: {error_msg}")
        else:
            st.error("Please enter text and ensure at least 1 provider is configured.")
    
    # Display blind test samples if available
    if st.session_state.blind_test_samples:
        display_blind_test_samples()

def generate_blind_test_samples(text: str, providers: List[str], language: str):
    """Generate audio samples for blind testing"""
    
    import random
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    
    # Map language to appropriate voices and providers
    language_voice_map = {
        "Tamil": {
            "murf_falcon_oct23": ["Alicia", "Murali"],
            "elevenlabs": ["Rachel"]  # English voice, but will try
        },
        "Telugu": {
            "murf_falcon_oct23": ["Josie", "Ronnie"],
            "elevenlabs": ["Rachel"]  # English voice, but will try
        },
        "Kannada": {
            "murf_falcon_oct23": ["Julia", "Maverick", "Rajesh"],
            "elevenlabs": ["Rachel"]  # English voice, but will try
        },
        "English": {
            "murf_falcon_oct23": ["Alicia", "Murali"],
            "elevenlabs": ["Rachel", "Domi", "Bella"]
        },
        "Hindi": {
            "murf_falcon_oct23": ["Alicia", "Murali"],
            "elevenlabs": ["Rachel"]  # English voice, but will try
        }
    }
    
    async def test_provider(provider_id: str):
        try:
            provider = TTSProviderFactory.create_provider(provider_id)
            provider_name = TTS_PROVIDERS[provider_id].name
            
            # Check if this provider has voices mapped for the selected language
            lang_providers = language_voice_map.get(language, {})
            if provider_id not in lang_providers:
                # Provider not in map, skip
                return None, provider_name, True  # True = intentionally skipped
            
            # Select appropriate voice based on language
            preferred_voices = lang_providers[provider_id]
            available_voices = TTS_PROVIDERS[provider_id].supported_voices
            
            # Find a voice that matches the language preference and is available
            voice = None
            for pref_voice in preferred_voices:
                if pref_voice in available_voices:
                    voice = pref_voice
                    break
            
            # Fallback to first available voice if no match
            if not voice:
                voice = available_voices[0] if available_voices else "default"
            
            status_text.text(f"Generating {provider_name} with voice {voice}...")
            
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
            return result, provider_name, False
            
        except Exception as e:
            provider_name = TTS_PROVIDERS.get(provider_id, {}).name if provider_id in TTS_PROVIDERS else provider_id
            st.warning(f"WARNING: {provider_name} failed - {str(e)}")
            return None, provider_name, False
    
    # Run tests
    for i, provider_id in enumerate(providers):
        result_data = asyncio.run(test_provider(provider_id))
        result, provider_name, skipped = result_data
        
        if skipped:
            # Provider doesn't support this language, skip silently
            pass
        elif result and result.success:
            results.append(result)
            st.success(f"SUCCESS: {provider_name} generated audio")
        elif result:
            st.error(f"ERROR: {provider_name} failed - {result.error_message}")
        else:
            st.error(f"ERROR: {provider_name} failed to generate")
        
        progress_bar.progress((i + 1) / len(providers))
    
    status_text.text("Samples generated!")
    
    if len(results) < 1:
        st.error("ERROR: No successful samples generated. Please check your API keys and try again.")
        progress_bar.empty()
        status_text.empty()
        st.session_state.blind_test_samples = []
        return
    
    # Show info if only one provider succeeded
    if len(results) == 1:
        st.info("INFO: Only one provider generated audio successfully. For best blind testing, configure both providers.")
    
    # Randomize the order of samples
    random.shuffle(results)
    
    # Assign anonymous labels (A, B, C, etc.) - dynamically generate based on number of results
    labels = [chr(65 + i) for i in range(len(results))]  # Generates A, B, C, D, E, F, G, H, etc.
    for i, result in enumerate(results):
        result.blind_label = labels[i]
    
    # Store samples in session state
    st.session_state.blind_test_samples = results
    st.session_state.blind_test_voted = False
    st.session_state.blind_test_vote_choice = None
    
    st.success(f"SUCCESS: Generated {len(results)} blind test samples!")
    st.rerun()

def display_blind_test_samples():
    """Display blind test samples for voting"""
    
    samples = st.session_state.blind_test_samples
    
    if not st.session_state.blind_test_voted:
        # Voting phase - don't reveal providers
        st.subheader("Listen and Vote")
        st.markdown("**Listen to each sample and vote for the one with the best quality:**")
        
        # Display samples in rows of 4
        for i in range(0, len(samples), 4):
            cols = st.columns(4)
            for j, result in enumerate(samples[i:i+4]):
                with cols[j]:
                    st.markdown(f"### Sample {result.blind_label}")
                    
                    if result.audio_data:
                        # Custom audio player without download option in 3-dot menu
                        audio_base64 = base64.b64encode(result.audio_data).decode()
                        audio_html = f"""
                        <audio controls controlsList="nodownload" style="width: 100%;">
                            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
                        </audio>
                        """
                        st.markdown(audio_html, unsafe_allow_html=True)
                        st.caption(f"Sample {result.blind_label}")
                        
                        # Download button
                        st.download_button(
                            label="Download MP3",
                            data=result.audio_data,
                            file_name=f"sample_{result.blind_label}.mp3",
                            mime="audio/mpeg",
                            key=f"download_blind_{result.blind_label}_{i}_{j}"
                        )
        
        st.divider()
        
        # Voting section
        st.markdown("### Cast Your Vote")
        
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
            
            # Update ELO ratings - winner beats all others (but only count as one vote)
            # We'll update ELO ratings for all comparisons but only save one vote to database
            losers = [r for r in samples if r.blind_label != selected_label]
            if losers:
                # Update ELO ratings for all comparisons
                for loser_result in losers:
                    handle_blind_test_vote(winner_result, loser_result, save_vote=False)
                
                # Save only one vote to database
                handle_blind_test_vote(winner_result, losers[0], save_vote=True)
            
            st.rerun()
    
    else:
        # Results phase - reveal providers
        st.subheader("Results Revealed!")
        
        # Show which sample the user voted for
        voted_sample = next(r for r in samples if r.blind_label == st.session_state.blind_test_vote_choice)
        
        st.success(f"**You voted for Sample {st.session_state.blind_test_vote_choice}**")
        st.info(f"**Sample {st.session_state.blind_test_vote_choice} was generated by: {voted_sample.provider.title()} ({voted_sample.model_name})**")
        
        st.divider()
        
        # Show all samples with revealed providers
        st.subheader("All Samples Revealed")
        
        # Create comparison table
        comparison_data = []
        for result in sorted(samples, key=lambda r: r.blind_label):
            is_winner = result.blind_label == st.session_state.blind_test_vote_choice
            comparison_data.append({
                "Sample": result.blind_label,
                "Provider": result.provider.title(),
                "Model": result.model_name,
                "Location": get_location_display(result),
                "File Size (KB)": f"{result.file_size_bytes / 1024:.1f}",
                "Your Choice": "WINNER" if is_winner else ""
            })
        
        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Show audio samples with labels
        st.subheader("Listen Again (with provider names)")
        
        # Display audio players in rows of 4
        sorted_samples = sorted(samples, key=lambda r: r.blind_label)
        for i in range(0, len(sorted_samples), 4):
            cols = st.columns(4)
            for j, result in enumerate(sorted_samples[i:i+4]):
                with cols[j]:
                    is_winner = result.blind_label == st.session_state.blind_test_vote_choice
                    if is_winner:
                        st.markdown(f"### WINNER: Sample {result.blind_label}")
                    else:
                        st.markdown(f"### Sample {result.blind_label}")
                    
                    st.markdown(f"**{result.provider.title()}**")
                    st.caption(result.model_name)
                    
                    if result.audio_data:
                        # Custom audio player without download option in 3-dot menu
                        audio_base64 = base64.b64encode(result.audio_data).decode()
                        audio_html = f"""
                        <audio controls controlsList="nodownload" style="width: 100%;">
                            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
                        </audio>
                        """
                        st.markdown(audio_html, unsafe_allow_html=True)
                        st.caption(f"Size: {result.file_size_bytes/1024:.1f} KB")
                        
                        # Download button
                        st.download_button(
                            label="Download MP3",
                            data=result.audio_data,
                            file_name=f"{result.provider}_{result.blind_label}.mp3",
                            mime="audio/mpeg",
                            key=f"download_revealed_{result.blind_label}_{i}_{j}"
                        )
        
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
                st.session_state.current_page = "Leaderboard"
                st.rerun()

def handle_blind_test_vote(winner_result: BenchmarkResult, loser_result: BenchmarkResult, save_vote: bool = True):
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
        
        # Save the vote in database only if requested
        if save_vote:
            db.save_user_vote(
                winner_result.provider, 
                loser_result.provider, 
                winner_result.text[:100] + "..." if len(winner_result.text) > 100 else winner_result.text,
                session_id="blind_test_session"
            )
        
    except Exception as e:
        st.error(f"Error updating ratings: {e}")

def leaderboard_page():
    """ELO leaderboard page with persistent data"""
    
    st.header("Leaderboard")
    st.markdown("ELO-based rankings of TTS providers")
    
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
    
    # Leaderboard table
    st.subheader("Current Rankings")
    
    # Get current location for display
    current_location = geo_service.get_location_string()
    location_display = f"{geo_service.get_country_flag()} {current_location}"
    
    df_leaderboard = pd.DataFrame(leaderboard)
    df_leaderboard["Provider"] = df_leaderboard["provider"].str.title()
    
    # Add model names and location
    df_leaderboard["Model"] = df_leaderboard["provider"].apply(get_model_name)
    df_leaderboard["Location"] = location_display
    
    # Format the display columns (removed ELO, TTFB columns)
    display_df = df_leaderboard[[
        "rank", "Provider", "Model", "Location",
        "games_played", "wins", "losses", "win_rate"
    ]].copy()
    
    # Convert games_played to actual test count
    # Each blind test involves 2 providers, and each vote increments games_played for both
    # So we divide by 2 to get the actual number of tests
    display_df["Total Tests"] = (display_df["games_played"] / 2).astype(int)
    
    display_df = display_df[[
        "rank", "Provider", "Model", "Location",
        "Total Tests", "wins", "losses", "win_rate"
    ]].copy()
    
    display_df.columns = [
        "Rank", "Provider", "Model", "Location",
        "Total Tests", "Wins", "Losses", "Win Rate %"
    ]
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # User voting statistics
    st.subheader("User Voting Statistics")
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
        st.info("No user votes yet. Vote in Blind Test to start building preference data!")


if __name__ == "__main__":
    main()