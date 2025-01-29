import os
from dotenv import load_dotenv
import streamlit as st

# Try to load from .env file
load_dotenv()

# Get API keys - first try environment variables, then streamlit secrets
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY') or st.secrets.get('YOUTUBE_API_KEY')

# Add debug logging
print("\nAPI Keys loaded:")
print(f"YouTube API Key: {YOUTUBE_API_KEY[:10]}...")
print(f"OpenAI API Key: {OPENAI_API_KEY[:10]}...")
print(f"YouTube API Key source: {'Environment' if os.getenv('YOUTUBE_API_KEY') else 'Streamlit Secrets'}")

# YouTube API settings
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
MAX_RESULTS = 10  # Number of videos to fetch per search 