"""
Scholarship Extraction Agent.
Uses LLM to extract structured scholarship information from raw content.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain.llms.openai import OpenAI
from langchain.schema import SystemMessage, HumanMessage

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.prompts.extraction_prompt import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT_TEMPLATE,
)
from app.utils import (
    clean_text,
    parse_date_flexible,
    is_valid_url,
    generate_hash,
    truncate_text,
)
from app.workflows import ScholarshipState

logger = logging.getLogger(__name__)


class ExtractionAgent(BaseAgent):
    """
    Extraction agent for structured scholarship data.
    
    Uses OpenAI GPT-4 to intelligently extract scholarship information
    from unstructured web content.
    
    Features:
    - LLM-based data extraction
    - JSON validation and error recovery
    - Deadline parsing and validation
    - Content truncation for token efficiency
    - Retry logic for failed extractions
    - Metadata tracking
    """

    def __init__(self):
        """Initialize the extraction agent."""
        super().__init__(
            name="ExtractionAgent",
            description="Extracts structured scholarship information using LLM"
        )
        self.llm = OpenAI(
            api_key=settings.openai_api_key,
            model_name=settings.openai_model,
            temperature=0,  # Deterministic output for data extraction
            max_tokens=1000,
            request_timeout=settings.llm_timeout,
        )
        self.extraction_count = 0
        self.success_count = 0
        self.error_count = 0

    def validate_extraction(self, data: Dict[str, Any]) -> bool:
        """
        Validate extracted scholarship data.
        
        Args:
            data: Extracted scholarship data
            
        Returns:
            True if data is valid
            
        Checks:
        - Has required fields
        - Fields are not empty
        - URLs are valid
        - Deadlines are parseable
        """
        if not isinstance(data, dict):
            return False
        
        # Check for error marker
        if "error" in data:
            return False
        
        # Check required fields have content
        required_fields = ["scholarship_name", "country", "university", "official_link"]
        for field in required_fields:
            value = data.get(field, "").strip()
            if not value or value.lower() == "not specified":
                self.log_debug(f"Missing required field: {field}")
                return False
        
        # Validate URL
        url = data.get("official_link", "")
        if not is_valid_url(url):
            self.log_debug(f"Invalid URL: {url}")
            return False
        
        return True

    def parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        """
        Parse deadline string to datetime.
        
        Args:
            deadline_str: Deadline string from extraction
            
        Returns:
            Parsed datetime or None
        """
        if not deadline_str or deadline_str.lower() == "not specified":
            return None
        
        try:
            parsed = parse_date_flexible(deadline_str)
            if parsed and parsed > datetime.utcnow():
                return parsed
            return None
        except Exception as e:
            self.log_debug(f"Failed to parse deadline '{deadline_str}': {e}")
            return None

    def sanitize_extraction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and sanitize extracted data.
        
        Args:
            data: Raw extracted data
            
        Returns:
            Cleaned data
        """
        # Clean text fields
        for key in data:
            if isinstance(data[key], str):
                data[key] = clean_text(data[key]).strip()
                # Limit field lengths
                if key != "official_link":
                    data[key] = truncate_text(data[key], max_length=2000)
        
        # Parse deadline
        if "application_deadline" in data:
            deadline_str = data["application_deadline"]
            parsed_deadline = self.parse_deadline(deadline_str)
            if parsed_deadline:
                data["application_deadline"] = parsed_deadline.isoformat()
            else:
                data["application_deadline"] = deadline_str
        
        return data

    async def extract_from_search_result(
        self, result: Dict[str, Any], retry_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Extract scholarship information from a single search result.
        
        Args:
            result: Search result with title, url, content
            retry_count: Current retry attempt (for recursion)
            
        Returns:
            Extracted scholarship data or None if extraction failed
        """
        max_retries = 2
        
        try:
            # Prepare content
            title = result.get("title", "")
            url = result.get("url", "")
            content = result.get("content", "")
            
            # Truncate content to avoid token limits (keep ~3000 chars)
            content = truncate_text(content, max_length=3000, suffix="")
            
            # Prepare prompt
            user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
                title=title,
                url=url,
                content=content
            )
            
            self.log_debug(f"Extracting from: {title[:50]}...")
            
            # Call LLM
            try:
                response = self.llm.predict(
                    text=user_prompt,
                    system_prompt=EXTRACTION_SYSTEM_PROMPT
                )
            except Exception as e:
                # Retry with fallback
                self.log_warning(f"LLM call failed, retry {retry_count + 1}: {str(e)}")
                if retry_count < max_retries:
                    await asyncio.sleep(2)  # Wait before retry
                    return await self.extract_from_search_result(result, retry_count + 1)
                raise
            
            # Parse JSON response
            try:
                # Clean response - remove markdown code blocks if present
                response_text = response.strip()
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                
                extracted_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                self.log_warning(f"Failed to parse JSON response: {e}")
                self.log_debug(f"Response was: {response[:200]}")
                if retry_count < max_retries:
                    await asyncio.sleep(1)
                    return await self.extract_from_search_result(result, retry_count + 1)
                return None
            
            # Check for error marker
            if isinstance(extracted_data, dict) and "error" in extracted_data:
                self.log_debug(f"LLM marked as non-scholarship: {extracted_data['error']}")
                return None
            
            # Validate
            if not self.validate_extraction(extracted_data):
                self.log_debug(f"Validation failed for: {extracted_data.get('scholarship_name', 'N/A')}")
                return None
            
            # Sanitize
            extracted_data = self.sanitize_extraction(extracted_data)
            
            # Add metadata
            extracted_data["source_url"] = url
            extracted_data["extracted_at"] = datetime.utcnow().isoformat()
            extracted_data["hash"] = generate_hash(
                f"{extracted_data.get('scholarship_name')}{url}"
            )
            
            self.success_count += 1
            self.log_info(f"✓ Extracted: {extracted_data.get('scholarship_name', 'N/A')}")
            return extracted_data
            
        except Exception as e:
            self.error_count += 1
            self.log_error(f"Extraction error: {str(e)}", exc=e)
            return None

    async def extract_batch(
        self, results: List[Dict[str, Any]], batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Extract scholarships from multiple search results.
        
        Args:
            results: List of search results
            batch_size: Number of concurrent extractions
            
        Returns:
            List of extracted scholarships
            
        Processes results in batches to manage API rate limits.
        """
        extracted_scholarships = []
        total = len(results)
        
        self.log_info(f"Starting batch extraction of {total} results")
        
        # Process in batches
        for i in range(0, total, batch_size):
            batch = results[i : i + batch_size]
            self.log_info(f"Processing batch {i // batch_size + 1} ({len(batch)} items)")
            
            # Process batch concurrently
            tasks = [self.extract_from_search_result(result) for result in batch]
            batch_results = await asyncio.gather(*tasks)
            
            # Filter out None values
            valid_results = [r for r in batch_results if r is not None]
            extracted_scholarships.extend(valid_results)
            
            self.log_info(f"Batch complete: {len(valid_results)} / {len(batch)} successful")
            
            # Small delay between batches
            if i + batch_size < total:
                await asyncio.sleep(1)
        
        return extracted_scholarships

    async def execute(self, state: ScholarshipState) -> ScholarshipState:
        """
        Execute the extraction agent workflow.
        
        Args:
            state: Current workflow state with search results
            
        Returns:
            Updated state with extracted scholarships
            
        Main flow:
        1. Get search results from state
        2. Extract scholarship information using LLM
        3. Validate and clean data
        4. Update state with extracted scholarships
        """
        try:
            self.log_info("Starting scholarship extraction workflow")
            
            # Get search results
            search_results = state.search_results
            if not search_results:
                self.log_warning("No search results to extract")
                return state
            
            self.log_info(f"Extracting from {len(search_results)} search results")
            
            # Extract scholarships
            extracted = await self.extract_batch(
                search_results,
                batch_size=5
            )
            
            self.log_info(f"Extraction complete: {len(extracted)} valid scholarships")
            
            # Update state
            state.scholarships = extracted
            
            # Add metadata
            state.execution_metadata["extraction_agent_input"] = len(search_results)
            state.execution_metadata["extraction_agent_output"] = len(extracted)
            state.execution_metadata["extraction_agent_success"] = self.success_count
            state.execution_metadata["extraction_agent_errors"] = self.error_count
            if len(search_results) > 0:
                success_rate = (self.success_count / len(search_results)) * 100
                state.execution_metadata["extraction_agent_success_rate"] = f"{success_rate:.1f}%"
            state.execution_metadata["extraction_agent_completed_at"] = datetime.utcnow().isoformat()
            
            return state
            
        except Exception as e:
            self.log_error(f"Extraction agent failed: {str(e)}", exc=e)
            return self.add_error_to_state(
                state,
                f"Extraction failed: {str(e)}"
            )


async def run_extraction_agent_demo():
    """
    Demo function to test the extraction agent.
    
    Usage:
        python -c "
        import asyncio
        from app.agents.extraction_agent import run_extraction_agent_demo
        asyncio.run(run_extraction_agent_demo())
        "
    """
    from app.agents.search_agent import SearchAgent
    from app.workflows import ScholarshipState
    
    print("🔍 Running Extraction Agent Demo...\n")
    
    # First run search
    print("Step 1: Running search...")
    search_agent = SearchAgent()
    state = ScholarshipState()
    state = await search_agent.execute(state)
    
    print(f"Step 2: Extracting from {len(state.search_results)} results...\n")
    
    # Then extract
    extraction_agent = ExtractionAgent()
    state = await extraction_agent.execute(state)
    
    print(f"\n✅ Extraction Complete!")
    print(f"📊 Extracted {len(state.scholarships)} scholarships\n")
    
    # Display results
    for i, scholarship in enumerate(state.scholarships[:3], 1):
        print(f"{i}. {scholarship.get('scholarship_name', 'N/A')}")
        print(f"   Country: {scholarship.get('country', 'N/A')}")
        print(f"   University: {scholarship.get('university', 'N/A')}")
        print(f"   Level: {scholarship.get('degree_level', 'N/A')}")
        print(f"   Deadline: {scholarship.get('application_deadline', 'N/A')}")
        print()


if __name__ == "__main__":
    asyncio.run(run_extraction_agent_demo())

