# Quick Setup Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies
```bash
cd /Users/surajpratap/Downloads/Benchmarking-Telugu
pip install -r requirements.txt
```

### Step 2: Configure API Keys

1. **Copy the example environment file:**
```bash
cp .env.example .env
```

2. **Edit `.env` and add your API keys:**
```bash
# Open with your editor
nano .env
# or
code .env
```

3. **Get your API keys:**
   - **Murf AI**: https://murf.ai/ (Required for Tamil/Telugu/Kannada)
   - **ElevenLabs**: https://elevenlabs.io/ (Optional)

4. **Your `.env` should look like this:**
```
MURF_API_KEY=murf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 3: Test Your Setup
```bash
python test_api.py
```

You should see:
```
✅ Murf Falcon: WORKING
✅ ElevenLabs Flash: WORKING
🎉 All providers are working!
```

### Step 4: Run the App
```bash
python run.py
```

Or directly with Streamlit:
```bash
streamlit run app.py
```

### Step 5: Access the App
Open your browser to: **http://localhost:8501**

---

## 📱 Using the App

### Blind Test Screen
1. **Enter text** in any language:
   - Tamil (தமிழ்)
   - Telugu (తెలుగు)
   - Kannada (ಕನ್ನಡ)
   - Hindi (हिंदी)
   - English

2. **Select language** from dropdown (matches voices automatically)

3. **Click "Generate Blind Test"**

4. **Listen** to samples A, B, etc. (providers hidden)

5. **Vote** for your favorite

6. **See results** - providers revealed!

### Leaderboard Screen
- View ELO rankings
- See provider statistics
- Track performance over time

---

## 🎤 Available Voices

### Tamil (தமிழ்)
- **Alicia** - Female, Conversational
- **Murali** - Male

### Telugu (తెలుగు)
- **Josie** - Female, Conversational
- **Ronnie** - Male

### Kannada (ಕನ್ನಡ)
- **Julia** - Female, Conversational
- **Maverick** - Male, Conversational
- **Rajesh** - Male

---

## ⚠️ Troubleshooting

### "No successful samples generated"
- **Check API keys** in `.env` file
- **Run test script:** `python test_api.py`
- **Check internet connection**
- **Verify account has credits** (for Murf/ElevenLabs)

### "API key not found"
- **Make sure `.env` file exists** in the project root
- **Check file permissions:** `ls -la .env`
- **Verify variable names** match exactly (MURF_API_KEY)

### "Text contains excessive special characters"
- **This is fixed!** App now supports all Indian scripts
- If you still see this, try shorter text first

### Voice not working for language
- **Select correct language** from dropdown
- Tamil text → Select "Tamil (தமிழ்)"
- Telugu text → Select "Telugu (తెలుగు)"
- Kannada text → Select "Kannada (ಕನ್ನಡ)"

---

## 💡 Tips

1. **Best Results:** Configure both Murf and ElevenLabs for comparison
2. **Language Selection:** Always match your text language with dropdown
3. **Sample Texts:** Use the "📝 Sample Texts" expander for quick testing
4. **Character Limit:** Up to 5000 characters supported
5. **Download Audio:** After voting, download MP3 files for each provider

---

## 🆘 Still Need Help?

1. **Check logs** when running the app
2. **Run diagnostic:** `python test_api.py`
3. **Verify Python version:** `python --version` (need 3.9+)
4. **Check dependencies:** `pip list | grep streamlit`

---

## ✅ Quick Checklist

- [ ] Python 3.9+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with API keys
- [ ] Test script passes (`python test_api.py`)
- [ ] App runs (`python run.py`)
- [ ] Can access http://localhost:8501
- [ ] Text input works in all languages
- [ ] Audio generation successful
- [ ] Voting works
- [ ] Leaderboard displays

**All checked?** 🎉 You're ready to go!

