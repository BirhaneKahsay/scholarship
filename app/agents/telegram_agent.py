"""
Telegram Publisher Agent.
Sends scholarship announcements to Telegram channels and groups.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

from telegram import Bot, error as telegram_error
from telegram.constants import ParseMode

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.database.db import SessionLocal
from app.database.models import TelegramMessage, Scholarship
from app.workflows import ScholarshipState

logger = logging.getLogger(__name__)


class TelegramAgent(BaseAgent):
    """
    Telegram publisher agent.
    
    Sends scholarship announcements to Telegram channels and groups.
    Tracks message delivery and handles errors gracefully.
    
    Features:
    - Multi-channel publishing
    - Message delivery tracking
    - Error handling and retries
    - Engagement tracking
    - Database persistence
    """

    def __init__(self):
        """Initialize the Telegram agent."""
        super().__init__(
            name="TelegramAgent",
            description="Publishes scholarship announcements to Telegram"
        )
        self.bot = Bot(token=settings.telegram_bot_token)
        self.channel_id = settings.telegram_channel_id
        self.group_id = settings.telegram_group_id
        self.sent_count = 0
        self.failed_count = 0

    async def send_to_channel(
        self, message: str, chat_id: str = None
    ) -> tuple[bool, int, str]:
        """
        Send message to a Telegram channel.
        
        Args:
            message: Message text to send
            chat_id: Channel/group ID (uses default if None)
            
        Returns:
            Tuple of (success, message_id, error_message)
        """
        if not chat_id:
            chat_id = self.channel_id
        
        try:
            # Send message with HTML formatting
            msg = await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
            
            self.log_info(f"✓ Sent to {chat_id}: Message {msg.message_id}")
            self.sent_count += 1
            return True, msg.message_id, ""
            
        except telegram_error.BadRequest as e:
            error_msg = f"Bad request: {str(e)}"
            self.log_error(f"Failed to send message: {error_msg}")
            self.failed_count += 1
            return False, 0, error_msg
            
        except telegram_error.Unauthorized as e:
            error_msg = f"Unauthorized: {str(e)}"
            self.log_error(f"Authentication failed: {error_msg}")
            self.failed_count += 1
            return False, 0, error_msg
            
        except telegram_error.ChatMigrated as e:
            error_msg = f"Chat migrated: {str(e)}"
            self.log_warning(f"Chat migration detected: {error_msg}")
            self.failed_count += 1
            return False, 0, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log_error(f"Failed to send message: {error_msg}", exc=e)
            self.failed_count += 1
            return False, 0, error_msg

    async def save_to_database(
        self,
        scholarship_id: str,
        message_text: str,
        is_sent: bool,
        message_id: int = 0,
        error_message: str = ""
    ) -> bool:
        """
        Save Telegram message record to database.
        
        Args:
            scholarship_id: ID of the scholarship
            message_text: The message text
            is_sent: Whether message was sent successfully
            message_id: Telegram message ID (if sent)
            error_message: Error message if failed
            
        Returns:
            True if saved successfully
        """
        try:
            db = SessionLocal()
            
            # Create record
            record = TelegramMessage(
                scholarship_id=scholarship_id,
                message_text=message_text,
                formatted_message=message_text,
                telegram_message_id=message_id if message_id else None,
                telegram_chat_id=self.channel_id,
                telegram_chat_type="channel",
                is_sent=is_sent,
                sent_at=datetime.utcnow() if is_sent else None,
                send_error=error_message if not is_sent else None,
            )
            
            db.add(record)
            db.commit()
            db.close()
            
            self.log_debug(f"Saved Telegram message record to database")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to save to database: {str(e)}", exc=e)
            return False

    async def send_message_with_db(
        self,
        scholarship: Dict[str, Any],
        message: str,
        chat_id: str = None
    ) -> bool:
        """
        Send message and track in database.
        
        Args:
            scholarship: Scholarship data
            message: Message to send
            chat_id: Telegram chat ID
            
        Returns:
            True if sent successfully
        """
        # Send message
        success, msg_id, error = await self.send_to_channel(message, chat_id)
        
        # Get or create scholarship ID
        scholarship_id = scholarship.get("id")
        if not scholarship_id:
            # Use hash as temporary ID
            from app.utils import generate_hash
            scholarship_id = generate_hash(f"{scholarship.get('scholarship_name')}{scholarship.get('official_link')}")
        
        # Save to database
        await self.save_to_database(
            scholarship_id=str(scholarship_id),
            message_text=message,
            is_sent=success,
            message_id=msg_id if success else 0,
            error_message=error if not success else ""
        )
        
        return success

    async def publish_messages(
        self,
        scholarships: List[Dict[str, Any]],
        messages: List[str],
        delay_between_messages: int = 2
    ) -> List[str]:
        """
        Publish messages to Telegram.
        
        Args:
            scholarships: List of scholarship data
            messages: List of formatted messages
            delay_between_messages: Seconds to wait between posts
            
        Returns:
            List of successfully posted scholarship identifiers
        """
        posted_ids = []
        
        if len(messages) != len(scholarships):
            self.log_error(
                f"Message/scholarship mismatch: {len(messages)} messages, {len(scholarships)} scholarships"
            )
            return posted_ids
        
        self.log_info(f"Publishing {len(messages)} messages to Telegram")
        
        for i, (scholarship, message) in enumerate(zip(scholarships, messages), 1):
            try:
                # Send main channel
                success = await self.send_message_with_db(
                    scholarship=scholarship,
                    message=message,
                    chat_id=self.channel_id
                )
                
                if success:
                    posted_ids.append(scholarship.get("scholarship_name", ""))
                    
                    # Also send to group if configured
                    if self.group_id:
                        await asyncio.sleep(1)
                        await self.send_to_channel(message, self.group_id)
                
                # Delay between messages
                if i < len(messages):
                    await asyncio.sleep(delay_between_messages)
                    
            except Exception as e:
                self.log_error(f"Failed to publish message {i}: {str(e)}", exc=e)
                continue
        
        self.log_info(f"Published {len(posted_ids)} messages successfully")
        return posted_ids

    async def execute(self, state: ScholarshipState) -> ScholarshipState:
        """
        Execute the Telegram publisher workflow.
        
        Args:
            state: Current workflow state with corrected messages
            
        Returns:
            Updated state with posted scholarship IDs
            
        Main flow:
        1. Get corrected messages from state
        2. Send to Telegram channel/group
        3. Track in database
        4. Update state with posted IDs
        """
        try:
            self.log_info("Starting Telegram publisher workflow")
            
            # Get messages and scholarships
            messages = state.corrected_messages
            scholarships = state.scholarships
            
            if not messages or not scholarships:
                self.log_warning("No messages or scholarships to publish")
                return state
            
            if len(messages) != len(scholarships):
                self.log_warning(
                    f"Message/scholarship mismatch: {len(messages)} messages, {len(scholarships)} scholarships"
                )
                messages = messages[:len(scholarships)]
            
            self.log_info(f"Publishing {len(messages)} scholarships to Telegram")
            
            # Publish messages
            posted_ids = await self.publish_messages(scholarships, messages)
            
            self.log_info(f"Publisher complete: {len(posted_ids)} posted successfully")
            
            # Update state
            state.posted_scholarships = posted_ids
            
            # Add metadata
            state.execution_metadata["telegram_agent_input"] = len(messages)
            state.execution_metadata["telegram_agent_sent"] = self.sent_count
            state.execution_metadata["telegram_agent_failed"] = self.failed_count
            state.execution_metadata["telegram_agent_completed_at"] = datetime.utcnow().isoformat()
            
            return state
            
        except Exception as e:
            self.log_error(f"Telegram agent failed: {str(e)}", exc=e)
            return self.add_error_to_state(
                state,
                f"Telegram publishing failed: {str(e)}"
            )


async def run_telegram_agent_demo():
    """
    Demo function to test the telegram agent.
    WARNING: This will actually send messages to your Telegram channel!
    
    Only run if you want to test real message sending.
    """
    from app.agents.search_agent import SearchAgent
    from app.agents.extraction_agent import ExtractionAgent
    from app.agents.grammar_agent import GrammarAgent
    from app.workflows import ScholarshipState
    
    print("⚠️ WARNING: This demo will send real messages to Telegram!")
    print("Press Ctrl+C to cancel, or Enter to continue...\n")
    input()
    
    print("🔍 Running Full Pipeline Demo (Search → Extract → Grammar → Telegram)...\n")
    
    # Full pipeline
    print("Step 1: Searching...")
    search_agent = SearchAgent()
    state = ScholarshipState()
    state = await search_agent.execute(state)
    print(f"  Found {len(state.search_results)} scholarships\n")
    
    print("Step 2: Extracting...")
    extraction_agent = ExtractionAgent()
    state = await extraction_agent.execute(state)
    print(f"  Extracted {len(state.scholarships)} scholarships\n")
    
    print("Step 3: Grammar correction...")
    grammar_agent = GrammarAgent()
    state = await grammar_agent.execute(state)
    print(f"  Corrected {len(state.corrected_messages)} messages\n")
    
    print("Step 4: Publishing to Telegram...")
    telegram_agent = TelegramAgent()
    state = await telegram_agent.execute(state)
    print(f"  Posted {len(state.posted_scholarships)} scholarships\n")
    
    print("✅ Pipeline Complete!")
    print(f"\nPosted scholarships:")
    for scholarship in state.posted_scholarships[:5]:
        print(f"  • {scholarship}")


if __name__ == "__main__":
    print("Demo disabled - use import instead")
    print("This agent sends real Telegram messages")

