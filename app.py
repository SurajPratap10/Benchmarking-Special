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
    
    # Track page navigation for sentence randomization
    if "previous_page" not in st.session_state:
        st.session_state.previous_page = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = page
    
    # Update page tracking
    if st.session_state.current_page != page:
        st.session_state.previous_page = st.session_state.current_page
        st.session_state.current_page = page
    
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
    
    # 30 sentences for each language
    language_sentences = {
        "Bengali": [
            "আপনি যে issue টা ফেস করছেন একটু detail এ বলবেন? আমি সঙ্গে সঙ্গে system এ check করছি।",
            "আপনার account verification এর জন্য আমাকে এক মিনিট দিন, details confirm করে আপনাকে update দিচ্ছি।",
            "আপনি যে error টা বলছেন যদি বারবার আসে, আমি একটা ticket raise করে technical team এ escalate করবো।",
            "আপনার payment status এখন pending দেখাচ্ছে; refresh করে দেখে আপনাকে exact তথ্য দিচ্ছি।",
            "এই feature এখনো সব users এর জন্য available না; আপনাকে early access দিতে পারি কি না দেখে নিচ্ছি।",
            "আপনার email এ যে link ছিল মনে হচ্ছে expired হয়েছে; আমি নতুন verification link এখনই পাঠাচ্ছি।",
            "আপনার order হয়তো delay হয়েছে; courier এর সঙ্গে কথা বলে latest tracking info জানাচ্ছি।",
            "আপনি যে mobile number দিয়েছেন সেটা আমাদের system এ match করছে না; কি আপনি recently update করেছেন?",
            "আপনার login issue troubleshoot করতে আমি quick reset করে দেখছি, আপনি confirm করবেন।",
            "call এ যে steps বুঝিয়েছি সেগুলো আমি email এও পাঠিয়ে দিচ্ছি reference এর জন্য।",
            "আমাদের নতুন plan এ আপনি বেশি storage, faster support আর dedicated manager এর মতো benefits পাবেন।",
            "Trial এর সময় যদি কোনো limitation ফেস করেন, আমি সেগুলো সাথে সাথে unlock করে দিতে পারবো।",
            "আমাদের product আপনার workflow এ কিভাবে fit হয় সেটা দেখানোর জন্য আমি personalized demo arrange করবো।",
            "আপনার use-case এর জন্য আমাদের premium features একদম perfect, especially automation tools।",
            "আপনার team বড় হলে, enterprise plan নিলে cost ও কম পড়ে।",
            "আমি আপনাকে একটা quote পাঠাচ্ছি যাতে আপনি পুরো pricing structure compare করতে পারেন।",
            "আমাদের dashboard এর reports দিয়ে আপনি daily performance track করতে পারবেন।",
            "চাইলে আপনার team এর জন্য onboarding session schedule করে দেব।",
            "decision নেয়ার আগে আমি আমাদের case studies আর customer success stories পাঠিয়ে দেব।",
            "আপনার requirement অনুযায়ী custom integration ও setup করা যাবে—interest থাকলে বলুন।",
            "price নিয়ে আপনার concern ঠিক, কিন্তু আমাদের নতুন plan এর value অনেক বেশি।",
            "এই feature আপনার daily operations কমপক্ষে ৩০% faster করবে—তাই অনেক customer এটা prefer করে।",
            "আপনি ভাবার সময় নিন, কিন্তু আমি যে discount বলেছি সেটা পরের Friday পর্যন্ত available।",
            "আপনার team ইতিমধ্যে আমাদের platform partly use করছে; full migration করলে consistency বাড়বে।",
            "আমি পাঠানো proposal দেখার পর যদি কোনও doubt থাকে, আমি call এ clear করে দেব।",
            "চাইলে competitors এর সাথে আমাদের comparison ও পাঠিয়ে দেব।",
            "আপনি যে সমস্যা বলেছেন সেটা আমাদের engineering team already fix করছে; আমি update দেব।",
            "আপনি এখন upgrade করলে support team থেকে priority assistance পাবেন।",
            "আপনার দেওয়া feedback খুব useful; আমি সেটা product team এ পাঠিয়েছি।",
            "আপনার সুবিধামত আমি follow-up call schedule করবো, কোন দিন ভালো বলুন।"
        ],
        "Tamil": [
            "நீங்கள் face பண்ணும் issue பற்றி கொஞ்சம் detail ஆக சொல்ல முடியுமா? நான் உடனே system ல check பண்ணுறேன்।",
            "உங்கள் account verification காக ஒரு minute குடுங்க, details confirm பண்ணி update பண்றேன்।",
            "நீங்க சொன்ன error repeat ஆகுறது நெனச்சா, நான் ஒரு ticket raise பண்ணி technical team கிட்ட escalate பண்ணுறேன்।",
            "உங்கள் payment status இப்ப pending னு காட்டுது; refresh பண்ணி பார்த்து exact update சொல்றேன்।",
            "இந்த feature இன்னும் எல்லா users கும் available இல்ல; உங்களுக்கு early access குடுக்கலாமா னு check பண்ணுறேன்।",
            "நீங்கள் பெற்ற email ல இருக்குற link expired ஆயிருச்சு போல; புதிய verification link உடனே அனுப்புறேன்।",
            "உங்கள் order delay ஆயிருக்கு போல; courier கிட்ட பேசிட்டு latest tracking info சொல்றேன்।",
            "நீங்க கொடுத்த mobile number system ல match ஆகலை; recently update பண்ணிங்களா?",
            "உங்கள் login issue troubleshoot பண்ண quick reset try பண்ணுறேன், நீங்க confirm பண்ணுங்க।",
            "call ல explain பண்ணி கொடுத்த steps நா இப்ப email லும் share பண்றேன் reference காக।",
            "நம்ம புதிய plan ல நீங்க அதிக storage, faster support, dedicated manager மாதிரி benefits பெறுவீங்க।",
            "Trial time ல எந்த limitations இருந்தாலும், நா அதை உடனே unlock பண்ணித் தருறேன்।",
            "நம்ம product உங்க workflow க்கு எப்படி suit ஆகும் னு காட்ட நான் personalized demo arrange பண்ணுவேன்।",
            "நீங்க சொன்ன use-case க்கு நம்ம premium features ரொம்ப perfect, especially automation tools।",
            "உங்க team பெருசா இருந்தா, enterprise plan எடுத்தா cost கம்மி ஆகும்।",
            "நா உங்களுக்கு ஒரு quote send பண்ணுறேன்; அதுல pricing structure easy ஆக compare பண்ணலாம்।",
            "நம்ம dashboard ல இருக்குற reports மூலம் நீங்க தினமும் performance track பண்ணலாம்।",
            "வேண்டும்னா உங்க team காக onboarding sessionயும் schedule பண்ணி வைக்கிறேன்।",
            "decision எடுக்கும் முன்னாடி நா நம்ம case studies மற்றும் success stories அனுப்புறேன்।",
            "உங்க requirement க்கு custom integration கூட setup பண்ணிக்கொடுப்போம்—interest இருந்தா சொல்லுங்க।",
            "price பற்றிய உங்க concern சரிதான்; ஆனா நம்ம புதிய plan ல கிடைக்கும் value அதிகம்।",
            "இந்த feature உங்க daily operations ல குறைந்தது 30% speed கூடும்; அதனால தான் customer க்கள் இதை prefer பண்றாங்க।",
            "நீங்க யோசிக்க time எடுக்கலாம்; ஆனா நா சொன்ன discount அடுத்த Friday வரை தான் available।",
            "உங்க team already நம்ம platformஐ partly use பண்ணிட்டு இருக்காங்க; full migration consistency அதிகப்படுத்தும்।",
            "நா அனுப்பின proposal பாத்துட்டு doubts இருந்தா call ல clear பண்ணிடுறேன்।",
            "நீங்க விரும்பினா competitors உடன் நம்ம comparisonயும் அனுப்புறேன்।",
            "நீங்க சொன்ன issue வை நம்ம engineering team already fix பண்ணிட்டு இருக்கு; update உடனே சொல்றேன்।",
            "இப்ப upgrade பண்ணீங்கனா, நம்ம support teamலிருந்து priority assistance கிடைக்கும்।",
            "நீங்க கொடுத்த feedback ரொம்ப useful; அதை நா product team கிட்ட forward பண்ணிட்டேன்।",
            "உங்க convenience க்கு ஏற்ப follow-up call schedule பண்ணுறேன்; எந்த நாள் நல்லது சொல்லுங்க।"
        ],
        "Telugu": [
            "మీకు ఎదురవుతున్న issue గురించీ ఇంకొంచెం detail గా చెప్పగలరా? నేను వెంటనే system లో check చేస్తాను।",
            "మీ account verification కోసం నాకు ఒక minute time ఇవ్వండి, details confirm చేసుకొని మీకు update ఇస్తాను।",
            "మీరు చెప్పిన error regularly వస్తుంటే, నేను ఒక ticket raise చేసి మా technical team కి escalate చేస్తాను।",
            "మీ payment status ఇప్పుడు pending గా కనిపిస్తోంది; నేను refresh చేసి చూశాక మీకు exact సమాచారం ఇస్తా।",
            "ఈ feature ప్రస్తుతం అన్ని users కి available లేదు, కానీ మీకు early access ఇవ్వగలమో నేను check చేస్తాను।",
            "మీకు వచ్చిన email లో ఉన్న link expired అయ్యిందనిపిస్తోంది; నేను కొత్త verification link వెంటనే పంపుతాను।",
            "మీ order delay అయ్యింది అనిపిస్తోంది; courier తో మాట్లాడి latest tracking info వెంటనే చెప్తా।",
            "మీరు ఇచ్చిన mobile number మా system లో match కావడం లేదు; మీరు recent గా update చేశారా?",
            "మీ login సమస్యను troubleshoot చేయడానికి నేను ఒక quick reset try చేస్తాను, మీరు confirm చెయ్యండి।",
            "మీకు call లో explain చేసిన steps ని నేను ఇప్పుడు email లో కూడా share చేస్తాను for reference।",
            "మా కొత్త plan లో మీరు ఎక్కువ storage, faster support, మరియు dedicated manager వంటి benefits పొందగలరు।",
            "మీరు trial సమయంలో ఏవైనా limitations ఫేస్ చేస్తే, నేను వాటిని వెంటనే unlock చేయగలను।",
            "మా product మీ workflow కి ఎలా సరిపోతుందో చూపడానికి నేను ఒక personalized demo arrange చేస్తాను।",
            "మీరు చెప్పిన use-case కి మా premium features perfect గా suit అవుతాయి, especially automation tools।",
            "మీరు పెద్ద team use చేస్తుంటే, మా enterprise plan తీసుకుంటే మీకు cost కూడా save అవుతుంది।",
            "నేను మీకు ఒక quote share చేస్తాను, దాంతో మీరు complete pricing structure easy గా compare చేయగలరు।",
            "మా dashboard లో ఉన్న reports help తో మీరు ప్రతి రోజూ performance track చేయగలరు।",
            "మీకు కావాలంటే, నేను మీ team కోసం ఒక onboarding session కూడా schedule చేస్తాను।",
            "మీరు decide చేసే ముందు, మా case studies మరియు customer success stories కూడా పంపిస్తాను।",
            "మీరు చెప్పిన requirements కి custom integration కూడా setup చేయగలం, మీకు interest ఉంటే చెపండి।",
            "మీరు price గురించి concern చెప్పినది valid; కానీ మా కొత్త plan లో వచ్చే value చాలా ఎక్కువగా ఉంటుంది।",
            "ఈ feature మీ daily operations ని at least 30% faster చేస్తుంది, అందుకే చాలా customers దీన్ని prefer చేస్తున్నారు।",
            "మీరు ఆలోచించడానికి time తీసుకోండి, కానీ నేను చెప్పిన discount వచ్చే Friday వరకు మాత్రమే available।",
            "మీ team ఇప్పటికే మా platform ని partially use చేస్తోంది; full migration మీకు మరింత consistency ఇస్తుంది।",
            "నేను మీకు పంపిన proposal చూశాక ఏవైనా doubts ఉంటే, నేను call లో clarify చేస్తాను।",
            "మీకు కావాలంటే, నేను మీకు competitors తో మా comparison కూడా పంపగలను।",
            "మీరు చెప్పిన సమస్యను మా engineering team already fix చేస్తోంది; మీకు వెంటనే update ఇస్తాను।",
            "ఇప్పుడు మీరు upgrade చేస్తే, మా support team నుండి priority assistance కూడా పొందగలరు।",
            "మీరు ఇచ్చిన feedback చాలా useful; నేను దాన్ని మా product team కి forward చేశాను।",
            "మీ convenience కి అనుగుణంగా నేను ఒక follow-up call schedule చేస్తాను, ఏ రోజు బెటర్ చెప్పండి।"
        ],
        "Kannada": [
            "ನೀವು face ಮಾಡ್ತಿರುವ issue ಕುರಿತು ಸ್ವಲ್ಪ detail ಗೆ ಹೇಳ್ತೀರಾ? ನಾನು ಈಗಲೇ system ನಲ್ಲಿ check ಮಾಡ್ತೀನಿ।",
            "ನಿಮ್ಮ account verification ಗಾಗಿ ಒಂದು minute ಕೊಡಿ, details confirm ಮಾಡಿ update ಕೊಡ್ತೀನಿ।",
            "ನೀವು ಹೇಳಿದ error frequent ಆಗಿ ಬರುತ್ತಿದ್ರೆ, ನಾನು ಒಂದು ticket raise ಮಾಡಿ technical team ಗೆ escalate ಮಾಡ್ತೀನಿ।",
            "ನಿಮ್ಮ payment status ಈಗ pending ಅಂತ ತೋರಿಸ್ತಾ ಇದೆ; refresh ಮಾಡಿ exact ಮಾಹಿತಿಯನ್ನು ಹೇಳ್ತೀನಿ।",
            "ಈ feature ಇನ್ನೂ ಎಲ್ಲ users ಗೆ available ಇಲ್ಲ; ನಿಮಗೆ early access ಕೊಡಬಹುದಾ ಅಂತ check ಮಾಡ್ತೀನಿ।",
            "ನಿಮ್ಮ email ನಲ್ಲಿ ಬಂದ link expired ಆಗಿದೆ ಅನಿಸುತ್ತಿದೆ; ಹೊಸ verification link ಈಗಲೇ ಕಳುಸ್ತೀನಿ।",
            "ನಿಮ್ಮ order delay ಆಗಿದೆ ಅನಿಸ್ತಿದೆ; courier ಜೊತೆಗೆ ಮಾತಾಡಿ tracking info ಕೊಡ್ತೀನಿ।",
            "ನೀವು ಕೊಟ್ಟ mobile number system ನಲ್ಲಿ match ಆಗ್ತಿಲ್ಲ; recently update ಮಾಡಿದ್ದೀರಾ?",
            "ನಿಮ್ಮ login issue troubleshoot ಮಾಡಲು ನಾನು quick reset try ಮಾಡ್ತೀನಿ, ನೀವು confirm ಮಾಡಿ।",
            "call ನಲ್ಲಿ explain ಮಾಡಿದ steps ನ್ನು ಈಗ email ನಲ್ಲಿ ಕೂಡ share ಮಾಡ್ತೀನಿ।",
            "ನಮ್ಮ ಹೊಸ plan ನಲ್ಲಿ ನಿಮಗೆ ಹೆಚ್ಚು storage, faster support ಮತ್ತು dedicated manager benefits ಸಿಗುತ್ತವೆ।",
            "Trial ಸಮಯದಲ್ಲಿ ಯಾವುದಾದರೂ limitations ಬಂದ್ರೆ, ನಾನು ಕೂಡಲೇ unlock ಮಾಡ್ತೀನಿ।",
            "ನಮ್ಮ product ನಿಮ್ಮ workflow ಗೆ ಹೇಗೆ suit ಆಗುತ್ತದೋ ಎನ್ನೋದು ತೋರಿಸಲು personalized demo ಕೊಡ್ತೀನಿ।",
            "ನಿಮ್ಮ use-case ಗೆ ನಮ್ಮ premium features ತುಂಬಾ perfect, especially automation tools।",
            "ನಿಮ್ಮ team ದೊಡ್ಡದಿದ್ದರೆ, enterprise plan ತೆಗೆದುಕೊಂಡರೆ cost ಕೂಡ save ಆಗುತ್ತದೆ।",
            "ನಿಮಗೆ ಒಂದು quote ಕಳುಸ್ತೀನಿ, pricing structure ನೀವೇ compare ಮಾಡಬಹುದು।",
            "ನಮ್ಮ dashboard ನಲ್ಲಿ ಇರುವ reports ಮೂಲಕ ನೀವು daily performance track ಮಾಡಬಹುದು।",
            "ಬೇಕಾದರೆ ನಿಮ್ಮ team ಗಾಗಿ onboarding session ಕೂಡ schedule ಮಾಡ್ತೀನಿ।",
            "decision ಮಾಡುವ ಮೊದಲು ನಾನು ನಮ್ಮ case studies ಹಾಗೂ success stories ಕಳುಸ್ತೀನಿ।",
            "ನಿಮ್ಮ requirements ಗೆ custom integration ಕೂಡ setup ಮಾಡ್ತೀನಿ—interest ಇದ್ದರೆ ಹೇಳಿ।",
            "price ಬಗ್ಗೆ ನಿಮ್ಮ concern ಸರಿ; ಆದರೆ ನಮ್ಮ ಹೊಸ plan ನ value ತುಂಬಾ ಹೆಚ್ಚಿನದು।",
            "ಈ feature ನಿಮ್ಮ daily operations ಅನ್ನು ಕನಿಷ್ಠ 30% faster ಮಾಡುತ್ತದೆ, ಅದ್ದರಿಂದ customers ಇದನ್ನು prefer ಮಾಡ್ತಾರೆ।",
            "ನೀವು ಯೋಚಿಸಲು ಸಮಯ ತೆಗೊಳ್ಳಿ, ಆದರೆ ನಾನು ಹೇಳಿದ discount ಮುಂದಿನ Friday ತನಕ ಮಾತ್ರ available।",
            "ನಿಮ್ಮ team already ನಮ್ಮ platform ನ್ನು partly use ಮಾಡ್ತಿದೆ; full migration consistency ಕೊಡ್ತದೆ।",
            "ನಾನು ಕಳುಹಿಸಿದ proposal ನೋಡಿ doubts ಇದ್ದರೆ call ನಲ್ಲಿ clarify ಮಾಡ್ತೀನಿ।",
            "ಬೇಕಾದ್ರೆ ನಮ್ಮ competitors ಜೊತೆ comparison ಕೂಡ ಕಳುಸ್ತೀನಿ।",
            "ನೀವು ಹೇಳಿದ issue ನ್ನು ನಮ್ಮ engineering team already fix ಮಾಡ್ತಿದೆ; update ಕೊಡ್ತೀನಿ।",
            "ಈಗ upgrade ಮಾಡಿದರೆ ನಮ್ಮ support team ನಿಂದ priority assistance ಸಿಗುತ್ತದೆ।",
            "ನೀವು ಕೊಟ್ಟ feedback ತುಂಬಾ useful; ಅದನ್ನಾ ನಾನು product team ಗೆ forward ಮಾಡಿದ್ದೇನೆ।",
            "ನಿಮ್ಮ convenience ಗೆ follow-up call schedule ಮಾಡ್ತೀನಿ; ಯಾವ ದಿನ ಒಳ್ಳೆಯದು ಹೇಳಿ।"
        ],
        "Hindi": [
            "जो issue आप face कर रहे हैं, थोड़ी detail में बताएँ? मैं तुरंत system में check करता हूँ।",
            "आपके account verification के लिए मुझे एक minute दें, details confirm करके update देता हूँ।",
            "जो error आप बता रहे हैं अगर बार-बार आ रहा है तो मैं एक ticket raise करके technical team को escalate करता हूँ।",
            "आपका payment status अभी pending दिख रहा है; refresh करके सही जानकारी देता हूँ।",
            "ये feature अभी सभी users के लिए available नहीं है; मैं check करता हूँ कि आपको early access दिया जा सकता है या नहीं।",
            "आपके email वाला link शायद expired हो गया है; मैं नया verification link भेज देता हूँ।",
            "आपका order delay हो गया लगता है; courier से बात करके latest tracking info देता हूँ।",
            "आपने दिया हुआ mobile number system में match नहीं हो रहा; क्या आपने इसे हाल ही में update किया है?",
            "आपकी login समस्या troubleshoot करने के लिए मैं quick reset try करता हूँ, आप confirm कर दें।",
            "call में बताए steps मैं email में भी भेज रहा हूँ reference के लिए।",
            "हमारे नए plan में आपको ज्यादा storage, faster support और dedicated manager जैसे benefits मिलेंगे।",
            "अगर trial के दौरान कोई limitation आती है, तो मैं उसे तुरंत unlock कर सकता हूँ।",
            "हमारा product आपके workflow में कैसे fit होता है ये दिखाने के लिए मैं personalized demo arrange करूँगा।",
            "आपके use-case के लिए हमारे premium features perfect हैं, especially automation tools।",
            "अगर आपकी team बड़ी है तो enterprise plan लेने से cost भी कम होगी।",
            "मैं आपको एक quote भेज देता हूँ ताकि आप pricing compare कर सकें।",
            "हमारे dashboard के reports से आप daily performance track कर पाएँगे।",
            "चाहें तो आपकी team के लिए onboarding session भी arrange कर दूँगा।",
            "decision लेने से पहले मैं हमारी case studies और success stories भी भेज दूँगा।",
            "आपकी requirement के अनुसार हम custom integration भी setup कर सकते हैं — बताइए अगर interest है।",
            "price को लेकर आपकी चिंता सही है, लेकिन हमारे नए plan की value भी काफी ज्यादा है।",
            "ये feature आपकी daily operations कम से कम 30% faster कर देगा, इसलिए बहुत से customers इसे prefer करते हैं।",
            "आप सोचने के लिए समय लें, पर मैंने जो discount बताया है वो अगले Friday तक ही available है।",
            "आपकी team already हमारा platform partly use कर रही है; full migration consistency बढ़ाएगा।",
            "मैंने भेजा हुआ proposal देखने के बाद अगर doubt हो तो call पर clear कर दूँगा।",
            "चाहें तो मैं competitors के साथ हमारी comparison भी भेज सकता हूँ।",
            "आपने जो issue बताया उसे हमारी engineering team already fix कर रही है; update देता रहूँगा।",
            "अभी upgrade करने पर आपको support team से priority assistance भी मिलेगा।",
            "आपका दिया feedback बहुत useful है; मैंने उसे product team को forward कर दिया है।",
            "आपकी convenience के अनुसार मैं follow-up call schedule करूँगा, कौन सा दिन बेहतर होगा बताइए।"
        ],
        "Marathi": [
            "तुम्हाला येणारा issue थोडा detail मध्ये सांगाल का? मी लगेच system मध्ये check करतो।",
            "तुमच्या account verification साठी मला एक minute द्या, details confirm करून update देतो।",
            "तुम्ही सांगितलेला error वारंवार येत असेल तर मी एक ticket raise करून technical team ला escalate करतो।",
            "तुमचा payment status सध्या pending दाखवतो; refresh करून exact माहिती देतो।",
            "हा feature अजून सगळ्या users साठी available नाही; तुम्हाला early access देता येईल का ते पाहतो।",
            "तुमच्या email मधला link कदाचित expired झाला आहे; मी नवीन verification link पाठवतो।",
            "तुमचा order delay झाल्यासारखा वाटतो; courier कडून tracking info घेऊन सांगतो।",
            "तुम्ही दिलेला mobile number आमच्या system मध्ये match होत नाही; recently update केला का?",
            "तुमचा login issue troubleshoot करण्यासाठी मी quick reset करतो, तुम्ही confirm करा।",
            "call मध्ये सांगितलेल्या steps मी email मधूनही पाठवतो reference साठी।",
            "आमच्या नवीन plan मध्ये तुम्हाला जास्त storage, faster support आणि dedicated manager असे benefits मिळतात।",
            "Trial दरम्यान काही limitations आल्या तर मी लगेच unlock करू शकतो।",
            "आमचा product तुमच्या workflow मध्ये कसा बसतो हे दाखवण्यासाठी मी personalized demo arrange करेन।",
            "तुमच्या use-case साठी आमचे premium features perfect आहेत, especially automation tools।",
            "तुमची team मोठी असेल तर enterprise plan घेतल्याने cost कमी होईल।",
            "मी तुम्हाला एक quote पाठवतो ज्याने तुम्हाला pricing compare करायला सोपं जाईल।",
            "आमच्या dashboard मधल्या reports ने तुम्ही daily performance track करू शकता।",
            "हवं असल्यास तुमच्या team साठी onboarding session पण schedule करू शकतो।",
            "decision घेण्याआधी मी आमच्या case studies आणि success stories पाठवतो।",
            "तुमच्या requirement नुसार custom integration सुद्धा setup करू शकतो—interest असेल तर सांगा।",
            "price बद्दल तुमची concern valid आहे; पण आमच्या नवीन plan चं value खूप जास्त आहे।",
            "हा feature तुमचे daily operations किमान 30% faster करेल, म्हणून बरेच customers हे prefer करतात।",
            "निर्णय घेण्यासाठी वेळ घ्या, पण मी सांगितलेला discount पुढच्या Friday पर्यंतच आहे।",
            "तुमची team आधीपासून आमचा platform partly use करते; full migration consistency वाढवेल।",
            "मी पाठवलेला proposal बघून doubts असतील तर call वर clear करतो।",
            "हवं असल्यास competitors सोबत आमची comparison पण देऊ शकतो।",
            "तुम्ही सांगितलेला issue आमची engineering team already fix करत आहे; update देत राहीन।",
            "तुम्ही upgrade केलात तर support team कडून priority assistance मिळेल।",
            "तुम्ही दिलेला feedback खूप useful आहे; तो मी product team कडे forward केलाय।",
            "तुमच्या convenience नुसार follow-up call schedule करतो; कोणता दिवस योग्य ते सांगा।"
        ],
        "Punjabi": [
            "ਤੁਸੀਂ ਜਿਹੜਾ issue face ਕਰ ਰਹੇ ਹੋ, ਥੋੜ੍ਹਾ detail ਵਿੱਚ ਦੱਸੋਗੇ? ਮੈਂ ਤੁਰੰਤ system ਵਿੱਚ check ਕਰਦਾ ਹਾਂ।",
            "ਤੁਹਾਡੇ account verification ਲਈ ਮੈਨੂੰ ਇੱਕ minute ਦਿਓ, details confirm ਕਰਕੇ update ਦੇ ਦਿਆਂਗਾ।",
            "ਜੇਹੜਾ error ਤੁਸੀਂ ਦੱਸਿਆ, ਜੇ ਉਹ ਵਾਰ–ਵਾਰ ਆ ਰਿਹਾ ਹੈ, ਤਾਂ ਮੈਂ ਇੱਕ ticket raise ਕਰਕੇ technical team ਨੂੰ escalate ਕਰਾਂਗਾ।",
            "ਤੁਹਾਡਾ payment status ਹੁਣ pending ਦਿਖਾ ਰਿਹਾ ਹੈ; refresh ਕਰਕੇ ਤੁਹਾਨੂੰ exact ਜਾਣਕਾਰੀ ਦਿੰਦਾ ਹਾਂ।",
            "ਇਹ feature ਹੁਣੇ ਸਾਰੇ users ਲਈ available ਨਹੀਂ; ਮੈਂ check ਕਰਦਾ ਹਾਂ ਕਿ ਤੁਹਾਨੂੰ early access ਦੇ ਸਕਦੇ ਹਾਂ ਕਿ ਨਹੀਂ।",
            "ਤੁਹਾਡੇ email ਵਾਲਾ link expired ਲੱਗਦਾ ਹੈ; ਮੈਂ ਹੁਣੇ ਨਵਾਂ verification link ਭੇਜ ਦਿੰਦਾ ਹਾਂ।",
            "ਤੁਹਾਡਾ order delay ਹੋਇਆ ਲੱਗਦਾ ਹੈ; courier ਨਾਲ ਗੱਲ ਕਰਕੇ ਤੁਹਾਨੂੰ tracking info ਦਿਆਂਗਾ।",
            "ਤੁਸੀਂ ਦਿੱਤਾ mobile number system ਵਿੱਚ match ਨਹੀਂ ਹੋ ਰਿਹਾ; ਕੀ ਤੁਸੀਂ ਇਸਨੂੰ recently update ਕੀਤਾ ਸੀ?",
            "ਤੁਹਾਡਾ login issue troubleshoot ਕਰਨ ਲਈ ਮੈਂ quick reset try ਕਰਦਾ ਹਾਂ, ਤੁਸੀਂ confirm ਕਰ ਦੇਣਾ।",
            "call 'ਤੇ ਜਿਹੜੇ steps explain ਕੀਤੇ, ਉਹ ਮੈਂ email 'ਚ ਵੀ send ਕਰਾਂਗਾ reference ਲਈ।",
            "ਸਾਡੇ ਨਵੇਂ plan ਵਿੱਚ ਤੁਹਾਨੂੰ ਵੱਧ storage, faster support ਅਤੇ dedicated manager ਵਰਗੇ benefits ਮਿਲਣਗੇ।",
            "Trial ਦੌਰਾਨ ਜੇ ਕੋਈ limitation ਆਈ, ਤਾਂ ਮੈਂ ਉਸਨੂੰ ਤੁਰੰਤ unlock ਕਰ ਸਕਦਾ ਹਾਂ।",
            "ਸਾਡਾ product ਤੁਹਾਡੇ workflow ਵਿੱਚ ਕਿਵੇਂ fit ਹੁੰਦਾ ਹੈ, ਇਹ ਵੇਖਾਉਣ ਲਈ ਮੈਂ personalized demo arrange ਕਰਾਂਗਾ।",
            "ਤੁਹਾਡੇ use-case ਲਈ ਸਾਡੇ premium features ਬਹੁਤ perfect ਹਨ, especially automation tools।",
            "ਜੇ ਤੁਹਾਡੀ team ਵੱਡੀ ਹੈ, ਤਾਂ enterprise plan ਨਾਲ ਤੁਹਾਡਾ cost ਵੀ ਬਚੇਗਾ।",
            "ਮੈਂ ਤੁਹਾਨੂੰ ਇੱਕ quote ਭੇਜ ਦਿਆਂਗਾ, ਜਿਸ ਨਾਲ ਤੁਸੀਂ pricing compare ਕਰ ਸਕਦੇ ਹੋ।",
            "ਸਾਡੇ dashboard ਦੇ reports ਨਾਲ ਤੁਸੀਂ daily performance track ਕਰ ਸਕਦੇ ਹੋ।",
            "ਜੇ ਤੁਹਾਨੂੰ ਚਾਹੀਦਾ ਹੈ, ਤਾਂ ਮੈਂ ਤੁਹਾਡੀ team ਲਈ onboarding session ਵੀ schedule ਕਰ ਦਿਆਂਗਾ।",
            "decision ਲੈਣ ਤੋਂ ਪਹਿਲਾਂ ਮੈਂ ਤੁਹਾਨੂੰ ਸਾਡੀਆਂ case studies ਅਤੇ success stories ਵੀ send ਕਰ ਦਿਆਂਗਾ।",
            "ਤੁਹਾਡੇ requirements ਅਨੁਸਾਰ ਅਸੀਂ custom integration ਵੀ setup ਕਰ ਸਕਦੇ ਹਾਂ—interest ਹੋਵੇ ਤਾਂ ਦੱਸੋ।",
            "price ਬਾਰੇ ਤੁਹਾਡੀ concern ਠੀਕ ਹੈ, ਪਰ ਸਾਡੇ ਨਵੇਂ plan ਦੀ value ਬਹੁਤ ਜ਼ਿਆਦਾ ਹੈ।",
            "ਇਹ feature ਤੁਹਾਡੇ daily operations ਘੱਟੋ-ਘੱਟ 30% faster ਕਰ ਦੇਵੇਗਾ, ਇਸ ਲਈ ਕਈ customers ਇਸਨੂੰ prefer ਕਰਦੇ ਹਨ।",
            "ਤੁਸੀਂ ਸੋਚਣ ਲਈ ਸਮਾਂ ਲਓ, ਪਰ ਮੈਂ ਦੱਸਿਆ discount ਸਿਰਫ਼ ਅਗਲੇ Friday ਤਕ available ਹੈ।",
            "ਤੁਹਾਡੀ team ਪਹਿਲਾਂ ਹੀ ਸਾਡਾ platform partly use ਕਰ ਰਹੀ ਹੈ; full migration consistency ਵਧਾਏਗਾ।",
            "ਮੈਂ ਭੇਜਿਆ proposal ਦੇਖ ਕੇ doubts ਹੋਣ ਤੇ ਮੈਂ call 'ਤੇ clear ਕਰਾਂਗਾ।",
            "ਜੇ ਤੁਸੀਂ ਚਾਹੋ, ਮੈਂ competitors ਨਾਲ ਸਾਡੀ comparison ਵੀ ਭੇਜ ਸਕਦਾ ਹਾਂ।",
            "ਤੁਸੀਂ ਦੱਸਿਆ issue ਸਾਡੀ engineering team already fix ਕਰ ਰਹੀ ਹੈ; ਮੈਂ ਤੁਹਾਨੂੰ update ਦਿੰਦਾ ਰਹਾਂਗਾ।",
            "ਹੁਣ upgrade ਕਰਨ 'ਤੇ ਤੁਹਾਨੂੰ support team ਤੋਂ priority assistance ਵੀ ਮਿਲੇਗਾ।",
            "ਤੁਹਾਡਾ feedback ਬਹੁਤ useful ਹੈ; ਮੈਂ ਉਹ product team ਨੂੰ forward ਕਰ ਦਿੱਤਾ ਹੈ।",
            "ਤੁਹਾਡੀ convenience ਅਨੁਸਾਰ ਮੈਂ follow-up call schedule ਕਰਾਂਗਾ, ਕਿਹੜਾ ਦਿਨ better ਹੋਵੇਗਾ ਦੱਸੋ।"
        ],
        "English-India": [
            "Could you please explain the issue you are facing in a little more detail? I will check it in the system right away.",
            "Please allow me a minute for your account verification; I will confirm the details and update you.",
            "If the error you mentioned is occurring frequently, I will raise a ticket and escalate it to our technical team.",
            "Your payment status is currently showing as pending; I will refresh the page and provide the exact update.",
            "This feature is not available for all users yet; I will check if we can offer you early access.",
            "It seems the link in your email has expired; I will send you a new verification link immediately.",
            "Your order appears to be delayed; I will check with the courier and share the latest tracking information.",
            "The mobile number you provided is not matching in our system; have you updated it recently?",
            "To troubleshoot your login issue, I will try a quick reset; please confirm once done.",
            "I will also share the steps I explained on the call via email for your reference.",
            "Our new plan offers higher storage, faster support, and benefits like a dedicated account manager.",
            "If you face any limitations during the trial, I can unlock them for you right away.",
            "I can arrange a personalized demo to show how our product fits your workflow.",
            "For your use case, our premium features are a perfect match, especially the automation tools.",
            "If you have a large team, choosing the enterprise plan will also help reduce your costs.",
            "I will share a quote with you so you can easily compare the pricing structure.",
            "With the reports available on our dashboard, you can track performance on a daily basis.",
            "If needed, I can also schedule an onboarding session for your team.",
            "Before you make a decision, I will share our case studies and customer success stories.",
            "We can also set up custom integration based on your requirements; please let me know if you are interested.",
            "Your concern about pricing is valid, but the value offered in our new plan is significantly higher.",
            "This feature can make your daily operations at least 30% faster, which is why many customers prefer it.",
            "Please take your time to think, but the discount I mentioned is available only until next Friday.",
            "Your team is already partially using our platform; a full migration will offer better consistency.",
            "If you have any doubts after reviewing the proposal, I can clarify them on a call.",
            "I can also share our comparison with competitors if you would like.",
            "The issue you mentioned is already being worked on by our engineering team; I will keep you updated.",
            "If you upgrade now, you will also receive priority support from our support team.",
            "Your feedback is very helpful; I have forwarded it to our product team.",
            "I can schedule a follow-up call as per your convenience; please let me know which day works best."
        ]
    }
    
    # Language selection with auto-update
    language = st.selectbox(
        "Select Language:",
        ["Tamil", "Telugu", "Kannada", "Marathi", "Punjabi", "Bengali", "English-India", "Hindi"],
        key="language_selector"
    )
    
    # Get random sentence for selected language
    import random
    sentences_for_language = language_sentences.get(language, language_sentences["Tamil"])
    
    # Always pick a random sentence when language changes or page loads
    # Track language and page navigation to trigger new sentence selection
    
    # Initialize tracking variables
    if "blind_test_language_tracker" not in st.session_state:
        st.session_state.blind_test_language_tracker = None
    if "sentence_cache" not in st.session_state:
        st.session_state.sentence_cache = {}
    if "blind_test_visit_id" not in st.session_state:
        st.session_state.blind_test_visit_id = 0
    
    # Check if language changed
    language_changed = st.session_state.blind_test_language_tracker != language
    
    # Check if we just navigated to Blind Test page
    current_page = st.session_state.get("current_page", "Blind Test")
    previous_page = st.session_state.get("previous_page", None)
    just_navigated_to_blind = (previous_page is not None and 
                               previous_page != "Blind Test" and 
                               current_page == "Blind Test")
    
    # Create a unique key combining language and visit ID to ensure new sentence on each visit
    visit_key = f"{language}_{st.session_state.blind_test_visit_id}"
    
    # Pick new random sentence if:
    # - Language changed
    # - Navigating to Blind Test page (from Leaderboard or reload)
    # - First time for this language/visit combination
    if language_changed or just_navigated_to_blind or visit_key not in st.session_state.sentence_cache:
        # Update language tracking
        st.session_state.blind_test_language_tracker = language
        
        # Increment visit ID to ensure new sentence on next visit
        if language_changed or just_navigated_to_blind:
            st.session_state.blind_test_visit_id = st.session_state.blind_test_visit_id + 1
            visit_key = f"{language}_{st.session_state.blind_test_visit_id}"
        
        # Pick random sentence from the 30 available for this language
        st.session_state.sentence_cache[visit_key] = random.choice(sentences_for_language)
    
    default_text = st.session_state.sentence_cache[visit_key]
    
    st.write("")  # Add spacing
    
    # Text input with multilingual support
    # Use key that changes when language changes to force update
    text_input = st.text_area(
        "Enter text to test:",
        value=default_text,
        height=120,
        max_chars=5000,
        key=f"text_input_{language}"
    )
    
    char_count = len(text_input)
    st.caption(f"Characters: {char_count}/5000")
    
    st.write("")  # Add spacing
    
    # Provider selection for blind test
    st.subheader("Provider Selection")
    
    # Get provider display names
    provider_display_names = {
        provider_id: TTS_PROVIDERS[provider_id].name 
        for provider_id in configured_providers
    }
    
    # Determine number of providers to compare
    num_providers_to_compare = st.radio(
        "Number of providers to compare:",
        ["2", "All 3"] if len(configured_providers) >= 3 else ["2"] if len(configured_providers) >= 2 else ["1"],
        key="num_providers_radio",
        horizontal=True
    )
    
    # Select which providers to compare
    selected_providers = []
    if num_providers_to_compare == "All 3" and len(configured_providers) >= 3:
        # Use all configured providers
        selected_providers = configured_providers
        st.info(f"Comparing all {len(configured_providers)} providers: {', '.join([provider_display_names[p] for p in selected_providers])}")
    elif num_providers_to_compare == "2" and len(configured_providers) >= 2:
        # Let user select 2 providers - show only display names
        provider_options = [provider_display_names[p] for p in configured_providers]
        provider_id_map = {provider_display_names[p]: p for p in configured_providers}
        
        col1, col2 = st.columns(2)
        with col1:
            provider1_name = st.selectbox(
                "Select Provider 1:",
                provider_options,
                key="provider1_select"
            )
        with col2:
            # Filter out provider1 from provider2 options
            provider2_options = [p for p in provider_options if p != provider1_name]
            provider2_name = st.selectbox(
                "Select Provider 2:",
                provider2_options,
                key="provider2_select"
            )
        
        # Map display names back to provider IDs
        provider1_id = provider_id_map[provider1_name]
        provider2_id = provider_id_map[provider2_name]
        selected_providers = [provider1_id, provider2_id]
    else:
        # Only one provider available
        selected_providers = configured_providers
        st.info(f"Only 1 provider configured: {provider_display_names[configured_providers[0]]}")
    
    st.write("")  # Add spacing
    
    # Generate blind test samples
    if st.button("Generate Blind Test", type="primary"):
        if text_input and len(selected_providers) >= 1:
            # Validate input
            valid, error_msg = session_manager.validate_request(text_input)
            if valid:
                generate_blind_test_samples(text_input, selected_providers, language)
            else:
                st.error(f"ERROR: {error_msg}")
        else:
            st.error("Please enter text and ensure at least 1 provider is selected.")
    
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
            "murf_falcon_oct23": ["Murali"],
            "elevenlabs": ["Rachel"],  # English voice, but will try
            "cartesia_sonic3": ["Conversational Lady"]  # English voice, but will try
        },
        "Telugu": {
            "murf_falcon_oct23": ["Josie", "Ronnie"],
            "elevenlabs": ["Bella"],  # English voice, but will try
            "cartesia_sonic3": ["Conversational Lady"]  # English voice, but will try
        },
        "Kannada": {
            "murf_falcon_oct23": ["Julia", "Maverick", "Rajesh"],
            "elevenlabs": ["Domi"],  # English voice, but will try
            "cartesia_sonic3": ["Conversational Lady"]  # English voice, but will try
        },
        "Marathi": {
            "murf_falcon_oct23": ["Alicia"],
            "elevenlabs": ["Rachel"],  # English voice, but will try
            "cartesia_sonic3": ["Conversational Lady"]  # English voice, but will try
        },
        "Punjabi": {
            "murf_falcon_oct23": ["Harman"],
            "elevenlabs": ["Rachel"],  # English voice, but will try
            "cartesia_sonic3": ["Conversational Lady"]  # English voice, but will try
        },
        "Bengali": {
            "murf_falcon_oct23": ["Abhik"],
            "elevenlabs": ["Rachel"],  # English voice, but will try
            "cartesia_sonic3": ["Conversational Lady"]  # English voice, but will try
        },
        "English-India": {
            "murf_falcon_oct23": ["Anisha"],
            "elevenlabs": ["Rachel"],  # English voice, but will try
            "cartesia_sonic3": ["Conversational Lady"]  # English voice, but will try
        },
        "Hindi": {
            "murf_falcon_oct23": ["Aman"],
            "elevenlabs": ["Rachel"],  # English voice, but will try
            "cartesia_sonic3": ["Conversational Lady"]  # English voice, but will try
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
    st.session_state.blind_test_language = language  # Store language for vote tracking
    st.session_state.blind_test_voted = False
    st.session_state.blind_test_vote_choice = None
    
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
            
            # Get language from session state
            language = st.session_state.get("blind_test_language", "all")
            
            # Update ELO ratings - winner beats all others (but only count as one vote)
            # We'll update ELO ratings for all comparisons but only save one vote to database
            losers = [r for r in samples if r.blind_label != selected_label]
            if losers:
                # Update ELO ratings for all comparisons
                for loser_result in losers:
                    handle_blind_test_vote(winner_result, loser_result, language, save_vote=False)
                
                # Save only one vote to database
                handle_blind_test_vote(winner_result, losers[0], language, save_vote=True)
            
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
        st.subheader("Listen Audios and Vote")
        
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

def handle_blind_test_vote(winner_result: BenchmarkResult, loser_result: BenchmarkResult, language: str = "all", save_vote: bool = True):
    """Handle blind test vote and update ELO ratings for a specific language"""
    
    from database import db
    
    try:
        # Get current ratings for this language
        winner_rating_before = db.get_elo_rating(winner_result.provider, language)
        loser_rating_before = db.get_elo_rating(loser_result.provider, language)
        
        # Update ratings for this language
        new_winner_rating, new_loser_rating = db.update_elo_ratings(
            winner_result.provider, loser_result.provider, k_factor=32, language=language
        )
        
        # Save the vote in database only if requested
        if save_vote:
            db.save_user_vote(
                winner_result.provider, 
                loser_result.provider, 
                winner_result.text[:100] + "..." if len(winner_result.text) > 100 else winner_result.text,
                session_id="blind_test_session",
                language=language
            )
        
    except Exception as e:
        st.error(f"Error updating ratings: {e}")

def leaderboard_page():
    """ELO leaderboard page with persistent data, broken down by language"""
    
    st.header("Leaderboard")
    st.markdown("Rankings of TTS providers by language")
    
    # Language selection for leaderboard
    available_languages = ["All Languages", "Tamil", "Telugu", "Kannada", "Marathi", "Punjabi", "Bengali", "English-India", "Hindi"]
    
    # Get languages that have data from database
    try:
        db_languages = db.get_available_languages()
        # Convert "all" to "All Languages" if present
        if "all" in db_languages:
            db_languages = [lang if lang != "all" else "All Languages" for lang in db_languages]
        # Merge with available languages, prioritizing those with data
        if db_languages:
            available_languages = db_languages + [lang for lang in available_languages if lang not in db_languages]
    except:
        pass
    
    # Set default to "All Languages" (index 0) unless user has previously selected something
    if "leaderboard_language_filter" not in st.session_state:
        st.session_state.leaderboard_language_filter = "All Languages"
    
    # Find the index of the current selection
    try:
        default_index = available_languages.index(st.session_state.leaderboard_language_filter)
    except ValueError:
        default_index = 0  # Default to "All Languages"
    
    selected_language = st.selectbox(
        "Filter by Language:",
        available_languages,
        index=default_index,
        key="leaderboard_language_filter",
        help="Select a language to see rankings for that language only, or 'All Languages' to see combined rankings"
    )
    
    # Convert "All Languages" back to "all" for database query
    db_language = "all" if selected_language == "All Languages" else selected_language
    
    # Get persistent leaderboard data for selected language
    leaderboard = st.session_state.benchmark_engine.get_leaderboard(db_language)
    
    # If no data for selected language, show message and don't display leaderboard
    if not leaderboard:
        if selected_language == "All Languages":
            st.info("No leaderboard data available. Run benchmarks to generate rankings.")
        else:
            st.info(f"No leaderboard data available for {selected_language}. Run blind tests with this language to generate rankings.")
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
    
    # Ensure numeric types before division
    display_df["games_played"] = pd.to_numeric(display_df["games_played"], errors='coerce').fillna(0)
    display_df["wins"] = pd.to_numeric(display_df["wins"], errors='coerce').fillna(0)
    display_df["losses"] = pd.to_numeric(display_df["losses"], errors='coerce').fillna(0)
    
    # Convert games_played, wins, and losses to actual test count
    # Each blind test involves 2 providers, and each vote increments counts for both
    # So we divide by 2 to get the actual number of tests
    display_df["Total Tests"] = (display_df["games_played"] / 2).astype(int)
    display_df["Wins"] = (display_df["wins"] / 2).astype(int)
    display_df["Losses"] = (display_df["losses"] / 2).astype(int)
    
    # Ensure win_rate is numeric
    display_df["win_rate"] = pd.to_numeric(display_df["win_rate"], errors='coerce').fillna(0.0)
    
    display_df = display_df[[
        "rank", "Provider", "Model", "Location",
        "Total Tests", "Wins", "Losses", "win_rate"
    ]].copy()
    
    display_df.columns = [
        "Rank", "Provider", "Model", "Location",
        "Total Tests", "Wins", "Losses", "Win Rate %"
    ]
    
    # Format win_rate as percentage string for display
    display_df["Win Rate %"] = display_df["Win Rate %"].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # User voting statistics for selected language
    st.subheader(f"User Voting Statistics{' - ' + selected_language if selected_language != 'All Languages' else ''}")
    vote_stats = db.get_vote_statistics(db_language)
    
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