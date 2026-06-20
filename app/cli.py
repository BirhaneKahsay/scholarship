"""
CLI commands for the Scholarship Agent.
Provides command-line interface for workflow execution and scheduler management.
"""

import asyncio
import sys
import click
from datetime import datetime
from typing import Optional

from app.config import settings, logger
from app.database.db import init_db
from app.workflows import create_workflow, ScholarshipState
from app.scheduler.scheduler import get_scheduler


@click.group()
@click.version_option(version="2.0.0", prog_name="Scholarship Agent")
def cli():
    """Scholarship Agent CLI - Discover and publish scholarships automatically."""
    pass


@cli.command()
@click.option(
    "--queries",
    "-q",
    multiple=True,
    help="Search queries (can be used multiple times)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run workflow without publishing to Telegram",
)
def run(queries: tuple, dry_run: bool):
    """Run the scholarship discovery workflow once."""
    click.echo("\n" + "=" * 60)
    click.echo("🎓 Scholarship Agent - Single Run Mode")
    click.echo("=" * 60)
    
    try:
        # Initialize database
        init_db()
        click.echo("✅ Database initialized")
        
        # Create workflow
        workflow = create_workflow()
        click.echo("✅ Workflow created")
        
        # Prepare state
        search_queries = list(queries) if queries else []
        initial_state = ScholarshipState(
            search_queries=search_queries,
            execution_metadata={
                "run_type": "manual",
                "started_at": datetime.utcnow().isoformat(),
                "dry_run": dry_run,
            },
        )
        
        click.echo(f"🔍 Starting workflow with {len(search_queries) if search_queries else 'auto'} queries...")
        
        # Execute workflow
        result = workflow.invoke(initial_state.dict())
        
        # Display results
        click.echo("\n" + "=" * 60)
        click.echo("📊 WORKFLOW RESULTS")
        click.echo("=" * 60)
        click.echo(f"🔍 Search Results: {len(result.get('search_results', []))}")
        click.echo(f"📋 Extracted: {len(result.get('scholarships', []))}")
        click.echo(f"✍️  Messages Created: {len(result.get('corrected_messages', []))}")
        click.echo(f"📱 Posted: {len(result.get('posted_scholarships', []))}")
        click.echo(f"❌ Errors: {len(result.get('errors', []))}")
        click.echo("=" * 60)
        
        if result.get("errors"):
            click.echo("\n⚠️  Errors encountered:")
            for error in result.get("errors", [])[:5]:
                click.echo(f"  • {error}")
        
        click.echo("\n✅ Workflow completed successfully\n")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        logger.error(f"Workflow failed: {e}", exc_info=True)
        sys.exit(1)


@cli.group()
def scheduler():
    """Scheduler management commands."""
    pass


@scheduler.command("start")
def scheduler_start():
    """Start the background scheduler (2x daily runs)."""
    click.echo("\n" + "=" * 60)
    click.echo("⏰ Scholarship Scheduler - Starting")
    click.echo("=" * 60)
    
    try:
        # Initialize database
        init_db()
        
        # Get scheduler
        sched = get_scheduler()
        
        # Display configuration
        click.echo(f"\n📋 Scheduler Configuration:")
        click.echo(f"  • First run:  {settings.scheduler_first_run_time} UTC")
        click.echo(f"  • Second run: {settings.scheduler_second_run_time} UTC")
        click.echo(f"  • Timezone:   {settings.scheduler_timezone}")
        
        # Start scheduler
        sched.start()
        
        # Display scheduled jobs
        click.echo(f"\n📅 Scheduled Jobs:")
        for job in sched.get_jobs():
            next_run = job.get("next_run_time", "N/A")
            click.echo(f"  • {job['name']}")
            click.echo(f"    Next run: {next_run}")
        
        click.echo("\n" + "=" * 60)
        click.echo("✅ Scheduler started successfully")
        click.echo("Press Ctrl+C to stop")
        click.echo("=" * 60 + "\n")
        
        # Keep running
        try:
            while True:
                asyncio.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n\nShutting down...")
            sched.stop()
            click.echo("✅ Scheduler stopped")
            
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        logger.error(f"Scheduler startup failed: {e}", exc_info=True)
        sys.exit(1)


@scheduler.command("status")
def scheduler_status():
    """Check scheduler status."""
    try:
        sched = get_scheduler()
        status = sched.get_status()
        
        click.echo("\n" + "=" * 60)
        click.echo("📊 Scheduler Status")
        click.echo("=" * 60)
        click.echo(f"Running: {'✅ Yes' if status['is_running'] else '❌ No'}")
        click.echo(f"Active Jobs: {status['job_count']}")
        
        if status['jobs']:
            click.echo("\n📅 Scheduled Jobs:")
            for job in status['jobs']:
                click.echo(f"  • {job['name']}")
                click.echo(f"    Trigger: {job['trigger']}")
                click.echo(f"    Next run: {job['next_run_time'] or 'Not scheduled'}")
        
        # Show last runs
        last_runs = sched.get_last_runs(limit=5)
        if last_runs:
            click.echo("\n📈 Last 5 Runs:")
            for run in last_runs:
                status_emoji = "✅" if run['status'] == "success" else "❌"
                click.echo(f"  {status_emoji} {run['executed_at']}")
                click.echo(f"     Results: {run['search_count']} searched, "
                          f"{run['scholarship_count']} scholarships, "
                          f"{run['posted_count']} posted")
        
        click.echo("=" * 60 + "\n")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)


@scheduler.command("stop")
def scheduler_stop():
    """Stop the background scheduler."""
    try:
        sched = get_scheduler()
        
        if not sched.is_running:
            click.echo("\n⚠️  Scheduler is not running\n")
            return
        
        sched.stop()
        click.echo("\n✅ Scheduler stopped successfully\n")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)


@scheduler.command("pause")
def scheduler_pause():
    """Pause scheduled jobs (scheduler still running)."""
    try:
        sched = get_scheduler()
        
        if not sched.is_running:
            click.echo("\n⚠️  Scheduler is not running\n")
            return
        
        sched.pause()
        click.echo("\n⏸️  Scheduler paused - jobs will not execute\n")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)


@scheduler.command("resume")
def scheduler_resume():
    """Resume paused scheduled jobs."""
    try:
        sched = get_scheduler()
        
        if not sched.is_running:
            click.echo("\n⚠️  Scheduler is not running\n")
            return
        
        sched.resume()
        click.echo("\n▶️  Scheduler resumed\n")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)


@scheduler.command("run-now")
def scheduler_run_now():
    """Run the workflow immediately (not waiting for schedule)."""
    try:
        sched = get_scheduler()
        
        click.echo("\n🎯 Running workflow immediately...\n")
        
        result = sched.run_now(run_id="cli_manual")
        
        if result:
            click.echo("=" * 60)
            click.echo("📊 RESULTS")
            click.echo("=" * 60)
            click.echo(f"🔍 Search Results: {len(result.get('search_results', []))}")
            click.echo(f"📋 Extracted: {len(result.get('scholarships', []))}")
            click.echo(f"✍️  Messages Created: {len(result.get('corrected_messages', []))}")
            click.echo(f"📱 Posted: {len(result.get('posted_scholarships', []))}")
            click.echo("=" * 60 + "\n")
        else:
            click.echo("❌ Workflow execution failed\n")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        sys.exit(1)


@cli.command()
def init():
    """Initialize the database and create tables."""
    try:
        click.echo("\n🗄️  Initializing database...\n")
        
        init_db()
        
        click.echo("=" * 60)
        click.echo("✅ Database initialized successfully")
        click.echo("=" * 60)
        click.echo("Created tables:")
        click.echo("  • Scholarship")
        click.echo("  • TelegramMessage")
        click.echo("  • ProcessingLog")
        click.echo("  • DuplicateCache")
        click.echo("  • SchedulerRun")
        click.echo("=" * 60 + "\n")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}\n", err=True)
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
def config():
    """Display current configuration."""
    click.echo("\n" + "=" * 60)
    click.echo("⚙️  Configuration Settings")
    click.echo("=" * 60)
    
    click.echo("\n🔑 API Configuration:")
    click.echo(f"  • OpenAI Model: {settings.openai_model}")
    click.echo(f"  • API Timeout: {settings.llm_timeout}s")
    
    click.echo("\n📱 Telegram Configuration:")
    click.echo(f"  • Channel ID: {settings.telegram_channel_id[:10]}...")
    click.echo(f"  • Group ID: {settings.telegram_group_id or 'Not configured'}")
    
    click.echo("\n🗄️  Database Configuration:")
    db_host = settings.database_url.split("@")[1].split(":")[0] if "@" in settings.database_url else "..."
    click.echo(f"  • Host: {db_host}")
    
    click.echo("\n⏰ Scheduler Configuration:")
    click.echo(f"  • Enabled: {'✅ Yes' if settings.scheduler_enabled else '❌ No'}")
    click.echo(f"  • First Run: {settings.scheduler_first_run_time} UTC")
    click.echo(f"  • Second Run: {settings.scheduler_second_run_time} UTC")
    
    click.echo("\n🔍 Search Configuration:")
    click.echo(f"  • Max Results: {settings.max_search_results}")
    click.echo(f"  • Term Rotation: {'✅ Yes' if settings.search_terms_rotation_enabled else '❌ No'}")
    
    click.echo("\n✔️  Fact-Check Configuration:")
    click.echo(f"  • Enabled: {'✅ Yes' if settings.fact_check_enabled else '❌ No'}")
    click.echo(f"  • Deadline Check: {'✅ Yes' if settings.deadline_check_enabled else '❌ No'}")
    
    click.echo("\n🔄 Duplicate Detection:")
    click.echo(f"  • Enabled: {'✅ Yes' if settings.duplicate_check_enabled else '❌ No'}")
    click.echo(f"  • Threshold: {settings.duplicate_threshold * 100:.0f}%")
    
    click.echo("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    cli()
