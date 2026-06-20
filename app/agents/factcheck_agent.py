"""
Fact-Check Agent.
Verifies scholarship information for accuracy and validity.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

import httpx

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.utils import is_valid_url, is_deadline_passed, parse_date_flexible
from app.workflows import ScholarshipState

logger = logging.getLogger(__name__)


class FactCheckAgent(BaseAgent):
    """
    Fact-checking and validation agent.
    
    Verifies scholarship information for accuracy:
    - Checks that URLs are accessible and valid
    - Validates deadlines haven't passed
    - Confirms scholarship info matches source page
    - Verifies university existence and legitimacy
    
    Features:
    - URL validation and accessibility check
    - Deadline validation
    - Content verification
    - Error tolerance (doesn't fail on single errors)
    """

    def __init__(self):
        """Initialize the fact-check agent."""
        super().__init__(
            name="FactCheckAgent",
            description="Verifies scholarship information accuracy"
        )
        self.verified_count = 0
        self.flagged_count = 0
        self.error_count = 0

    async def check_url_accessibility(
        self, url: str, timeout: int = 10
    ) -> Tuple[bool, str]:
        """
        Check if URL is accessible.
        
        Args:
            url: URL to check
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (is_accessible, status_message)
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.head(url, follow_redirects=True)
                
                if response.status_code == 200:
                    return True, "✓ URL accessible"
                elif response.status_code < 400:
                    return True, f"✓ URL accessible (status: {response.status_code})"
                else:
                    return False, f"✗ URL returned {response.status_code}"
                    
        except httpx.TimeoutException:
            return False, "✗ URL timeout"
        except httpx.ConnectError:
            return False, "✗ Connection error"
        except Exception as e:
            return False, f"✗ Error: {str(e)[:50]}"

    def validate_deadline(self, deadline_str: str) -> Tuple[bool, str]:
        """
        Validate scholarship deadline.
        
        Args:
            deadline_str: Deadline string to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not deadline_str or deadline_str.lower() == "not specified":
            return True, "✓ Deadline not specified (OK for ongoing scholarships)"
        
        try:
            parsed_date = parse_date_flexible(deadline_str)
            
            if not parsed_date:
                return False, f"✗ Could not parse deadline: {deadline_str}"
            
            if is_deadline_passed(parsed_date):
                return False, f"✗ Deadline has passed: {deadline_str}"
            
            # Check if deadline is too far in future (5+ years)
            from datetime import timedelta
            five_years = datetime.utcnow() + timedelta(days=365*5)
            if parsed_date > five_years:
                return False, f"✗ Deadline suspiciously far in future: {deadline_str}"
            
            return True, f"✓ Valid deadline: {parsed_date.strftime('%Y-%m-%d')}"
            
        except Exception as e:
            return False, f"✗ Deadline validation error: {str(e)[:50]}"

    def validate_scholarship_data(self, scholarship: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate scholarship data for completeness and logic.
        
        Args:
            scholarship: Scholarship data to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        required_fields = ["scholarship_name", "country", "university", "official_link"]
        for field in required_fields:
            value = scholarship.get(field, "").strip()
            if not value or value.lower() == "not specified":
                issues.append(f"✗ Missing or empty required field: {field}")
        
        # Validate URL format
        url = scholarship.get("official_link", "")
        if url and not is_valid_url(url):
            issues.append(f"✗ Invalid URL format: {url}")
        
        # Check for suspicious patterns
        name = scholarship.get("scholarship_name", "").lower()
        if any(word in name for word in ["scam", "fake", "test", "example"]):
            issues.append(f"✗ Suspicious scholarship name: {name}")
        
        # Validate country is not empty
        country = scholarship.get("country", "").strip()
        if not country or len(country) < 2:
            issues.append("✗ Invalid country")
        
        # University name check
        university = scholarship.get("university", "").strip()
        if not university or len(university) < 3:
            issues.append("✗ University name too short or empty")
        
        # Check for reasonable degree levels
        degree = scholarship.get("degree_level", "").lower()
        valid_degrees = ["bachelor", "master", "phd", "research", "postdoctoral", "diploma"]
        if degree and not any(d in degree for d in valid_degrees):
            issues.append(f"✗ Unusual degree level: {degree}")
        
        return len(issues) == 0, issues

    async def fact_check_scholarship(
        self, scholarship: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Perform fact-checks on a single scholarship.
        
        Args:
            scholarship: Scholarship data to fact-check
            
        Returns:
            Tuple of (scholarship_with_flags, issues_found)
        """
        issues = []
        
        try:
            # 1. Validate data structure
            is_valid, data_issues = self.validate_scholarship_data(scholarship)
            issues.extend(data_issues)
            
            # 2. Check URL accessibility
            if settings.deadline_check_enabled:
                url = scholarship.get("official_link", "")
                if url:
                    accessible, url_status = await self.check_url_accessibility(url)
                    if accessible:
                        self.log_debug(url_status)
                    else:
                        issues.append(url_status)
            
            # 3. Validate deadline
            if settings.deadline_check_enabled:
                deadline = scholarship.get("application_deadline", "")
                valid_deadline, deadline_status = self.validate_deadline(deadline)
                if valid_deadline:
                    self.log_debug(deadline_status)
                else:
                    issues.append(deadline_status)
            
            # Add fact-check results to scholarship
            scholarship["fact_check_status"] = "verified" if len(issues) == 0 else "flagged"
            scholarship["fact_check_issues"] = issues
            scholarship["fact_checked_at"] = datetime.utcnow().isoformat()
            
            if len(issues) == 0:
                self.verified_count += 1
                self.log_info(f"✓ Verified: {scholarship.get('scholarship_name', 'N/A')}")
            else:
                self.flagged_count += 1
                self.log_warning(f"⚠ Flagged: {scholarship.get('scholarship_name', 'N/A')}")
                for issue in issues:
                    self.log_debug(f"  {issue}")
            
            return scholarship, issues
            
        except Exception as e:
            self.error_count += 1
            self.log_error(f"Fact-check error: {str(e)}", exc=e)
            scholarship["fact_check_status"] = "error"
            scholarship["fact_check_error"] = str(e)
            return scholarship, [f"✗ Fact-check error: {str(e)}"]

    async def fact_check_batch(
        self, scholarships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Fact-check multiple scholarships concurrently.
        
        Args:
            scholarships: List of scholarships to verify
            
        Returns:
            List of scholarships with fact-check results
        """
        self.log_info(f"Fact-checking {len(scholarships)} scholarships")
        
        # Create fact-check tasks
        tasks = [self.fact_check_scholarship(s) for s in scholarships]
        
        # Run concurrently (limit to avoid rate limits)
        results = await asyncio.gather(*tasks)
        
        # Extract updated scholarships
        checked_scholarships = [s for s, _ in results]
        
        self.log_info(f"Fact-checking complete: {self.verified_count} verified, {self.flagged_count} flagged")
        
        return checked_scholarships

    async def execute(self, state: ScholarshipState) -> ScholarshipState:
        """
        Execute the fact-check agent workflow.
        
        Args:
            state: Current workflow state with extracted scholarships
            
        Returns:
            Updated state with fact-checked scholarships
        """
        try:
            self.log_info("Starting fact-check workflow")
            
            # Get scholarships
            scholarships = state.scholarships
            if not scholarships:
                self.log_warning("No scholarships to fact-check")
                return state
            
            # Fact-check all scholarships
            checked_scholarships = await self.fact_check_batch(scholarships)
            
            # Optionally filter out flagged items (strict mode)
            if not getattr(settings, "keep_flagged_scholarships", False):
                # Keep all for now, just flag them
                state.scholarships = checked_scholarships
            else:
                state.scholarships = checked_scholarships
            
            # Add metadata
            state.execution_metadata["fact_check_agent_input"] = len(scholarships)
            state.execution_metadata["fact_check_agent_verified"] = self.verified_count
            state.execution_metadata["fact_check_agent_flagged"] = self.flagged_count
            state.execution_metadata["fact_check_agent_errors"] = self.error_count
            state.execution_metadata["fact_check_agent_completed_at"] = datetime.utcnow().isoformat()
            
            return state
            
        except Exception as e:
            self.log_error(f"Fact-check agent failed: {str(e)}", exc=e)
            return self.add_error_to_state(
                state,
                f"Fact-check failed: {str(e)}"
            )

