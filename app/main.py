"""
Main entry point for the Scholarship Agent application.
Initializes the system and coordinates all components.
Supports both one-time workflow execution and background scheduling.
"""

import asyncio
import logging
import sys
from datetime import datetime

from app.config import settings, logger
from app.database.db import init_db, close_db
from app.workflows import create_workflow, ScholarshipState
from app.scheduler.scheduler import get_scheduler


class ScholarshipAgent:
    """
    Main scholarship agent orchestrator.
    Coordinates scheduling, workflow execution, and monitoring.
    """

    def __init__(self):
        """Initialize the scholarship agent."""
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing Scholarship Agent in {settings.environment} environment")
        
        # Initialize database
        try:
            init_db()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

        # Create workflow
        try:
            self.workflow = create_workflow()
            self.logger.info("Complete workflow created and compiled")
        except Exception as e:
            self.logger.error(f"Failed to create workflow: {e}")
            raise

    async def run_workflow(self, search_queries: list = None) -> dict:
        """
        Execute the complete scholarship agent workflow.
        
        Args:
            search_queries: Optional list of search queries. If None, uses rotation.
            
        Returns:
            Dictionary with workflow results and metadata
            
        Workflow:
        1. Search: Find scholarships on web
        2. Extract: Parse scholarship details
        3. Fact-Check: Verify information
        4. Grammar: Improve message quality
        5. Publish: Send to Telegram
        6. Database: Store for later
            
        Example:
            results = await agent.run_workflow([
                "DAAD scholarship Ethiopia",
                "Fully funded master's scholarship Africa"
            ])
        """
        self.logger.info("=" * 60)
        self.logger.info("🚀 STARTING SCHOLARSHIP AGENT WORKFLOW")
        self.logger.info("=" * 60)
        
        try:
            # Create initial state
            initial_state = ScholarshipState(
                search_queries=search_queries or [],
                execution_metadata={
                    "workflow_started_at": datetime.now().isoformat(),
                    "environment": settings.environment,
                },
            )

            self.logger.info(f"Workflow state initialized")
            
            # Execute workflow
            self.logger.info("Invoking LangGraph workflow...")
            final_state = await self.workflow.ainvoke(
                    initial_state.model_dump()
                )
                            
            result_state = ScholarshipState(**final_state)

            # Log completion
            self.logger.info("=" * 60)
            self.logger.info("✅ WORKFLOW COMPLETED SUCCESSFULLY")
            self.logger.info("=" * 60)
            
            # Print summary
            print("\n📊 WORKFLOW SUMMARY")
            print("=" * 60)
            print(f"🔍 Search Results: {len(result_state.search_results)}")
            print(f"📋 Extracted: {len(result_state.scholarships)}")
            print(f"✍️ Messages Created: {len(result_state.corrected_messages)}")
            print(f"📱 Posted to Telegram: {len(result_state.posted_scholarships)}")
            print(f"❌ Errors: {len(result_state.errors)}")
            print("=" * 60)
            
            # Print metadata
            if result_state.execution_metadata:
                print("\n📈 EXECUTION METADATA")
                print("=" * 60)
                for key, value in sorted(result_state.execution_metadata.items()):
                    print(f"  {key}: {value}")
                print("=" * 60)
            
            # Print errors if any
            if result_state.errors:
                print("\n⚠️ ERRORS ENCOUNTERED")
                print("=" * 60)
                for error in result_state.errors:
                    print(f"  • {error}")
                print("=" * 60)
            
            return result_state.model_dump()

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}", exc_info=True)
            print(f"\n❌ WORKFLOW FAILED: {str(e)}\n")
            raise

    def shutdown(self):
        """Gracefully shutdown the agent."""
        self.logger.info("Shutting down Scholarship Agent")
        close_db()
        self.logger.info("Database connection closed")


async def main():
    """Main async entry point."""
    logger.info("=" * 60)
    logger.info("Scholarship Agent v2.0 - Complete Pipeline")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug Mode: {settings.debug}")
    logger.info(f"OpenAI Model: {settings.openai_model}")
    logger.info(f"Scheduler Enabled: {settings.scheduler_enabled}")
    logger.info("=" * 60)

    # Create agent
    agent = ScholarshipAgent()

    # Optional: Use custom search queries or leave empty for rotation
    test_queries = [
        "DAAD scholarship Ethiopia 2026 Master's",
        "Fully funded PhD scholarship international students",
    ]

    try:
        # Run complete workflow
        results = await agent.run_workflow(search_queries=test_queries)
        
        # Print top scholarships found
        if results.get("posted_scholarships"):
            print("\n🎓 TOP SCHOLARSHIPS POSTED")
            print("=" * 60)
            for scholarship in results.get("posted_scholarships", [])[:5]:
                print(f"  ✓ {scholarship}")
            print("=" * 60)

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        raise

    finally:
        agent.shutdown()


def main_sync():
    """Synchronous entry point for script execution."""
    asyncio.run(main())


def cli_entry():
    """Command line interface entrypoint.

    Commands:
      run           - Run the workflow once (default)
      scheduler     - Manage background scheduler (start/status/run-now/stop)
    """
    import argparse
    import time

    parser = argparse.ArgumentParser(prog="scholarship-agent")
    subparsers = parser.add_subparsers(dest="command")

    # run command
    run_parser = subparsers.add_parser("run", help="Run the workflow once")
    run_parser.add_argument("--queries", nargs="*", help="Optional search queries")

    # scheduler command
    sched_parser = subparsers.add_parser("scheduler", help="Manage the background scheduler")
    sched_parser.add_argument("action", choices=["start", "status", "run-now", "stop"], help="Scheduler action")

    args = parser.parse_args()

    if args.command in (None, "run"):
        # Default: run once
        queries = getattr(args, "queries", None)
        asyncio.run(main()) if queries is None else asyncio.run(_run_with_queries(args.queries))
        return

    if args.command == "scheduler":
        sched = get_scheduler()

        if args.action == "start":
            try:
                sched.start()
                # Keep process alive so BackgroundScheduler can run
                print("Scheduler started. Press Ctrl+C to exit and stop scheduler.")
                try:
                    while True:
                        time.sleep(3600)
                except KeyboardInterrupt:
                    print("Keyboard interrupt received. Stopping scheduler...")
                    sched.stop()
            except Exception as e:
                print(f"Failed to start scheduler: {e}")

        elif args.action == "status":
            status = sched.get_status()
            print("Scheduler status:")
            for k, v in status.items():
                print(f"  {k}: {v}")

        elif args.action == "run-now":
            print("Triggering immediate run...")
            result = sched.run_now(run_id="cli")
            if result:
                print("Run completed. Summary:")
                print(f"  Search results: {len(result.get('search_results', []))}")
                print(f"  Scholarships: {len(result.get('scholarships', []))}")
                print(f"  Posted: {len(result.get('posted_scholarships', []))}")
            else:
                print("Run failed. Check logs for details.")

        elif args.action == "stop":
            sched.stop()
            print("Scheduler stopped.")


async def _run_with_queries(queries: list):
    """Run workflow with provided queries and print summary."""
    agent = ScholarshipAgent()
    try:
        await agent.run_workflow(search_queries=queries)
    finally:
        agent.shutdown()


if __name__ == "__main__":
    cli_entry()

