from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from tools import Tool


class Message(dict):
    """
    Simple message type: {"role": "user|agent|system", "content": str, "sender": str}
    You can extend this later with more fields (e.g. tools used, metadata, etc.).
    """


class Agent(Protocol):
    """
    Interface for all agents in the system.
    Each agent receives the shared conversation state and returns either:
      - a new message to add
      - or None, if it decides to stay silent for this turn
    """

    name: str

    def act(self, messages: List[Message]) -> Optional[Message]:  # pragma: no cover - interface
        ...


@dataclass
class SimpleAgent:
    """
    Minimal example agent implementation you can customize.

    Each agent can be configured with a set of tools.
    Tools are thin wrappers around external systems (email, ticketing, policy lookup, memory, etc.)
    defined in `tools.py`.
    """

    name: str
    description: str
    tools: List[Tool] = field(default_factory=list)

    def act(self, messages: List[Message]) -> Optional[Message]:
        # Very dumb example: just acknowledges the last user/agent message.
        if not messages:
            return None

        last = messages[-1]
        content = last.get("content", "")

        # You can add logic here (pattern matching, tool calls, LLM calls, etc.)
        reply = f"{self.name} saw: {content}"

        return Message(
            role="agent",
            content=reply,
            sender=self.name,
        )


@dataclass
class MultiAgentSystem:
    """
    Holds a collection of agents and coordinates a simple collaboration loop.

    Basic usage:

        mas = MultiAgentSystem(agents=[agent1, agent2])
        history = mas.run(user_message="Help with order #123", max_turns=5)
    """

    agents: List[Agent] = field(default_factory=list)
    system_prompt: str = "You are a team of agents collaborating to assist the user."

    def add_agent(self, agent: Agent) -> None:
        self.agents.append(agent)

    def run(
        self,
        user_message: str,
        max_turns: int = 5,
        initial_messages: Optional[List[Message]] = None,
    ) -> List[Message]:
        """
        Run a simple round‑robin collaboration loop.
        - Start from system + user messages
        - Each turn, every agent gets the full history and may add a message
        - Stops when max_turns is reached or no agent responds in a round
        """
        messages: List[Message] = []

        # Seed conversation
        messages.append(
            Message(
                role="system",
                content=self.system_prompt,
                sender="system",
            )
        )

        if initial_messages:
            messages.extend(initial_messages)

        messages.append(
            Message(
                role="user",
                content=user_message,
                sender="user",
            )
        )

        for _ in range(max_turns):
            any_response = False

            for agent in self.agents:
                response = agent.act(messages)
                if response is not None:
                    messages.append(response)
                    any_response = True

            if not any_response:
                break

        return messages

