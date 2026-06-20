# Development Guide - Scholarship Agent

## Part 1 Complete ✅

You now have a **production-ready foundation** with:
- LangGraph workflow orchestration framework
- SQLAlchemy database models (Scholarship, TelegramMessage, ProcessingLog, etc.)
- Pydantic configuration management
- Logging infrastructure
- Utility functions
- Docker support

## Current File Structure

```
✅ Core Application Files
- app/config.py              (160 lines) - Configuration management
- app/logging_config.py      (140 lines) - Logging setup
- app/utils.py               (350 lines) - Helper utilities
- app/workflows.py           (180 lines) - LangGraph workflow
- app/main.py                (130 lines) - Entry point

✅ Database Layer
- app/database/db.py         (140 lines) - Connection & session management
- app/database/models.py     (300 lines) - 5 SQLAlchemy models

✅ Agent Infrastructure
- app/agents/base_agent.py   (150 lines) - Abstract base class

✅ Configuration Files
- requirements.txt           - All dependencies
- .env, .env.example         - Environment variables
- docker-compose.yml         - Development environment
- Dockerfile                 - Container image

✅ Documentation
- README.md                  - Full documentation
- QUICKSTART.md              - Quick setup
- verify_setup.py            - Setup validation
```

## Getting Started (5 Steps)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy template
cp .env.example .env

# Edit .env with your API keys:
# OPENAI_API_KEY=sk-...
# TAVILY_API_KEY=...
# TELEGRAM_BOT_TOKEN=...
# TELEGRAM_CHANNEL_ID=-100...
# DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db
```

### 3. Initialize Database
```bash
python -c "from app.database.db import init_db; init_db()"
```

### 4. Verify Setup
```bash
python verify_setup.py
```

### 5. Run Application
```bash
python -m app.main
```

## Part 2: Search Agent (Next)

The SearchAgent will:

### Key Files to Create
```
app/agents/search_agent.py      (~250 lines)
  - Extend BaseAgent
  - Use Tavily for web search
  - Query rotation logic
  - Results filtering and ranking
```

### Responsibilities
1. **Query Generation**: Build diverse search queries
   - "DAAD scholarship Ethiopia 2026"
   - "Fully funded master's scholarship Africa"
   - "Government scholarships 2026"
   - "PhD fellowship Ethiopia"

2. **Web Search**: Use Tavily API
   ```python
   from tavily import TavilyClient
   client = TavilyClient(api_key=settings.tavily_api_key)
   results = client.search("query", max_results=50)
   ```

3. **Results Filtering**
   - Check deadlines haven't passed
   - Verify official sources
   - Accepts Ethiopian applicants
   - Remove duplicates from same source

4. **State Update**
   ```python
   state.search_results = filtered_results
   state.search_queries = queries_used
   return state
   ```

### Integration with Workflow
```
START → search (SEARCH AGENT) → extract → ...
```

## Code Quality Standards

### Style Guide
```python
# Follow PEP 8
# Use type hints
# Add docstrings
# Keep functions focused

def search_scholarships(
    queries: List[str],
    max_results: int = 50
) -> List[Dict[str, Any]]:
    """
    Search for scholarships using web search.
    
    Args:
        queries: Search queries to execute
        max_results: Maximum results per query
        
    Returns:
        List of search results
    """
    pass
```

### Testing
```bash
# Format code
black app/

# Type checking
mypy app/

# Linting
flake8 app/

# Unit tests
pytest tests/
```

### Logging
```python
from app.config import logger

logger.info("Processing 50 scholarships")
logger.error("API error", exc_info=True)
logger.debug("Detailed info")
```

## Database Models

### Available Models

#### Scholarship
- Full scholarship information
- Extraction status
- Duplicate detection
- Track if posted

#### TelegramMessage
- Links scholarship to message
- Tracks delivery
- Engagement metrics

#### ProcessingLog
- Agent execution history
- Performance metrics
- Error tracking

#### DuplicateCache
- Hash-based comparison
- Similarity tracking

#### SchedulerRun
- Scheduled execution tracking
- Success/failure metrics

### Querying Examples
```python
from sqlalchemy import select
from app.database.models import Scholarship
from app.database.db import SessionLocal

db = SessionLocal()

# Get all scholarships
scholarships = db.query(Scholarship).all()

# Get active scholarships
active = db.query(Scholarship).filter(
    Scholarship.is_active == True,
    Scholarship.is_duplicate == False
).all()

# Get scholarships for a country
german = db.query(Scholarship).filter(
    Scholarship.country == "Germany"
).all()

db.close()
```

## API Integration Patterns

### OpenAI (LangChain)
```python
from langchain.llms import OpenAI
from app.config import settings

llm = OpenAI(
    api_key=settings.openai_api_key,
    model=settings.openai_model,
    temperature=0.7,
)

response = llm("Extract scholarship details...")
```

### Tavily (Web Search)
```python
from tavily import TavilyClient
from app.config import settings

client = TavilyClient(api_key=settings.tavily_api_key)
results = client.search("query", max_results=50)
```

### Telegram (Bot API)
```python
from telegram import Bot
from app.config import settings

bot = Bot(token=settings.telegram_bot_token)
bot.send_message(
    chat_id=settings.telegram_channel_id,
    text="Message",
    parse_mode="HTML"
)
```

### PostgreSQL (SQLAlchemy)
```python
from sqlalchemy.orm import Session
from app.database.models import Scholarship

def save_scholarship(db: Session, data: dict):
    scholarship = Scholarship(
        title=data["title"],
        country=data["country"],
        # ... other fields
    )
    db.add(scholarship)
    db.commit()
    return scholarship
```

## Workflow State Pattern

All agents receive and return ScholarshipState:

```python
from app.workflows import ScholarshipState

async def my_agent_execute(state: ScholarshipState) -> ScholarshipState:
    # Read from state
    search_results = state.search_results
    existing_scholarships = state.scholarships
    
    # Process
    processed = do_something(search_results)
    
    # Update state
    state.scholarships.extend(processed)
    state.execution_metadata["agent_name_processed"] = len(processed)
    
    # Return updated state
    return state
```

## Common Patterns

### Error Handling
```python
try:
    results = client.search(query)
except APIError as e:
    logger.error(f"API error: {e}", exc_info=True)
    state = self.add_error_to_state(state, str(e))
    return state
```

### Logging
```python
self.log_info(f"Processing {len(scholarships)} scholarships")
self.log_warning("Deadline in the past")
self.log_debug("Detailed information")
self.log_error("Something went wrong", exc)
```

### Duplicate Detection
```python
from app.utils import generate_hash, calculate_similarity

hash1 = generate_hash(title1)
sim = calculate_similarity(title1, title2)

if sim > settings.duplicate_threshold:
    # It's a duplicate
    pass
```

## Environment Variables

### Required (Must configure)
- OPENAI_API_KEY
- TAVILY_API_KEY
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHANNEL_ID
- DATABASE_URL

### Optional (Have defaults)
- ENVIRONMENT: development/production
- DEBUG: True/False
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR
- DUPLICATE_THRESHOLD: 0.85
- MAX_SEARCH_RESULTS: 50
- SCHEDULER_ENABLED: True
- FIRST_RUN_HOUR: 6
- SECOND_RUN_HOUR: 18

## Common Tasks

### Add a New Configuration Variable
```python
# In app/config.py
my_new_variable: str = Field(
    default="default_value",
    alias="MY_NEW_VARIABLE"
)

# In .env
MY_NEW_VARIABLE=actual_value

# Use it
from app.config import settings
value = settings.my_new_variable
```

### Add a New Database Model
```python
# In app/database/models.py
class MyModel(Base):
    __tablename__ = "my_table"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create table
from app.database.db import init_db
init_db()
```

### Add a New Utility Function
```python
# In app/utils.py
def my_helper_function(param: str) -> str:
    """Description of what it does."""
    return result

# Use it
from app.utils import my_helper_function
result = my_helper_function("input")
```

### Add a New Agent
```python
# In app/agents/my_agent.py
from app.agents import BaseAgent
from app.workflows import ScholarshipState

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__("MyAgent", "Does something")
    
    async def execute(self, state: ScholarshipState) -> ScholarshipState:
        self.log_info("Starting")
        # Do work
        return state
```

## Debugging

### Enable Debug Mode
```python
# In .env
DEBUG=True
LOG_LEVEL=DEBUG
```

### Check Logs
```bash
tail -f logs/app_*.log
```

### Database Inspection
```bash
psql postgresql://user:pass@localhost:5432/scholarship_agent

# List tables
\dt

# Query scholarships
SELECT title, country, application_deadline FROM scholarships LIMIT 5;
```

### Test API Connections
```bash
python verify_setup.py
```

## Performance Optimization

### Database
- Connection pooling: Configured in db.py
- Query optimization: Use indexes (already added)
- Batch operations: Use batch_list() from utils

### LLM
- Use lower temperature for deterministic results: temperature=0
- Batch API calls: Use async/await
- Cache responses: Consider redis for Part 8

### Web Search
- Limit results: max_results parameter
- Rate limiting: Configure in config.py
- Caching: Store results in database

## Deployment

### Docker
```bash
# Build
docker build -t scholarship-agent .

# Run
docker run -e OPENAI_API_KEY=... scholarship-agent

# Or use compose
docker-compose up -d
```

### Environment: Production vs Development
```python
if settings.environment == "production":
    # More logging
    # Stricter validation
    # Better error handling
else:
    # More verbose output
    # Allow test data
```

## Next Steps

1. **Part 2**: Implement SearchAgent with Tavily integration
2. **Part 3**: Implement ExtractionAgent with LLM
3. **Part 4**: Implement GrammarAgent for message improvement
4. **Part 5**: Implement TelegramAgent for publishing
5. **Part 6**: Setup APScheduler for 2x daily runs
6. **Part 7**: Implement duplicate detection
7. **Part 8**: Enhanced logging and error handling
8. **Part 9**: Docker and deployment
9. **Part 10**: GitHub Actions CI/CD

---

Happy coding! 🚀

