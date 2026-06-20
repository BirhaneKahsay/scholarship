"""
APScheduler-based job scheduling for the Scholarship Agent.
Handles 2x daily scholarship discovery workflow execution.
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job

from app.config import settings, logger
from app.database.db import SessionLocal
from app.database.models import SchedulerRun
from app.workflows import create_workflow, ScholarshipState


class ScholarshipScheduler:
    """
    Background scheduler for the Scholarship Agent.
    Executes the workflow on a predefined schedule (default: 8 AM and 5 PM UTC).
    """

    def __init__(self):
        """Initialize the scheduler with configuration from settings."""
        self.logger = logging.getLogger(__name__)
        self.scheduler = BackgroundScheduler(daemon=True)
        self.workflow = None
        self.is_running = False
        self.current_job_id = None
        
        self.logger.info("ScholarshipScheduler initialized")

    def _initialize_workflow(self):
        """Lazy-load workflow on first use."""
        if self.workflow is None:
            try:
                self.workflow = create_workflow()
                self.logger.info("Workflow initialized for scheduler")
            except Exception as e:
                self.logger.error(f"Failed to initialize workflow: {e}", exc_info=True)
                raise

    async def _execute_workflow_async(self) -> dict:
        """
        Execute the scholarship workflow.
        
        Returns:
            Dictionary with workflow results
        """
        try:
            self._initialize_workflow()
            
            # Create initial state
            initial_state = ScholarshipState(
                search_queries=[],  # Use rotation from search agent
                execution_metadata={
                    "scheduled_run": True,
                    "scheduled_at": datetime.now().isoformat(),
                },
            )

            self.logger.info("🔄 Executing scheduled workflow...")
            
            # Execute workflow in thread pool
            result = await asyncio.to_thread(
                self.workflow.invoke,
                initial_state.dict()
            )
            
            return result

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}", exc_info=True)
            raise

    def _save_scheduler_run(self, run_data: dict, status: str = "success", error_msg: str = None):
        """
        Save scheduler run record to database.
        
        Args:
            run_data: Workflow result data
            status: "success" or "failed"
            error_msg: Error message if failed
        """
        try:
            session = SessionLocal()
            
            # Count results
            search_count = len(run_data.get("search_results", []))
            scholarship_count = len(run_data.get("scholarships", []))
            posted_count = len(run_data.get("posted_scholarships", []))
            error_count = len(run_data.get("errors", []))
            
            scheduler_run = SchedulerRun(
                status=status,
                search_count=search_count,
                scholarship_count=scholarship_count,
                posted_count=posted_count,
                error_count=error_count,
                error_message=error_msg,
                metadata={
                    "execution_metadata": run_data.get("execution_metadata", {}),
                    "errors": run_data.get("errors", [])[:5],  # Store first 5 errors
                }
            )
            
            session.add(scheduler_run)
            session.commit()
            
            self.logger.info(
                f"✅ Scheduler run saved: {search_count} results, "
                f"{scholarship_count} scholarships, {posted_count} posted"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to save scheduler run: {e}", exc_info=True)
        finally:
            session.close()

    def _job_wrapper(self):
        """
        Wrapper function to execute async workflow in scheduler context.
        APScheduler runs synchronous functions, so we use this wrapper.
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info(f"⏰ SCHEDULED WORKFLOW STARTED at {datetime.utcnow().isoformat()}")
            self.logger.info("=" * 60)
            
            # Run async workflow
            result = asyncio.run(self._execute_workflow_async())
            
            # Save to database
            self._save_scheduler_run(result, status="success")
            
            self.logger.info("=" * 60)
            self.logger.info("✅ SCHEDULED WORKFLOW COMPLETED")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"❌ Scheduled workflow failed: {e}", exc_info=True)
            self._save_scheduler_run({}, status="failed", error_msg=str(e))
            # Don't re-raise - scheduler should continue running

    def start(self):
        """
        Start the background scheduler.
        
        Workflow runs at configured times:
        - First run: 8 AM UTC (configurable via SCHEDULER_FIRST_RUN_TIME)
        - Second run: 5 PM UTC (configurable via SCHEDULER_SECOND_RUN_TIME)
        """
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return

        try:
            # Parse configured times
            first_time = settings.scheduler_first_run_time  # "08:00"
            second_time = settings.scheduler_second_run_time  # "17:00"
            
            first_hour, first_minute = map(int, first_time.split(":"))
            second_hour, second_minute = map(int, second_time.split(":"))
            
            self.logger.info(f"Scheduling workflow at {first_time} and {second_time} UTC")
            
            # Schedule first run
            self.scheduler.add_job(
                self._job_wrapper,
                CronTrigger(hour=first_hour, minute=first_minute),
                id="scholarship_run_1",
                name="Scholarship Discovery - Morning Run",
                replace_existing=True,
                max_instances=1,
            )
            
            # Schedule second run
            self.scheduler.add_job(
                self._job_wrapper,
                CronTrigger(hour=second_hour, minute=second_minute),
                id="scholarship_run_2",
                name="Scholarship Discovery - Evening Run",
                replace_existing=True,
                max_instances=1,
            )
            
            self.logger.info("Jobs scheduled:")
            for job in self.scheduler.get_jobs():
                self.logger.info(f"  • {job.name} - {job.trigger}")
            
            # Start scheduler
            self.scheduler.start()
            self.is_running = True
            
            self.logger.info("🚀 Scheduler started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}", exc_info=True)
            raise

    def stop(self):
        """Stop the background scheduler gracefully."""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return

        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            self.logger.info("✅ Scheduler stopped gracefully")
            
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {e}", exc_info=True)
            raise

    def pause(self):
        """Pause all scheduled jobs without stopping scheduler."""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return

        try:
            self.scheduler.pause()
            self.logger.info("⏸️  Scheduler paused")
            
        except Exception as e:
            self.logger.error(f"Error pausing scheduler: {e}", exc_info=True)

    def resume(self):
        """Resume paused scheduled jobs."""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return

        try:
            self.scheduler.resume()
            self.logger.info("▶️  Scheduler resumed")
            
        except Exception as e:
            self.logger.error(f"Error resuming scheduler: {e}", exc_info=True)

    def run_now(self, run_id: str = "manual") -> Optional[dict]:
        """
        Manually trigger the workflow immediately.
        
        Args:
            run_id: Identifier for this manual run
            
        Returns:
            Workflow result dict, or None on error
        """
        try:
            self.logger.info(f"🎯 Manual workflow execution triggered (ID: {run_id})")
            result = asyncio.run(self._execute_workflow_async())
            self._save_scheduler_run(result, status="success")
            return result
            
        except Exception as e:
            self.logger.error(f"Manual run failed: {e}", exc_info=True)
            self._save_scheduler_run({}, status="failed", error_msg=str(e))
            return None

    def get_jobs(self) -> list:
        """Get list of all scheduled jobs with their details."""
        jobs_info = []
        
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            })
        
        return jobs_info

    def get_status(self) -> dict:
        """Get current scheduler status."""
        return {
            "is_running": self.is_running,
            "job_count": self.scheduler.get_job_count(),
            "jobs": self.get_jobs(),
            "scheduler_state": self.scheduler.state if hasattr(self.scheduler, 'state') else "unknown",
        }

    def get_last_runs(self, limit: int = 10) -> list:
        """
        Get last N scheduler runs from database.
        
        Args:
            limit: Number of runs to retrieve
            
        Returns:
            List of SchedulerRun records
        """
        try:
            session = SessionLocal()
            runs = session.query(SchedulerRun).order_by(
                SchedulerRun.executed_at.desc()
            ).limit(limit).all()
            
            runs_data = [
                {
                    "id": run.id,
                    "status": run.status,
                    "executed_at": run.executed_at.isoformat(),
                    "search_count": run.search_count,
                    "scholarship_count": run.scholarship_count,
                    "posted_count": run.posted_count,
                    "error_count": run.error_count,
                }
                for run in runs
            ]
            
            return runs_data
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve scheduler runs: {e}", exc_info=True)
            return []
        finally:
            session.close()


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> ScholarshipScheduler:
    """Get or create global scheduler instance (singleton)."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ScholarshipScheduler()
    return _scheduler_instance
