# Video Search & Summary App

A Streamlit application that searches YouTube videos and provides AI-powered summaries and content ratings.

## Features
- YouTube video search
- AI-powered content rating and summarization
- Multiple summary styles
- Transcript viewing and downloading
- Multi-language support
- User authentication
- Custom summary patterns

## Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables in `.env` file:
   ```
   YOUTUBE_API_KEY=your_youtube_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## Deployment
This app is ready to deploy on Streamlit Community Cloud:
1. Push code to GitHub
2. Connect to Streamlit Cloud
3. Add secrets in Streamlit Cloud settings:
   - YOUTUBE_API_KEY
   - OPENAI_API_KEY 