# 🚀 Deployment Guide - TTS Benchmarking Tool

## Quick Deploy (5 minutes)

### Option 1: Streamlit Cloud (FREE & EASIEST)

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "TTS Benchmarking Tool"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/tts-benchmarking.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to https://share.streamlit.io/
   - Click "New app"
   - Connect your GitHub repo
   - Set main file: `app.py`
   - Add secrets (API keys) in the secrets section
   - Click "Deploy"

3. **Your shareable link:** `https://YOUR_APP_NAME.streamlit.app`

### Option 2: Railway (FREE TIER)

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Deploy:**
   ```bash
   railway login
   railway init
   railway up
   ```

3. **Set environment variables:**
   ```bash
   railway variables set MURF_API_KEY=ap2_e69ee48a-7ef7-485c-800f-d072bab67d8e
   railway variables set DEEPGRAM_API_KEY=2bd9e1b3792c047dd0f92cb7e45e5a91ca2d5246
   ```

## Environment Variables Needed

```
MURF_API_KEY=ap2_e69ee48a-7ef7-485c-800f-d072bab67d8e
DEEPGRAM_API_KEY=2bd9e1b3792c047dd0f92cb7e45e5a91ca2d5246
```

## Files Ready for Deployment

✅ `requirements.txt` - All dependencies listed
✅ `Dockerfile` - Container configuration
✅ `.streamlit/config.toml` - Streamlit settings
✅ `.streamlit/secrets.toml` - API keys for Streamlit Cloud
✅ `app.py` - Main application
✅ All provider implementations working

## Webflow Integration

Once deployed, add this to your Webflow page:

```html
<iframe 
  src="https://your-app-name.streamlit.app" 
  width="100%" 
  height="800px" 
  frameborder="0"
  style="border-radius: 8px;">
</iframe>
```

## Troubleshooting

- **Import errors**: Check requirements.txt
- **API errors**: Verify environment variables
- **Database issues**: SQLite creates automatically
- **CORS issues**: Already configured in config.toml

Ready to deploy! 🚀
