# Quick Start Guide - Scholarship Agent

## 📋 Prerequisites

Before you begin, ensure you have:

- Python 3.10 or higher
- PostgreSQL 14 or higher installed and running
- Git
- API Keys:
  - OpenAI API key (ChatGPT/GPT-4)
  - Tavily API key (web search)
  - Telegram Bot Token
  - Telegram Channel ID

## 🚀 Installation Steps

### 1. Clone the Repository
```bash
cd scholarship-agent
cd scholarship-agent
```

### 2. Create Virtual Environment
```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual API keys
# Important: Use a text editor to fill in:
# - OPENAI_API_KEY
# - TAVILY_API_KEY
# - TELEGRAM_BOT_TOKEN
# - TELEGRAM_CHANNEL_ID
# - DATABASE_URL (PostgreSQL connection)
```

### 5. Initialize Database
```bash
python -c "from app.database.db import init_db; init_db()"
```

You should see: "Database tables created successfully"

### 6. Verify Installation
```bash
python -m app.main
```

Expected output:
```
============================================================
Scholarship Agent v1.0
============================================================
Environment: development
Debug Mode: True
Database: postgresql+psycopg2://...
Scheduler Enabled: True
============================================================
```

## 🎯 Getting API Keys

### OpenAI API Key
1. Go to https://platform.openai.com/account/api-keys
2. Click "Create new secret key"
3. Copy the key immediately (you won't see it again!)
4. Add to `.env`: `OPENAI_API_KEY=sk-...`

### Tavily API Key
1. Go to https://tavily.com
2. Sign up for free
3. Get your API key from the dashboard
4. Add to `.env`: `TAVILY_API_KEY=...`

### Telegram Bot Token
1. Chat with @BotFather on Telegram
2. Send: `/newbot`
3. Follow the prompts to create a new bot
4. Copy the token (e.g., `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
5. Add to `.env`: `TELEGRAM_BOT_TOKEN=...`

### Telegram Channel/Group ID
1. Create a new channel or group (or use existing one)
2. Add the bot to your channel/group as an admin
3. Send a test message to the channel
4. Go to https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
5. Replace `<YOUR_BOT_TOKEN>` with your actual bot token
6. Look for the chat ID (usually starts with `-100`)
7. Add to `.env`: `TELEGRAM_CHANNEL_ID=-100...`

### PostgreSQL Connection
```bash
# Option 1: Local PostgreSQL
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/scholarship_agent

# Option 2: Docker (if using docker-compose)
DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/scholarship_agent

# Option 3: Remote (e.g., Render, Railway)
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/scholarship_agent
```

## 📖 Project Structure

```
scholarship-agent/
├── app/
│   ├── agents/           # Agent implementations (Part 2-5)
│   ├── database/         # Database models and connections
│   ├── prompts/          # LLM prompts
│   ├── scheduler/        # Scheduling logic (Part 6)
│   ├── config.py         # Configuration management
│   ├── logging_config.py # Logging setup
│   ├── main.py          # Entry point
│   ├── utils.py         # Utility functions
│   ├── workflows.py     # LangGraph workflow
│   └── __init__.py
├── .env                 # Your local configuration
├── .env.example         # Template
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker image
├── docker-compose.yml   # Local development
└── README.md            # Full documentation
```

## 🔧 Configuration

### Environment Variables

**Required:**
```
OPENAI_API_KEY          # OpenAI API key
TAVILY_API_KEY          # Web search API key
TELEGRAM_BOT_TOKEN      # Telegram bot token
TELEGRAM_CHANNEL_ID     # Telegram channel ID
DATABASE_URL            # PostgreSQL connection string
```

**Optional (with defaults):**
```
ENVIRONMENT=development              # or 'production'
DEBUG=True                           # True/False
LOG_LEVEL=INFO                       # DEBUG, INFO, WARNING, ERROR
SCHEDULER_ENABLED=True               # Enable 2x daily runs
FIRST_RUN_HOUR=6                     # 6 AM
SECOND_RUN_HOUR=18                   # 6 PM
DUPLICATE_THRESHOLD=0.85             # 0-1, higher = stricter
```

## 🧪 Testing the Setup

### Test Database Connection
```bash
python -c "from app.database.db import engine; engine.connect(); print('✅ Database connection OK')"
```

### Test OpenAI Connection
```bash
python -c "
from langchain.llms import OpenAI
from app.config import settings
llm = OpenAI(api_key=settings.openai_api_key)
print('✅ OpenAI connection OK')
"
```

### Test Tavily Search
```bash
python -c "
from tavily import TavilyClient
from app.config import settings
client = TavilyClient(api_key=settings.tavily_api_key)
results = client.search('DAAD scholarship', max_results=5)
print(f'✅ Tavily search OK - found {len(results)} results')
"
```

### Test Telegram Bot
```bash
python -c "
from telegram import Bot
from app.config import settings
bot = Bot(token=settings.telegram_bot_token)
info = bot.get_me()
print(f'✅ Telegram bot OK - @{info.username}')
"
```

## 📚 Building the Agent (Step by Step)

The agent is built in 10 parts:

1. ✅ **Part 1** - Project setup, environment, LangGraph foundation (THIS PART)
2. 📝 **Part 2** - Scholarship Search Agent (uses Tavily)
3. 📋 **Part 3** - Scholarship Extraction Agent (LLM)
4. ✍️ **Part 4** - Grammar Agent (LLM)
5. 📱 **Part 5** - Telegram Publisher
6. ⏰ **Part 6** - APScheduler (twice daily)
7. 🔄 **Part 7** - Duplicate Detection
8. 📊 **Part 8** - Logging & Error Handling
9. 🐳 **Part 9** - Docker Deployment
10. 🚀 **Part 10** - GitHub Actions CI/CD

## 🔄 Workflow Flow

```
Scheduler (2x daily)
    ↓
Search Agent (find scholarships)
    ↓
Extraction Agent (extract details)
    ↓
Filtering (remove duplicates)
    ↓
Grammar Agent (improve writing)
    ↓
Fact Check (verify info)
    ↓
Telegram Publisher (send message)
    ↓
Database Storage (save for later)
```

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'langgraph'"
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### "ConnectionRefusedError: PostgreSQL"
```bash
# Make sure PostgreSQL is running
# macOS
brew services start postgresql

# Or use Docker
docker-compose up -d postgres
```

### "Authentication failed: OpenAI"
```bash
# Check your API key
echo $OPENAI_API_KEY
# Make sure it starts with 'sk-'
```

### "Database table exists" error
```bash
# Reset database (development only!)
python -c "from app.database.db import drop_all_tables, init_db; drop_all_tables(); init_db()"
```

## 📞 Support

- 📖 Full docs: See `README.md`
- 🐛 Issues: Check GitHub Issues
- 💬 Questions: Telegram support channel

## 🎉 Next Steps

After completing Part 1:

1. Read the full [README.md](README.md)
2. Proceed to Part 2: Scholarship Search Agent
3. Test the search agent with sample queries
4. Build towards full automation

---

**Happy scholarship hunting! 🎓**

