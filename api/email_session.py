from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
load_dotenv()

import db
from agents import LLMAgent, Message, MultiAgentSystem
from tools import (
    ShopifyGetCustomerOrdersTool,
    ShopifyGetOrderDetailsTool,
    ShopifyGetRelatedKnowledgeSourceTool,
    ShopifyRefundOrderTool,
    ShopifyCreateStoreCreditTool,
    SkioGetSubscriptionStatusTool,
    SkioPauseSubscriptionTool,
    SkioCancelSubscriptionTool,
)

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "shopify_get_order_details",
        "description": "Fetch detailed information for a single order by ID. Use order number like #1234.",
        "parameters": {
            "type": "object",
            "required": ["orderId"],
            "properties": {"orderId": {"type": "string", "description": "Order identifier, e.g. #1234"}},
        },
    },
    {
        "name": "shopify_get_customer_orders",
        "description": "Get customer orders by email. Use 'null' for after on first page.",
        "parameters": {
            "type": "object",
            "required": ["email", "after", "limit"],
            "properties": {
                "email": {"type": "string"},
                "after": {"type": "string", "description": "Cursor, use 'null' for first page"},
                "limit": {"type": "integer", "description": "Max 250"},
            },
        },
    },
    {
        "name": "shopify_refund_order",
        "description": "Refund an order. orderId is the full GID.",
        "parameters": {
            "type": "object",
            "required": ["orderId", "refundMethod"],
            "properties": {
                "orderId": {"type": "string"},
                "refundMethod": {
                    "type": "string",
                    "enum": ["ORIGINAL_PAYMENT_METHODS", "STORE_CREDIT"],
                },
            },
        },
    },
    {
        "name": "shopify_create_store_credit",
        "description": "Credit store credit to a customer.",
        "parameters": {
            "type": "object",
            "required": ["id", "creditAmount", "expiresAt"],
            "properties": {
                "id": {"type": "string", "description": "Customer GID"},
                "creditAmount": {
                    "type": "object",
                    "required": ["amount", "currencyCode"],
                    "properties": {
                        "amount": {"type": "string"},
                        "currencyCode": {"type": "string"},
                    },
                },
                "expiresAt": {"type": ["string", "null"]},
            },
        },
    },
    {
        "name": "skio_get_subscription_status",
        "description": "Get subscription status for a customer by email.",
        "parameters": {
            "type": "object",
            "required": ["email"],
            "properties": {"email": {"type": "string"}},
        },
    },
    {
        "name": "skio_pause_subscription",
        "description": "Pause a Skio subscription until a date.",
        "parameters": {
            "type": "object",
            "required": ["subscriptionId", "pausedUntil"],
            "properties": {
                "subscriptionId": {"type": "string"},
                "pausedUntil": {"type": "string", "description": "Format YYYY-MM-DD"},
            },
        },
    },
    {
        "name": "skio_cancel_subscription",
        "description": "Cancel a Skio subscription.",
        "parameters": {
            "type": "object",
            "required": ["subscriptionId", "cancellationReasons"],
            "properties": {
                "subscriptionId": {"type": "string"},
                "cancellationReasons": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "shopify_get_related_knowledge_source",
        "description": "Retrieve FAQs, PDFs, blog articles about a question. Use null for productId if not product-specific.",
        "parameters": {
            "type": "object",
            "required": ["question", "specificToProductId"],
            "properties": {
                "question": {"type": "string"},
                "specificToProductId": {"type": ["string", "null"]},
            },
        },
    },
    {
        "name": "escalate",
        "description": "Escalate to a human when you cannot safely proceed, when policy requires it, or when the customer request is outside your scope. Call this instead of replying.",
        "parameters": {
            "type": "object",
            "required": ["reason", "summary_for_team"],
            "properties": {
                "reason": {"type": "string", "description": "Why escalation is needed"},
                "summary_for_team": {
                    "type": "string",
                    "description": "Short structured summary: customer, issue, what was tried, suggested next steps",
                },
            },
        },
    },
]

# Tool subsets per agent
ROUTER_TOOLS = [
    t for t in TOOL_DEFINITIONS
    if t["name"] in ("shopify_get_order_details", "shopify_get_customer_orders", "skio_get_subscription_status")
]
POLICY_TOOLS = [
    t for t in TOOL_DEFINITIONS
    if t["name"] in ("shopify_get_related_knowledge_source", "escalate")
]
EXECUTOR_TOOLS = [
    t for t in TOOL_DEFINITIONS
    if t["name"] in (
        "shopify_get_order_details",
        "shopify_get_customer_orders",
        "shopify_refund_order",
        "shopify_create_store_credit",
        "skio_get_subscription_status",
        "skio_pause_subscription",
        "skio_cancel_subscription",
        "shopify_get_related_knowledge_source",
        "escalate",
    )
]

@dataclass
class SessionTrace:
    """Observable trace: final message, tool calls, actions."""

    final_message: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)

@dataclass
class EmailSession:
    """
    Email support session with continuous memory, tool calling, and escalation.

    Usage:
        session = EmailSession.start(customer_email="...", first_name="...", last_name="...", shopify_customer_id="...")
        result = session.reply("Where is my order?")  # first message
        result = session.reply("It's order #1234")   # follow-up (memory preserved)
    """

    session_id: int
    customer_email: str
    first_name: str
    last_name: str
    shopify_customer_id: str
    _tools: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def start(
        cls,
        customer_email: str,
        first_name: str,
        last_name: str,
        shopify_customer_id: str,
    ) -> "EmailSession":
        """Start a new email session. Persists to DB."""
        db.init_db()
        session_id = db.create_session(
            customer_email=customer_email,
            first_name=first_name,
            last_name=last_name,
            shopify_customer_id=shopify_customer_id,
        )
        return cls(
            session_id=session_id,
            customer_email=customer_email,
            first_name=first_name,
            last_name=last_name,
            shopify_customer_id=shopify_customer_id,
        )

    @classmethod
    def load(cls, session_id: int) -> Optional["EmailSession"]:
        """Load an existing session from DB."""
        row = db.get_session(session_id)
        if not row:
            return None
        return cls(
            session_id=row["id"],
            customer_email=row["customer_email"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            shopify_customer_id=row["shopify_customer_id"],
        )

    def _build_tools(self) -> Dict[str, Any]:
        if self._tools:
            return self._tools
        self._tools = {
            "shopify_get_order_details": ShopifyGetOrderDetailsTool(),
            "shopify_get_customer_orders": ShopifyGetCustomerOrdersTool(),
            "shopify_refund_order": ShopifyRefundOrderTool(),
            "shopify_create_store_credit": ShopifyCreateStoreCreditTool(),
            "skio_get_subscription_status": SkioGetSubscriptionStatusTool(),
            "skio_pause_subscription": SkioPauseSubscriptionTool(),
            "skio_cancel_subscription": SkioCancelSubscriptionTool(),
            "shopify_get_related_knowledge_source": ShopifyGetRelatedKnowledgeSourceTool(),
        }
        return self._tools

    def _tool_executor(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool by name. Handles 'escalate' specially."""
        if tool_name == "escalate":
            reason = arguments.get("reason", "Not specified")
            summary = arguments.get("summary_for_team", "")
            db.mark_session_escalated(self.session_id)
            db.add_escalation(
                self.session_id,
                summary_json={
                    "reason": reason,
                    "summary_for_team": summary,
                    "customer_email": self.customer_email,
                    "customer_name": f"{self.first_name} {self.last_name}",
                },
                reason=reason,
            )
            return json.dumps({
                "success": True,
                "escalated": True,
                "message": "Session escalated. No further automatic replies.",
            })

        tools = self._build_tools()
        tool = tools.get(tool_name)
        if not tool:
            return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})

        kwargs = dict(arguments)
        if tool_name == "shopify_get_customer_orders":
            if kwargs.get("after") is None or kwargs.get("after") == "null":
                kwargs["after"] = "null"
        try:
            result = tool.run(**kwargs)
        except Exception as e:
            result = {"success": False, "error": str(e)}
        return json.dumps(result) if isinstance(result, dict) else str(result)

    def _messages_for_llm(self, new_user_message: str) -> List[Dict[str, Any]]:
        """Build messages with system context and full history."""
        rows = db.get_session_messages(self.session_id)

        sys = (
            f"You are an email support agent for a brand. "
            f"Customer: {self.first_name} {self.last_name} <{self.customer_email}>, "
            f"Shopify customer ID: {self.shopify_customer_id}. "
            f"Use tools to look up orders, subscriptions, refunds, etc. "
            f"If you cannot safely proceed or policy requires human review, call the escalate tool. "
            f"Be helpful, concise, and professional. Match the customer's tone."
        )
        messages: List[Dict[str, Any]] = [{"role": "system", "content": sys}]

        for r in rows:
            role = r["role"]
            content = r["content"] or ""
            if role == "user":
                messages.append({"role": "user", "content": content})
            elif role == "assistant":
                messages.append({"role": "assistant", "content": content})

        messages.append({"role": "user", "content": new_user_message})
        return messages

    def reply(self, customer_message: str) -> Optional[SessionTrace]:
        """
        Process a new customer message and generate a reply via multi-agent pipeline:
        Router -> Policy -> Executor. Each agent can call tools.
        """
        if db.is_session_escalated(self.session_id):
            return None

        db.add_message(self.session_id, "user", customer_message, sender="customer")

        tool_call_collector: List[Dict[str, Any]] = []

        def executor(name: str, args: Dict[str, Any]) -> str:
            out = self._tool_executor(name, args)
            try:
                parsed = json.loads(out) if isinstance(out, str) else out
            except json.JSONDecodeError:
                parsed = {"raw": str(out)}
            db.add_tool_call(self.session_id, name, args, parsed)
            return out

        sys_context = (
            f"Customer: {self.first_name} {self.last_name} <{self.customer_email}>, "
            f"Shopify customer ID: {self.shopify_customer_id}."
        )

        router = LLMAgent(
            name="RouterAgent",
            system_prompt=(
                f"You are the Router agent for email support. {sys_context} "
                "Your job: classify the request and gather context. Use tools to look up orders or subscriptions. "
                "Output a short classification: e.g. SHIPPING_DELAY, REFUND_REQUEST, SUBSCRIPTION, WRONG_ITEM, PRODUCT_ISSUE, etc. "
                "Summarize what you found and what workflow applies. Pass this to Policy."
            ),
            tool_definitions=ROUTER_TOOLS,
            tool_executor=executor,
            tool_call_collector=tool_call_collector,
        )

        policy = LLMAgent(
            name="PolicyAgent",
            system_prompt=(
                f"You are the Policy agent. {sys_context} "
                "You receive Router's classification. Check workflow rules using shopify_get_related_knowledge_source. "
                "If we cannot safely proceed or policy requires human review, call the escalate tool. "
                "Otherwise output: PROCEED with a brief note for the Executor."
            ),
            tool_definitions=POLICY_TOOLS,
            tool_executor=executor,
            tool_call_collector=tool_call_collector,
        )

        executor_agent = LLMAgent(
            name="ExecutorAgent",
            system_prompt=(
                f"You are the Executor agent. {sys_context} "
                "You receive Router's analysis and Policy's decision. Execute the appropriate actions using tools: "
                "refunds, store credit, subscription pause/cancel, order lookup, etc. "
                "Produce the final customer-facing reply: helpful, concise, professional. "
                "If Policy escalated, do not execute—acknowledge escalation only."
            ),
            tool_definitions=EXECUTOR_TOOLS,
            tool_executor=executor,
            tool_call_collector=tool_call_collector,
        )

        mas = MultiAgentSystem(agents=[router, policy, executor_agent])

        rows = db.get_session_messages(self.session_id)
        initial: List[Dict[str, Any]] = []
        for r in rows[:-1]:  # exclude the last user message we just added
            role = r["role"]
            content = r["content"] or ""
            if role == "user":
                initial.append(Message(role="user", content=content, sender="customer"))
            elif role == "assistant":
                initial.append(Message(role="agent", content=content, sender="agent"))

        history = mas.run(
            user_message=customer_message,
            max_turns=1,
            initial_messages=initial,
        )

        tool_calls = tool_call_collector

        if db.is_session_escalated(self.session_id):
            customer_facing = (
                "Thank you for reaching out. We've escalated your request to our team. "
                "A team member will follow up with you shortly."
            )
            db.add_message(self.session_id, "assistant", customer_facing, sender="agent")
            actions = ["escalated_to_human"]
            for tc in tool_calls:
                if tc.get("name") == "escalate":
                    actions.append(f"escalate: {tc.get('arguments', {}).get('reason', '')}")
            return SessionTrace(
                final_message=customer_facing,
                tool_calls=tool_calls,
                actions_taken=actions,
            )

        content = ""
        for m in reversed(history):
            if m.get("sender") == "ExecutorAgent" and m.get("content"):
                content = m.get("content", "")
                if content != "(no text output)":
                    break
        if not content:
            content = history[-1].get("content", "") if history else "I apologize, I couldn't process that. Please try again."

        db.add_message(self.session_id, "assistant", content, sender="agent")

        actions = []
        for tc in tool_calls:
            name = tc.get("name", "")
            if name and name != "escalate":
                actions.append(f"{tc.get('agent', '')}/{name}({json.dumps(tc.get('arguments', {}))})")

        return SessionTrace(
            final_message=content,
            tool_calls=tool_calls,
            actions_taken=actions,
        )

    def get_trace(self) -> Dict[str, Any]:
        """Return observable trace for the session: messages, tool calls, escalation."""
        db.init_db()
        sess = db.get_session(self.session_id)
        if not sess:
            return {}
        messages = db.get_session_messages(self.session_id)
        tool_calls = db.get_session_tool_calls(self.session_id)
        return {
            "session_id": self.session_id,
            "customer_email": self.customer_email,
            "escalated": bool(sess.get("escalated")),
            "messages": [{"role": m["role"], "content": m["content"], "sender": m.get("sender")} for m in messages],
            "tool_calls": tool_calls,
        }
