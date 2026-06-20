# Scholarship Agent

A production-grade AI agent system for discovering, extracting, and publishing scholarship opportunities for Ethiopian students worldwide.

## Features

- 🔍 **Web Search**: Automated web search for scholarships using Tavily API
- 📋 **Intelligent Extraction**: LLM-powered extraction of scholarship details
- ✍️ **Grammar Correction**: Automated grammar and readability improvements
- ✅ **Fact Checking**: Verification of deadlines, URLs, and university information
- 🔄 **Duplicate Detection**: Machine learning-based duplicate scholarship detection
- 📱 **Telegram Integration**: Automatic posting to Telegram channels/groups
- 💾 **Database Storage**: PostgreSQL backend for persistence and analytics
- ⏰ **Scheduled Execution**: APScheduler for twice-daily automated runs
- 🔐 **Production Ready**: Logging, error handling, and deployment-ready

## Architecture

The system uses **LangGraph** for multi-agent orchestration:

```
Scheduler (2x daily)
    ↓
Search Agent (Web Search)
    ↓
Extraction Agent (LLM)
    ↓
Filtering Agent (Duplicates & Validation)
    ↓
Grammar Agent (LLM)
    ↓
Fact Check Agent
    ↓
Telegram Publisher
    ↓
Database Storage
```

## Tech Stack

- **LangGraph**: Multi-agent orchestration
- **LangChain**: LLM interactions
- **OpenAI GPT-4**: Language understanding and generation
- **Tavily**: Web search API
- **PostgreSQL**: Data persistence
- **Telegram Bot API**: Message publishing
- **APScheduler**: Task scheduling
- **SQLAlchemy**: ORM
- **Pydantic**: Data validation

## Project Structure

```
scholarship-agent/
├── app/
│   ├── agents/          # Agent implementations
│   ├── database/        # SQLAlchemy models and DB connection
│   ├── prompts/         # LLM prompts
│   ├── scheduler/       # APScheduler setup
│   ├── config.py        # Configuration management
│   ├── main.py          # Entry point
│   ├── workflows.py     # LangGraph workflow definition
│   └── __init__.py
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Environment variables (local)
└── README.md            # This file
```

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- OpenAI API key
- Tavily API key
- Telegram Bot Token

### Setup

1. **Clone and navigate to project**:
   ```bash
   cd scholarship-agent
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database credentials
   ```

5. **Initialize database**:
   ```bash
   python -c "from app.database.db import init_db; init_db()"
   ```

## Configuration

All configuration is managed through environment variables (see `.env.example`):

### Required
- `OPENAI_API_KEY`: OpenAI API key (gpt-4-turbo-preview)
- `TAVILY_API_KEY`: Tavily web search API key
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHANNEL_ID`: Target Telegram channel ID
- `DATABASE_URL`: PostgreSQL connection string

### Optional
- `TELEGRAM_GROUP_ID`: Target Telegram group ID
- `ENVIRONMENT`: development/production (default: development)
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
- `SCHEDULER_ENABLED`: Enable automatic scheduling (default: true)
- `DUPLICATE_THRESHOLD`: Similarity threshold 0-1 (default: 0.85)

## Usage

### Running the Agent

```bash
python -m app.main
```

### Running with Scheduler

```bash
# Scheduler will automatically trigger searches twice daily
python -m app.scheduler.scheduler
```

### Example Workflow

```python
import asyncio
from app.main import ScholarshipAgent

async def main():
    agent = ScholarshipAgent()
    
    queries = [
        "DAAD scholarship Ethiopia 2026",
        "Fully funded master's scholarship",
    ]
    
    results = await agent.run_workflow(queries)
    agent.shutdown()

asyncio.run(main())
```

## Database Schema

### Scholarships Table
- `id`: UUID primary key
- `title`: Scholarship name
- `country`: Target country
- `university`: Host university
- `degree_level`: Bachelor's, Master's, PhD
- `benefits`: Funding details
- `eligibility`: Requirements
- `application_deadline`: Deadline date
- `official_link`: Scholarship URL
- And more...

### Telegram Messages Table
- Tracks all messages sent to Telegram
- Links to scholarships
- Delivery status and engagement metrics

### Processing Logs Table
- Tracks all agent executions
- Performance metrics and errors
- Used for debugging and monitoring

### Duplicate Cache Table
- Stores scholarship hashes for duplicate detection
- Fast similarity comparison

## API Integration

### OpenAI
- Model: `gpt-4-turbo-preview`
- Used for: Extraction, grammar correction, fact-checking
- Rate limits: Configured with retries

### Tavily
- Web search across 10+ search engines
- Results filtering and curation

### Telegram Bot API
- Direct message posting to channels/groups
- Message editing and deletion support

## Development

### Running Tests

```bash
pytest -v
```

### Code Quality

```bash
# Format code
black app/

# Type checking
mypy app/

# Linting
flake8 app/
```

### Database Migrations

Using Alembic (optional for advanced use):

```bash
alembic init migrations
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

## Deployment

### Docker

```bash
docker build -t scholarship-agent .
docker run -e OPENAI_API_KEY=sk-... scholarship-agent
```

### Railway/Render

1. Push to GitHub
2. Connect repository
3. Set environment variables
4. Deploy

### VPS (Ubuntu)

```bash
# Setup
sudo apt install python3.10 python3-pip postgresql
git clone <repo>
cd scholarship-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run as service
sudo systemctl create scholarship-agent
```

## Monitoring & Logging

All agent actions are logged to:
- Console (development)
- `logs/app.log` (file)
- Database (ProcessingLog table)

Access logs:
```python
from app.config import logger
logger.info("Custom message")
```

## Error Handling

The system has comprehensive error handling:
- Network timeouts (with retries)
- LLM API failures (fallback models)
- Database connection failures (connection pooling)
- Malformed responses (validation)

## Troubleshooting

### "Database connection failed"
- Check PostgreSQL is running: `psql -U postgres`
- Verify DATABASE_URL in .env
- Run `init_db()` to create tables

### "OpenAI API error"
- Check OPENAI_API_KEY is valid
- Verify API quota: https://platform.openai.com/account/usage/overview
- Check rate limits: retry delay configured

### "No results found"
- Verify Tavily API key is valid
- Check search queries are not too specific
- Review error logs in ProcessingLog table

## Contributing

Contributions welcome! Areas for enhancement:
- Additional scholarship sources
- Multi-language support
- Advanced NLP filtering
- Analytics dashboard
- Mobile app integration

## License

MIT License

## Support

For issues, questions, or feature requests:
- GitHub Issues: [Create issue]
- Email: [Your email]
- Telegram: [@YourBotHandle]

---

**Built with ❤️ for Ethiopian students worldwide**

