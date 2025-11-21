# Streamlit Cloud Deployment Guide

## Database Persistence Issue

**Problem**: Streamlit Cloud uses an **ephemeral filesystem**. This means:
- Files are deleted when the app restarts
- Database resets daily or after each deployment
- Data is not persisted between deployments

## Solutions

### Option 1: Use External Database (Recommended)

Set up a cloud database service and configure your app to use it:

#### Using PostgreSQL (Supabase, Heroku, Railway, etc.)

1. Create a PostgreSQL database
2. Install required package:
   ```bash
   pip install psycopg2-binary
   ```
3. Update `database.py` to use PostgreSQL instead of SQLite
4. Set environment variables in Streamlit Cloud:
   - `DATABASE_URL=postgresql://user:password@host:port/database`

#### Using MySQL (PlanetScale, Railway, etc.)

1. Create a MySQL database
2. Install required package:
   ```bash
   pip install mysql-connector-python
   ```
3. Update `database.py` to use MySQL
4. Set environment variables in Streamlit Cloud

### Option 2: Use Cloud Storage for Database File

1. Store database file in cloud storage (AWS S3, Google Cloud Storage)
2. Download on app startup
3. Upload periodically or on shutdown

### Option 3: Use Streamlit Secrets for Database Connection

1. Go to your Streamlit Cloud app settings
2. Add secrets in "Secrets" tab:
   ```toml
   [database]
   url = "your_database_connection_string"
   ```
3. Update code to read from `st.secrets["database"]["url"]`

## Quick Configuration

To use a custom database path (for testing):

1. Set environment variable in Streamlit Cloud:
   ```
   DATABASE_PATH=/tmp/benchmark_data.db
   ```

**Note**: Even `/tmp` won't persist on Streamlit Cloud. You need an external database for true persistence.

## Recommended Services

- **Supabase**: Free PostgreSQL hosting
- **Railway**: Easy database deployment
- **Heroku Postgres**: Reliable PostgreSQL
- **PlanetScale**: MySQL with branching
- **Neon**: Serverless PostgreSQL

## Current Status

The app currently uses SQLite which works locally but resets on Streamlit Cloud. For production use, migrate to an external database.

