# 🚀 Streamlit Cloud Deployment Guide

This guide will help you deploy the TTS Benchmarking Tool on Streamlit Cloud.

## ✅ Prerequisites

Before deploying, make sure you have:
- ✅ Code pushed to GitHub (DONE!)
- ✅ A Streamlit Cloud account (free)
- ✅ API keys for Murf AI and Deepgram

---

## 📋 Step-by-Step Deployment

### 1. Create Streamlit Cloud Account

1. Go to [https://share.streamlit.io/](https://share.streamlit.io/)
2. Click **"Sign up"** or **"Sign in with GitHub"**
3. Authorize Streamlit to access your GitHub repositories

### 2. Deploy Your App

1. Click **"New app"** button
2. Fill in the deployment form:
   - **Repository**: `SurajPratap10/BenchMarking_Tool`
   - **Branch**: `main`
   - **Main file path**: `app.py`
3. Click **"Deploy!"**

### 3. Add Secrets (API Keys)

⚠️ **IMPORTANT**: You need to add your API keys as secrets!

1. After deployment starts, click on **"Advanced settings"** or **"⚙️ Settings"**
2. Go to **"Secrets"** tab
3. Add the following in the secrets editor:

```toml
MURF_API_KEY = "your-murf-api-key-here"
DEEPGRAM_API_KEY = "your-deepgram-api-key-here"
```

4. Click **"Save"**
5. The app will automatically restart with the secrets

---

## 🔧 Alternative: Deploy from Streamlit Cloud Dashboard

### Option A: Deploy via URL

1. Go to [https://share.streamlit.io/deploy](https://share.streamlit.io/deploy)
2. Paste your repository URL: `https://github.com/SurajPratap10/BenchMarking_Tool`
3. Select branch: `main`
4. Main file: `app.py`
5. Click **Deploy**

### Option B: Deploy from GitHub

1. On your GitHub repository page: [https://github.com/SurajPratap10/BenchMarking_Tool](https://github.com/SurajPratap10/BenchMarking_Tool)
2. Click the **"Deploy to Streamlit"** button (if available)
3. Or manually copy the URL and use Option A

---

## 📝 Files Required for Deployment

✅ Your repository already has all the necessary files:

- ✅ `app.py` - Main application file
- ✅ `requirements.txt` - Python dependencies
- ✅ `packages.txt` - System dependencies (ffmpeg, libsndfile1)
- ✅ `.gitignore` - Prevents sensitive files from being pushed

---

## 🔐 Getting Your API Keys

### Murf AI API Key
1. Go to [https://murf.ai](https://murf.ai)
2. Sign up / Log in to your account
3. Navigate to **API Settings** or **Developer** section
4. Copy your API key

### Deepgram API Key
1. Go to [https://deepgram.com](https://deepgram.com)
2. Sign up / Log in to your account
3. Navigate to **API Keys** section
4. Create a new API key or copy existing one

---

## ⚡ Quick Deploy Commands Summary

All commands have been executed! Here's what we did:

```bash
# 1. Stage all changes
git add -A

# 2. Commit changes
git commit -m "Add geolocation feature and optimize codebase"

# 3. Add GitHub remote
git remote add origin https://github.com/SurajPratap10/BenchMarking_Tool.git

# 4. Pull and merge with remote
git pull origin main --allow-unrelated-histories --no-rebase --no-edit

# 5. Resolve conflicts
git checkout --ours README.md
git add README.md
git commit -m "Merge remote README with local version"

# 6. Push to GitHub
git push -u origin main
```

✅ **Your code is now on GitHub!**

---

## 🌐 After Deployment

Once deployed, your app will be available at:
```
https://[your-app-name].streamlit.app
```

You can:
- Share the URL with anyone
- Update the app by pushing new commits to GitHub
- Monitor app logs in the Streamlit Cloud dashboard
- Manage secrets and settings from the dashboard

---

## 🐛 Troubleshooting

### App won't start?
- Check that all API keys are added in Secrets
- Verify `requirements.txt` and `packages.txt` are present
- Check app logs in Streamlit Cloud dashboard

### API errors?
- Verify API keys are correct in Secrets
- Make sure API keys have proper permissions
- Check API rate limits

### Database issues?
- The app uses SQLite which is automatically created
- Database file is temporary and resets on redeployment
- For persistent storage, consider upgrading to a cloud database

---

## 📚 Additional Resources

- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit Secrets Management](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Streamlit App Dependencies](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/app-dependencies)

---

## 🎉 You're All Set!

Your TTS Benchmarking Tool is ready to deploy on Streamlit Cloud!

**Next Steps:**
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select your repository
4. Add your API keys to Secrets
5. Deploy! 🚀

