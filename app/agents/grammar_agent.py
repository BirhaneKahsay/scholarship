"""
Grammar Correction Agent.
Uses LLM to improve scholarship announcement messages.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

from langchain.llms.openai import OpenAI

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.prompts.grammar_prompt import (
    GRAMMAR_SYSTEM_PROMPT,
    GRAMMAR_USER_PROMPT_TEMPLATE,
)
from app.utils import clean_text, truncate_text
from app.workflows import ScholarshipState

logger = logging.getLogger(__name__)


class GrammarAgent(BaseAgent):
    """
    Grammar and writing improvement agent.
    
    Uses OpenAI GPT-4 to improve scholarship announcement messages.
    Focuses on grammar, clarity, readability, and engagement.
    
    Features:
    - Grammar correction
    - Readability improvement
    - Consistent formatting
    - Emoji standardization
    - Message optimization
    - Retry logic for failed corrections
    """

    def __init__(self):
        """Initialize the grammar agent."""
        super().__init__(
            name="GrammarAgent",
            description="Improves scholarship message grammar and readability"
        )
        self.llm = OpenAI(
            api_key=settings.openai_api_key,
            model_name=settings.openai_model,
            temperature=0.5,  # Slightly creative for better writing
            max_tokens=500,
            request_timeout=settings.llm_timeout,
        )
        self.corrected_count = 0
        self.error_count = 0

    def format_scholarship_for_telegram(self, scholarship: Dict[str, Any]) -> str:
        """
        Format scholarship data into a readable Telegram message.
        
        Args:
            scholarship: Extracted scholarship data
            
        Returns:
            Formatted message string
            
        Creates a well-structured, emoji-enhanced message.
        """
        lines = []
        
        # Country and header
        country = scholarship.get("country", "Unknown")
        country_emojis = {
            "Germany": "🇩🇪",
            "Netherlands": "🇳🇱",
            "France": "🇫🇷",
            "USA": "🇺🇸",
            "United Kingdom": "🇬🇧",
            "Canada": "🇨🇦",
            "Australia": "🇦🇺",
            "Belgium": "🇧🇪",
            "Sweden": "🇸🇪",
            "Switzerland": "🇨🇭",
        }
        emoji = country_emojis.get(country, "🌍")
        
        lines.append(f"{emoji} <b>{country}</b>\n")
        
        # Scholarship name
        name = scholarship.get("scholarship_name", "")
        if name:
            lines.append(f"<b>{name}</b>\n")
        
        # Degree level
        degree = scholarship.get("degree_level", "")
        if degree:
            lines.append(f"🎓 {degree}\n")
        
        # Benefits
        benefits = scholarship.get("benefits", "")
        if benefits and benefits.lower() != "not specified":
            lines.append(f"💰 <b>Benefits</b>")
            # Parse and format benefits
            if isinstance(benefits, str):
                benefit_items = [b.strip() for b in benefits.split(",") if b.strip()]
                if benefit_items:
                    lines.append("\n")
                    for item in benefit_items[:5]:  # Limit to 5 items
                        lines.append(f"✅ {item}\n")
        
        # Eligibility
        eligibility = scholarship.get("eligibility", "")
        if eligibility and eligibility.lower() != "not specified":
            lines.append(f"\n👨‍🎓 <b>Eligibility</b>\n")
            if isinstance(eligibility, str):
                eligibility_items = [e.strip() for e in eligibility.split(",") if e.strip()]
                if eligibility_items:
                    for item in eligibility_items[:5]:  # Limit to 5 items
                        lines.append(f"• {item}\n")
        
        # Required documents
        documents = scholarship.get("required_documents", "")
        if documents and documents.lower() != "not specified":
            lines.append(f"\n📄 <b>Required Documents</b>\n")
            if isinstance(documents, str):
                doc_items = [d.strip() for d in documents.split(",") if d.strip()]
                if doc_items:
                    for item in doc_items[:6]:  # Limit to 6 items
                        lines.append(f"• {item}\n")
        
        # Deadline
        deadline = scholarship.get("application_deadline", "")
        if deadline and deadline.lower() != "not specified":
            lines.append(f"\n📅 <b>Deadline</b>\n{deadline}\n")
        
        # Application process
        process = scholarship.get("application_process", "")
        if process and process.lower() != "not specified":
            lines.append(f"\n📝 <b>How to Apply</b>\n{truncate_text(process, max_length=200)}\n")
        
        # Link
        link = scholarship.get("official_link", "")
        if link:
            lines.append(f"\n🔗 <b><a href='{link}'>Apply Now</a></b>\n")
        
        # Tags
        lines.append("\n")
        tags = []
        if country:
            country_tag = country.replace(" ", "").lower()
            tags.append(f"#{country_tag}")
        
        degree_tag = (degree.split()[0] if degree else "").lower()
        if degree_tag:
            tags.append(f"#{degree_tag}")
        
        tags.append("#scholarship")
        tags.append("#ethiopia")
        
        lines.append(" ".join(tags))
        
        message = "".join(lines)
        return message

    async def correct_message(
        self, message: str, retry_count: int = 0
    ) -> str:
        """
        Correct and improve a message.
        
        Args:
            message: Original message
            retry_count: Retry attempt number
            
        Returns:
            Improved message
        """
        max_retries = 2
        
        try:
            # Prepare prompt
            user_prompt = GRAMMAR_USER_PROMPT_TEMPLATE.format(
                message=message
            )
            
            self.log_debug(f"Correcting message ({len(message)} chars)")
            
            # Call LLM
            try:
                corrected = self.llm.predict(
                    text=user_prompt,
                    system_prompt=GRAMMAR_SYSTEM_PROMPT
                )
            except Exception as e:
                self.log_warning(f"LLM call failed, retry {retry_count + 1}: {str(e)}")
                if retry_count < max_retries:
                    await asyncio.sleep(1)
                    return await self.correct_message(message, retry_count + 1)
                raise
            
            # Clean result
            corrected = corrected.strip()
            
            # Validate (should not be empty)
            if not corrected:
                self.log_warning("LLM returned empty correction")
                return message  # Return original
            
            # Ensure links are preserved
            if "official_link" in str(message).lower() and "http" not in corrected:
                self.log_warning("Link may have been lost in correction")
            
            self.corrected_count += 1
            self.log_debug(f"Correction complete ({len(corrected)} chars)")
            return corrected
            
        except Exception as e:
            self.error_count += 1
            self.log_error(f"Grammar correction error: {str(e)}", exc=e)
            return message  # Return original on error

    async def process_scholarships(
        self, scholarships: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Process scholarships and create improved Telegram messages.
        
        Args:
            scholarships: List of extracted scholarships
            
        Returns:
            List of improved messages
        """
        messages = []
        
        for i, scholarship in enumerate(scholarships, 1):
            try:
                self.log_info(f"Processing {i}/{len(scholarships)}: {scholarship.get('scholarship_name', 'N/A')}")
                
                # Format message
                formatted_msg = self.format_scholarship_for_telegram(scholarship)
                
                # Correct grammar
                corrected_msg = await self.correct_message(formatted_msg)
                
                messages.append(corrected_msg)
                
            except Exception as e:
                self.log_error(f"Failed to process scholarship: {str(e)}", exc=e)
                continue
        
        return messages

    async def execute(self, state: ScholarshipState) -> ScholarshipState:
        """
        Execute the grammar agent workflow.
        
        Args:
            state: Current workflow state with extracted scholarships
            
        Returns:
            Updated state with corrected messages
            
        Main flow:
        1. Get extracted scholarships
        2. Format into Telegram messages
        3. Correct grammar and improve
        4. Update state with corrected messages
        """
        try:
            self.log_info("Starting grammar correction workflow")
            
            # Get scholarships
            scholarships = state.scholarships
            if not scholarships:
                self.log_warning("No scholarships to correct")
                return state
            
            self.log_info(f"Correcting {len(scholarships)} scholarship messages")
            
            # Process and correct
            corrected_messages = await self.process_scholarships(scholarships)
            
            self.log_info(f"Grammar correction complete: {len(corrected_messages)} messages")
            
            # Update state
            state.corrected_messages = corrected_messages
            
            # Add metadata
            state.execution_metadata["grammar_agent_input"] = len(scholarships)
            state.execution_metadata["grammar_agent_output"] = len(corrected_messages)
            state.execution_metadata["grammar_agent_corrected"] = self.corrected_count
            state.execution_metadata["grammar_agent_errors"] = self.error_count
            state.execution_metadata["grammar_agent_completed_at"] = datetime.utcnow().isoformat()
            
            return state
            
        except Exception as e:
            self.log_error(f"Grammar agent failed: {str(e)}", exc=e)
            return self.add_error_to_state(
                state,
                f"Grammar correction failed: {str(e)}"
            )


async def run_grammar_agent_demo():
    """
    Demo function to test the grammar agent.
    """
    from app.agents.search_agent import SearchAgent
    from app.agents.extraction_agent import ExtractionAgent
    from app.workflows import ScholarshipState
    
    print("🔍 Running Grammar Agent Demo...\n")
    
    # First run search and extraction
    print("Step 1: Running search...")
    search_agent = SearchAgent()
    state = ScholarshipState()
    state = await search_agent.execute(state)
    
    print(f"Step 2: Extracting from {len(state.search_results)} results...")
    extraction_agent = ExtractionAgent()
    state = await extraction_agent.execute(state)
    
    print(f"Step 3: Correcting {len(state.scholarships)} messages...\n")
    
    # Then correct grammar
    grammar_agent = GrammarAgent()
    state = await grammar_agent.execute(state)
    
    print(f"\n✅ Grammar Correction Complete!")
    print(f"📊 Corrected {len(state.corrected_messages)} messages\n")
    
    # Display results
    for i, msg in enumerate(state.corrected_messages[:2], 1):
        print(f"--- Message {i} ---")
        print(msg)
        print()


if __name__ == "__main__":
    asyncio.run(run_grammar_agent_demo())

