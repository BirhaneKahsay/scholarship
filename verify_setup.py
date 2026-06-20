#!/usr/bin/env python3
"""
Setup verification script for Scholarship Agent.
Validates all configurations and dependencies.
"""

import sys
import os
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_check(message, status, details=""):
    """Print a check result."""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {message}")
    if details:
        print(f"   {details}")


def check_python_version():
    """Check Python version."""
    print_header("Python Version")
    version = sys.version_info
    min_version = (3, 10)
    
    if version >= min_version:
        print_check(
            f"Python version {version.major}.{version.minor}.{version.micro}",
            True,
            "✓ Required: 3.10+"
        )
        return True
    else:
        print_check(
            f"Python version {version.major}.{version.minor}.{version.micro}",
            False,
            f"✗ Required: 3.10+, found: {version.major}.{version.minor}"
        )
        return False


def check_dependencies():
    """Check all required packages."""
    print_header("Python Dependencies")
    
    required_packages = [
        ("langgraph", "LangGraph"),
        ("langchain", "LangChain"),
        ("openai", "OpenAI"),
        ("tavily", "Tavily Search"),
        ("telegram", "Telegram Bot"),
        ("sqlalchemy", "SQLAlchemy"),
        ("psycopg2", "PostgreSQL Driver"),
        ("dotenv", "Python-dotenv"),
        ("pydantic", "Pydantic"),
        ("apscheduler", "APScheduler"),
    ]
    
    all_ok = True
    for package, name in required_packages:
        try:
            __import__(package)
            print_check(f"{name:.<40}", True)
        except ImportError:
            print_check(f"{name:.<40}", False, "Run: pip install -r requirements.txt")
            all_ok = False
    
    return all_ok


def check_environment_file():
    """Check .env file."""
    print_header("Environment Configuration")
    
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    # Check .env exists
    if env_path.exists():
        print_check(".env file exists", True)
    else:
        print_check(".env file exists", False, "Run: cp .env.example .env")
        return False
    
    # Check .env.example exists
    if env_example_path.exists():
        print_check(".env.example template exists", True)
    else:
        print_check(".env.example template exists", False)
    
    # Check required variables
    try:
        from app.config import settings
        
        required_vars = [
            ("OPENAI_API_KEY", "OpenAI API Key"),
            ("TAVILY_API_KEY", "Tavily API Key"),
            ("TELEGRAM_BOT_TOKEN", "Telegram Bot Token"),
            ("TELEGRAM_CHANNEL_ID", "Telegram Channel ID"),
            ("DATABASE_URL", "PostgreSQL URL"),
        ]
        
        all_ok = True
        for var, name in required_vars:
            try:
                value = getattr(settings, var.lower())
                if value and value != f"your-{var.lower()}" and not value.startswith("sk-your"):
                    print_check(f"{name:.<40}", True, "✓ Configured")
                else:
                    print_check(f"{name:.<40}", False, "⚠ Not configured or placeholder value")
                    all_ok = False
            except Exception as e:
                print_check(f"{name:.<40}", False, f"Error: {str(e)}")
                all_ok = False
        
        return all_ok
    except Exception as e:
        print_check("Load .env", False, f"Error: {str(e)}")
        return False


def check_database():
    """Check database connection."""
    print_header("Database Connection")
    
    try:
        from app.config import settings
        from sqlalchemy import create_engine, text
        
        # Create engine
        engine = create_engine(settings.database_url)
        
        # Try to connect
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            if result:
                print_check("PostgreSQL Connection", True, "✓ Connected successfully")
                
                # Check tables
                try:
                    from app.database.models import Scholarship
                    inspector_result = connection.execute(text(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                    ))
                    tables = [row[0] for row in inspector_result]
                    
                    if len(tables) > 0:
                        print_check(
                            f"Database Tables",
                            True,
                            f"✓ Found {len(tables)} tables"
                        )
                    else:
                        print_check(
                            f"Database Tables",
                            False,
                            "No tables found. Run: python -c 'from app.database.db import init_db; init_db()'"
                        )
                        return False
                except Exception as e:
                    print_check("Database Tables Check", False, f"Error: {str(e)}")
                    return False
                
                return True
    except Exception as e:
        print_check("PostgreSQL Connection", False, f"Error: {str(e)}")
        print("  Make sure PostgreSQL is running and DATABASE_URL is correct")
        return False


def check_openai():
    """Check OpenAI connection."""
    print_header("OpenAI API")
    
    try:
        from app.config import settings
        from openai import OpenAI
        
        client = OpenAI(api_key=settings.openai_api_key)
        
        # Test connection
        try:
            response = client.models.list()
            if response:
                print_check("OpenAI Connection", True, "✓ API key valid")
                return True
        except Exception as e:
            print_check("OpenAI Connection", False, f"Invalid API key: {str(e)}")
            return False
    except Exception as e:
        print_check("OpenAI Setup", False, f"Error: {str(e)}")
        return False


def check_tavily():
    """Check Tavily API."""
    print_header("Tavily Web Search API")
    
    try:
        from app.config import settings
        from tavily import TavilyClient
        
        client = TavilyClient(api_key=settings.tavily_api_key)
        
        # Test search
        try:
            results = client.search("test", max_results=1)
            if results or results is not None:
                print_check("Tavily Search API", True, "✓ API key valid")
                return True
        except Exception as e:
            print_check("Tavily Search API", False, f"Error: {str(e)}")
            return False
    except Exception as e:
        print_check("Tavily Setup", False, f"Error: {str(e)}")
        return False


def check_telegram():
    """Check Telegram Bot."""
    print_header("Telegram Bot")
    
    try:
        from app.config import settings
        from telegram import Bot
        
        bot = Bot(token=settings.telegram_bot_token)
        
        # Test connection
        try:
            me = bot.get_me()
            if me:
                print_check("Telegram Bot Connection", True, f"✓ Bot: @{me.username}")
                print_check("Telegram Channel ID", True, f"✓ Channel: {settings.telegram_channel_id}")
                return True
        except Exception as e:
            print_check("Telegram Bot Connection", False, f"Error: {str(e)}")
            return False
    except Exception as e:
        print_check("Telegram Setup", False, f"Error: {str(e)}")
        return False


def check_project_structure():
    """Check project structure."""
    print_header("Project Structure")
    
    required_files = [
        ("app/__init__.py", "App package"),
        ("app/config.py", "Configuration"),
        ("app/main.py", "Entry point"),
        ("app/workflows.py", "LangGraph workflow"),
        ("app/database/models.py", "Database models"),
        ("app/database/db.py", "Database connection"),
        ("app/agents/base_agent.py", "Base agent class"),
        ("requirements.txt", "Dependencies"),
        (".env", "Environment file"),
        ("README.md", "Documentation"),
    ]
    
    all_ok = True
    for file_path, description in required_files:
        if Path(file_path).exists():
            print_check(f"{description:.<40}", True)
        else:
            print_check(f"{description:.<40}", False, f"Missing: {file_path}")
            all_ok = False
    
    return all_ok


def main():
    """Run all checks."""
    print_header("Scholarship Agent - Setup Verification")
    print("This script validates your Scholarship Agent installation.\n")
    
    results = []
    
    # Run checks
    results.append(("Python Version", check_python_version()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("Project Structure", check_project_structure()))
    results.append(("Environment File", check_environment_file()))
    
    # Optional checks (may fail if services not running)
    try:
        results.append(("Database", check_database()))
    except Exception:
        pass
    
    try:
        results.append(("OpenAI API", check_openai()))
    except Exception:
        pass
    
    try:
        results.append(("Tavily API", check_tavily()))
    except Exception:
        pass
    
    try:
        results.append(("Telegram Bot", check_telegram()))
    except Exception:
        pass
    
    # Summary
    print_header("Setup Verification Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:.<50} {check_name}")
    
    print(f"\nTotal: {passed}/{total} checks passed\n")
    
    if passed == total:
        print("🎉 Setup is complete! You're ready to go.")
        print("\nNext steps:")
        print("1. Read QUICKSTART.md for first-time setup")
        print("2. Run: python -m app.main")
        print("3. Proceed to Part 2: Scholarship Search Agent")
        return 0
    else:
        print("⚠️  Some checks failed. Please review the errors above.")
        print("\nFor help:")
        print("- See QUICKSTART.md for setup instructions")
        print("- See README.md for detailed documentation")
        return 1


if __name__ == "__main__":
    sys.exit(main())

