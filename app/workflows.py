"""
LangGraph workflow orchestration for the Scholarship Agent.
Defines the multi-agent workflow using LangGraph.
"""

import asyncio
import logging
from typing import Annotated, Any, Dict, List

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class ScholarshipState(BaseModel):
    """
    Shared state passed between agents in the workflow.
    Represents the scholarship data and processing metadata.
    """

    # Search Results
    search_results: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Raw search results from web search"
    )
    
    # Extracted Scholarship Info
    scholarships: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Extracted scholarship information"
    )
    
    # Filtered Results
    filtered_scholarships: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Scholarships after filtering and duplicate removal"
    )
    
    # Messages
    telegram_messages: List[str] = Field(
        default_factory=list,
        description="Generated Telegram messages"
    )
    
    # Grammar-corrected Messages
    corrected_messages: List[str] = Field(
        default_factory=list,
        description="Messages after grammar correction"
    )
    
    # Fact-checked Results
    fact_checked_scholarships: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Scholarships after fact-checking"
    )
    
    # Posted Messages
    posted_scholarships: List[str] = Field(
        default_factory=list,
        description="IDs of scholarships successfully posted to Telegram"
    )
    
    # Metadata and Tracking
    search_queries: List[str] = Field(
        default_factory=list,
        description="Search queries used"
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="Errors encountered during processing"
    )
    
    execution_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about workflow execution"
    )

    class Config:
        arbitrary_types_allowed = True


def create_workflow():
    """
    Factory function to create and compile the complete scholarship workflow.
    
    Orchestrates all agents:
    search → extract → fact_check → grammar → publish → database
    
    Returns:
        Compiled LangGraph workflow ready for execution
    """
    from app.agents.search_agent import SearchAgent
    from app.agents.extraction_agent import ExtractionAgent
    from app.agents.factcheck_agent import FactCheckAgent
    from app.agents.grammar_agent import GrammarAgent
    from app.agents.telegram_agent import TelegramAgent

    # Create agent instances
    search_agent = SearchAgent()
    extraction_agent = ExtractionAgent()
    fact_check_agent = FactCheckAgent()
    grammar_agent = GrammarAgent()
    telegram_agent = TelegramAgent()

    # Create workflow nodes that wrap async agents
    async def search_node(state: ScholarshipState) -> ScholarshipState:
        return await search_agent.execute(state)

    async def extract_node(state: ScholarshipState) -> ScholarshipState:
        return await extraction_agent.execute(state)

    async def factcheck_node(state: ScholarshipState) -> ScholarshipState:
        return await fact_check_agent.execute(state)

    async def grammar_node(state: ScholarshipState) -> ScholarshipState:
        return await grammar_agent.execute(state)

    async def publish_node(state: ScholarshipState) -> ScholarshipState:
        return await telegram_agent.execute(state)

    async def database_node(state: ScholarshipState) -> ScholarshipState:
        """
        Store scholarships and messages in database.
        This is a placeholder - actual database storage is done by telegram agent.
        """
        return state

    # Build graph
    graph = StateGraph(ScholarshipState)

    # Add nodes
    graph.add_node("search", search_node)
    graph.add_node("extract", extract_node)
    graph.add_node("fact_check", factcheck_node)
    graph.add_node("grammar", grammar_node)
    graph.add_node("publish", publish_node)
    graph.add_node("database", database_node)

    # Add edges - linear workflow
    graph.add_edge(START, "search")
    graph.add_edge("search", "extract")
    graph.add_edge("extract", "fact_check")
    graph.add_edge("fact_check", "grammar")
    graph.add_edge("grammar", "publish")
    graph.add_edge("publish", "database")
    graph.add_edge("database", END)

    return graph.compile()


def create_minimal_workflow():
    """
    Create a minimal workflow for testing.
    Used during development and testing phases.
    
    Returns:
        A simple workflow graph
    """
    def dummy_node(state: ScholarshipState) -> ScholarshipState:
        """Dummy node for testing."""
        return state

    graph = StateGraph(ScholarshipState)
    graph.add_node("start", dummy_node)
    graph.add_edge(START, "start")
    graph.add_edge("start", END)
    
    return graph.compile()

