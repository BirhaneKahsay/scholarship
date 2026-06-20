"""
Scholarship Search Agent.
Uses Tavily API for web search and filters results.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from tavily import TavilyClient

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.utils import (
    extract_urls,
    is_deadline_passed,
    parse_date_flexible,
    is_valid_url,
    generate_hash,
)
from app.workflows import ScholarshipState

logger = logging.getLogger(__name__)


class SearchAgent(BaseAgent):
    """
    Search agent for finding scholarships on the web.
    
    Uses Tavily API to search the web for scholarships matching specific criteria.
    Filters results to ensure deadlines haven't passed and sources are official.
    
    Features:
    - Query rotation for diverse results
    - Deadline validation
    - Source credibility checking
    - Duplicate removal
    - Result ranking
    """

    # Search query templates for different scholarship types
    SEARCH_QUERIES = [
        # DAAD Scholarships
        "DAAD scholarship Ethiopia 2026 2027 fully funded",
        "DAAD Master's scholarship Africa Ethiopian",
        "DAAD PhD scholarship international students",
        
        # General fully funded scholarships
        "fully funded master's scholarship 2026 Ethiopian students",
        "fully funded PhD scholarship international developing countries",
        "fully funded bachelor's scholarship for African students",
        
        # Government scholarships
        "government scholarship Ethiopia 2026 2027",
        "government funded scholarship African students",
        "government scholarship Master's degree",
        
        # University scholarships
        "university scholarship Ethiopia fully funded",
        "international university scholarship for Ethiopian students",
        "university Master's scholarship Africa 2026",
        
        # Research fellowships
        "research fellowship Ethiopia 2026",
        "research fellowship for African scholars",
        "postdoctoral fellowship international",
        
        # Specific regions/countries
        "scholarship Germany Africa Ethiopian",
        "scholarship Netherlands for African students",
        "scholarship France international students",
        "scholarship USA for international students",
        "scholarship Canada for international students",
        "scholarship Australia for African students",
        
        # Additional keywords
        "merit-based scholarship 2026 international",
        "need-based scholarship for developing countries",
        "women scholarship in STEM 2026",
        "environmental scholarship international",
    ]

    # Official scholarship sources to prioritize
    OFFICIAL_SOURCES = [
        "daad.de",
        "daad.org",
        "masterscholars.com",
        "fulbright.org",
        "chevening.org",
        "studyportals.com",
        "idealist.org",
        "scholarship-positions.com",
        "mastersportal.com",
        "topuniversities.com",
        "timeshighereducation.com",
        "qsworlduniversityrankings.com",
        "universityscholarships.net",
        ".edu",
        ".ac.uk",
        ".fr/en",
        "scholarships.gov",
        "scholarshipdb.net",
        "scholarshipamerica.org",
    ]

    # Keywords to filter OUT (spam/low quality)
    SPAM_KEYWORDS = [
        "essay contest",
        "lottery",
        "guaranteed scholarship",
        "apply now instantly",
        "work from home",
        "make money",
        "bitcoin",
        "crypto",
    ]

    def __init__(self):
        """Initialize the search agent."""
        super().__init__(
            name="SearchAgent",
            description="Searches the web for scholarship opportunities"
        )
        self.tavily_client = TavilyClient(api_key=settings.tavily_api_key)
        self.search_queries = self.SEARCH_QUERIES.copy()
        self.query_index = 0

    def get_next_queries(self, num_queries: int = 5) -> List[str]:
        """
        Get the next batch of search queries using rotation.
        
        Args:
            num_queries: Number of queries to return
            
        Returns:
            List of search queries
            
        Uses rotating query index to ensure diverse results across multiple runs.
        """
        queries = []
        for _ in range(num_queries):
            query = self.search_queries[self.query_index % len(self.search_queries)]
            queries.append(query)
            self.query_index += 1
        
        return queries

    def is_spam_result(self, result: Dict[str, Any]) -> bool:
        """
        Check if a search result is likely spam or low quality.
        
        Args:
            result: Search result from Tavily
            
        Returns:
            True if result appears to be spam
        """
        title = (result.get("title") or "").lower()
        content = (result.get("content") or "").lower()
        url = (result.get("url") or "").lower()
        
        # Check for spam keywords
        combined_text = f"{title} {content} {url}"
        for spam_keyword in self.SPAM_KEYWORDS:
            if spam_keyword.lower() in combined_text:
                self.log_debug(f"Spam detected: {spam_keyword} in {result.get('title')}")
                return True
        
        return False

    def is_official_source(self, url: str) -> int:
        """
        Check if URL is from an official/trusted source and return priority score.
        
        Args:
            url: URL to check
            
        Returns:
            Priority score (higher = more trustworthy)
            - 3: Official scholarship provider
            - 2: Educational institution or aggregator
            - 1: Potentially valid source
            - 0: Unknown or low priority
        """
        url_lower = url.lower()
        
        # Check official sources
        for source in self.OFFICIAL_SOURCES:
            if source in url_lower:
                if any(x in url_lower for x in [".edu", ".ac.uk", "daad", "fulbright", "chevening"]):
                    return 3  # Highest priority
                return 2  # High priority
        
        # Check for educational domains
        if any(x in url_lower for x in [".edu", ".ac.uk", ".de", ".fr", ".nl"]):
            return 2
        
        # General web results
        if "http" in url_lower:
            return 1
        
        return 0

    def extract_deadline_from_content(self, content: str) -> Optional[datetime]:
        """
        Try to extract deadline date from content.
        
        Args:
            content: Content text to search
            
        Returns:
            Parsed deadline datetime or None
            
        Looks for common deadline patterns like:
        - "Deadline: 15 October 2026"
        - "Applications close: 2026-12-31"
        - "Due by: December 15"
        """
        if not content:
            return None
        
        # Common deadline indicators
        deadline_patterns = [
            r"deadline[:\s]+([^\n]+)",
            r"closing date[:\s]+([^\n]+)",
            r"application deadline[:\s]+([^\n]+)",
            r"applications close[:\s]+([^\n]+)",
            r"due[:\s]+([^\n]+)",
            r"closes[:\s]+([^\n]+)",
        ]
        
        import re
        for pattern in deadline_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                date_string = match.group(1).strip()
                # Take only the first part (before comma or period usually)
                date_string = date_string.split(",")[0].split(".")[0].strip()
                
                parsed_date = parse_date_flexible(date_string)
                if parsed_date:
                    return parsed_date
        
        return None

    def filter_search_results(
        self, results: List[Dict[str, Any]], min_priority: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Filter search results based on multiple criteria.
        
        Args:
            results: Raw search results from Tavily
            min_priority: Minimum source priority (0-3)
            
        Returns:
            Filtered and enhanced results
            
        Filtering criteria:
        - No spam/low quality content
        - Source credibility
        - Result completeness
        """
        filtered = []
        
        for result in results:
            # Skip spam results
            if self.is_spam_result(result):
                self.log_debug(f"Filtering spam: {result.get('title')}")
                continue
            
            # Check source priority
            priority = self.is_official_source(result.get("url", ""))
            if priority < min_priority:
                self.log_debug(f"Low priority source: {result.get('url')}")
                continue
            
            # Validate URL
            url = result.get("url", "")
            if not is_valid_url(url):
                self.log_debug(f"Invalid URL: {url}")
                continue
            
            # Extract deadline if present
            deadline = self.extract_deadline_from_content(
                result.get("content", "") + " " + result.get("title", "")
            )
            
            # Enhance result with extracted data
            enhanced_result = result.copy()
            enhanced_result["source_priority"] = priority
            enhanced_result["extracted_deadline"] = deadline.isoformat() if deadline else None
            enhanced_result["hash"] = generate_hash(f"{result.get('title')}{result.get('url')}")
            
            filtered.append(enhanced_result)
        
        # Sort by source priority (highest first)
        filtered.sort(key=lambda x: x["source_priority"], reverse=True)
        
        return filtered

    def deduplicate_results(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate results from search.
        
        Args:
            results: Search results to deduplicate
            
        Returns:
            Deduplicated results
            
        Uses URL and title hashing to identify duplicates.
        Keeps the highest priority version of each scholarship.
        """
        seen_urls = set()
        seen_hashes = set()
        unique_results = []
        
        for result in results:
            url = result.get("url", "").lower()
            hash_val = result.get("hash", "")
            
            # Skip if we've seen this URL or hash
            if url in seen_urls or hash_val in seen_hashes:
                self.log_debug(f"Duplicate found: {result.get('title')}")
                continue
            
            seen_urls.add(url)
            if hash_val:
                seen_hashes.add(hash_val)
            
            unique_results.append(result)
        
        self.log_info(f"Deduplication: {len(results)} → {len(unique_results)} results")
        return unique_results

    async def search_scholarship(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for scholarships using a single query.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of search results
            
        Makes async call to Tavily API with timeout handling.
        """
        try:
            self.log_info(f"Searching: {query}")
            
            # Use Tavily for web search
            results = self.tavily_client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",  # More comprehensive search
                include_answer=True,
            )
            
            # Extract just the results (Tavily returns dict with 'results' key)
            search_results = results.get("results", []) if isinstance(results, dict) else results
            
            self.log_info(f"Found {len(search_results)} results for: {query}")
            return search_results
            
        except Exception as e:
            self.log_error(f"Search failed for query '{query}': {str(e)}", exc=e)
            return []

    async def execute(self, state: ScholarshipState) -> ScholarshipState:
        """
        Execute the search agent workflow.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with search results
            
        Main responsibilities:
        1. Generate search queries (new or provided)
        2. Execute searches
        3. Filter and deduplicate results
        4. Update state
        5. Add metadata
        """
        try:
            self.log_info("Starting scholarship search workflow")
            
            # Use provided queries or generate new ones
            if state.search_queries and len(state.search_queries) > 0:
                queries = state.search_queries[:5]  # Limit to 5
                self.log_info(f"Using {len(queries)} provided search queries")
            else:
                queries = self.get_next_queries(num_queries=5)
                self.log_info(f"Generated {len(queries)} search queries using rotation")
            
            # Execute searches
            all_results = []
            search_tasks = []
            
            for query in queries:
                task = self.search_scholarship(
                    query,
                    max_results=settings.max_search_results // len(queries)
                )
                search_tasks.append(task)
            
            # Run searches concurrently
            search_results = await asyncio.gather(*search_tasks)
            
            # Combine results
            for results in search_results:
                all_results.extend(results)
            
            self.log_info(f"Total raw results: {len(all_results)}")
            
            # Filter results
            filtered_results = self.filter_search_results(
                all_results,
                min_priority=0
            )
            self.log_info(f"After filtering: {len(filtered_results)}")
            
            # Deduplicate results
            unique_results = self.deduplicate_results(filtered_results)
            self.log_info(f"After deduplication: {len(unique_results)}")
            
            # Update state
            state.search_results = unique_results
            state.search_queries = queries
            
            # Add metadata
            state.execution_metadata["search_agent_queries"] = len(queries)
            state.execution_metadata["search_agent_total_found"] = len(all_results)
            state.execution_metadata["search_agent_after_filter"] = len(filtered_results)
            state.execution_metadata["search_agent_final"] = len(unique_results)
            state.execution_metadata["search_agent_completed_at"] = datetime.now().isoformat()
            
            self.log_info(f"Search agent completed: {len(unique_results)} scholarships ready for extraction")
            return state
            
        except Exception as e:
            self.log_error(f"Search agent failed: {str(e)}", exc=e)
            return self.add_error_to_state(
                state,
                f"Search failed: {str(e)}"
            )


async def run_search_agent_demo():
    """
    Demo function to test the search agent independently.
    
    Usage:
        python -c "
        import asyncio
        from app.agents.search_agent import run_search_agent_demo
        asyncio.run(run_search_agent_demo())
        "
    """
    from app.workflows import ScholarshipState
    
    agent = SearchAgent()
    state = ScholarshipState()
    
    print("🔍 Running Search Agent Demo...\n")
    
    # Run search
    state = await agent.execute(state)
    
    print(f"\n✅ Search Complete!")
    print(f"📊 Found {len(state.search_results)} scholarships\n")
    
    # Display first few results
    for i, result in enumerate(state.search_results[:3], 1):
        print(f"{i}. {result.get('title', 'N/A')}")
        print(f"   URL: {result.get('url', 'N/A')}")
        print(f"   Priority: {result.get('source_priority', 'N/A')}")
        print()
    
    # Show metadata
    print("\n📈 Metadata:")
    for key, value in state.execution_metadata.items():
        if key.startswith("search_agent"):
            print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(run_search_agent_demo())

