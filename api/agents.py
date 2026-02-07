from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

from call_gpt import call_gpt_with_tools
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
class LLMAgent:
    """
    LLM-powered agent that can call tools. Uses call_gpt_with_tools.
    """

    name: str
    system_prompt: str
    tool_definitions: List[Dict[str, Any]]
    tool_executor: Callable[[str, Dict[str, Any]], str]
    tool_call_collector: Optional[List[Dict[str, Any]]] = None

    def act(self, messages: List[Message]) -> Optional[Message]:
        openai_messages: List[Dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            sender = m.get("sender", role)
            if role == "system":
                continue  # use our own system prompt
            if role == "user":
                openai_messages.append({"role": "user", "content": content})
            elif role == "agent":
                openai_messages.append({"role": "user", "content": f"[{sender}]: {content}"})

        result = call_gpt_with_tools(
            messages=openai_messages,
            tools=self.tool_definitions,
            tool_executor=self.tool_executor,
            temperature=0.3,
            max_tokens=1024,
            max_tool_rounds=5,
        )

        content = result.get("content", "")
        tool_calls = result.get("tool_calls", [])

        if self.tool_call_collector is not None:
            for tc in tool_calls:
                tc_copy = dict(tc)
                tc_copy["agent"] = self.name
                self.tool_call_collector.append(tc_copy)

        if not content and not tool_calls:
            return None

        return Message(
            role="agent",
            content=content or "(no text output)",
            sender=self.name,
            tool_calls=tool_calls,
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
