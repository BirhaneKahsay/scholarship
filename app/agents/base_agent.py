"""
Base agent class for all agents.
Provides common functionality and interface for all agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.workflows import ScholarshipState


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Defines the interface and common functionality for agents.
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize the base agent.
        
        Args:
            name: Agent name
            description: Agent description
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"agents.{self.name}")
        self.logger.info(f"Initialized {self.name}: {self.description}")

    @abstractmethod
    async def execute(self, state: ScholarshipState) -> ScholarshipState:
        """
        Execute the agent's main logic.
        Must be implemented by subclasses.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        pass

    def log_info(self, message: str):
        """Log info message."""
        self.logger.info(f"[{self.name}] {message}")

    def log_error(self, message: str, exc: Exception = None):
        """Log error message."""
        if exc:
            self.logger.error(f"[{self.name}] {message}", exc_info=exc)
        else:
            self.logger.error(f"[{self.name}] {message}")

    def log_warning(self, message: str):
        """Log warning message."""
        self.logger.warning(f"[{self.name}] {message}")

    def log_debug(self, message: str):
        """Log debug message."""
        self.logger.debug(f"[{self.name}] {message}")

    def add_error_to_state(self, state: ScholarshipState, error: str) -> ScholarshipState:
        """
        Add an error message to the state.
        
        Args:
            state: Current state
            error: Error message to add
            
        Returns:
            Updated state
        """
        state.errors.append(f"{self.name}: {error}")
        self.log_error(error)
        return state

    def add_metadata(
        self, state: ScholarshipState, key: str, value: Any
    ) -> ScholarshipState:
        """
        Add metadata to the execution state.
        
        Args:
            state: Current state
            key: Metadata key
            value: Metadata value
            
        Returns:
            Updated state
        """
        state.execution_metadata[f"{self.name}_{key}"] = value
        return state

    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.name})>"

