# AI Article & Video Recommender

Search multiple platforms for articles and videos, get AI-powered summaries and recommendations.

## Features

- **Multi-source article search**: Medium, Dev.to, HackerNoon, Towards Data Science, freeCodeCamp
- **YouTube video search** with thumbnails and transcript links
- **AI summaries** using GPT-4 to determine if content is worth your time
- **Age filter** to find recent content (past week/month/year)

## Setup

### Local Development

```bash
pip install -r requirements.txt
streamlit run ai_recommendations_app.py
```

### Streamlit Cloud

1. Fork/push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo
4. Add secrets in the dashboard:

```toml
OPENAI_API_KEY = "sk-..."
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key for GPT-4 summaries |
