# AI Content Curator

Automated content curation based on your interests and projects. Searches articles, YouTube, Reddit, and Stack Overflow, uses AI to summarize and recommend, and syncs to Obsidian.

## Features

- **Multi-source search**: Medium, Dev.to, HackerNoon, YouTube, Reddit, Stack Overflow
- **Project scanning**: Analyze GitHub repos to suggest relevant topics
- **AI summaries**: GPT-4 powered summaries with skill level and time estimates
- **Preference learning**: Improves recommendations based on your actions
- **Obsidian sync**: Export read items to your knowledge base
- **Automated refresh**: Cron-based content updates

## Quick Start

### Local Development

```bash
# Clone and setup
git clone <repo>
cd content-curator
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="sk-..."

# Run
streamlit run app.py
```

### Docker (QNAP NAS)

```bash
# Create .env file
echo "OPENAI_API_KEY=sk-..." > .env
echo "OBSIDIAN_VAULT=/share/Obsidian" >> .env

# Build and run
docker-compose up -d
```

Access at `http://your-nas-ip:8501`

### Tailscale Setup

1. Install Tailscale on NAS and phone
2. Access via Tailscale IP: `http://100.x.x.x:8501`

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 | Yes |
| `GITHUB_TOKEN` | GitHub token for private repos | No |
| `OBSIDIAN_VAULT` | Path to Obsidian vault | No |

## Architecture

See `docs/plans/2025-01-21-content-curator-design.md` for full design document.

## Development

```bash
# Run tests
pytest -v

# Run specific test
pytest tests/test_database.py -v
```
