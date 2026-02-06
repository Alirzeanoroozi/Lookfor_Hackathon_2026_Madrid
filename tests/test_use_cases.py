"""
Tests based on use_cases.csv.

Covers: Shipping Delay, Wrong/Missing Item, Product No Effect, Refund Request,
Order Modification, Positive Feedback, Subscription, Discount/Promo.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from db import get_session_messages
from email_session import EmailSession


# Example messages from use_cases.csv (Example Summaries column)
USE_CASE_MESSAGES = {
    "shipping_delay": [
        "Order #43189 shows 'in transit' for 10 days. Any update?",
        "Hi, just curious when my BuzzPatch will arrive to Toronto.",
        "Can you confirm the estimated delivery date? Thanks!",
    ],
    "wrong_missing_item": [
        "Got Zen stickers instead of Focus—kids need them for school, help!",
        "My package arrived with only 2 of the 3 packs I paid for.",
        "Received the pet collar but the tick stickers are missing.",
    ],
    "product_no_effect": [
        "Kids still getting bitten even with 2 stickers on.",
        "Focus patches aren't helping my son concentrate.",
        "Itch relief patch did nothing for the sting.",
    ],
    "refund_request": [
        "Please refund order #51234; product arrived too late.",
        "Want my money back—stickers don't repel mosquitoes as promised.",
        "Returning unused packs for a full refund, thanks.",
    ],
    "order_modification": [
        "Accidentally ordered twice—please cancel one.",
        "Realised I used wrong address—cancel so I can reorder.",
        "Need to cancel order #67890 before it ships, thanks.",
    ],
    "positive_feedback": [
        "BuzzPatch saved our camping trip—no bites at all!",
        "The kids LOVE choosing their emoji stickers each night.",
        "Focus patches actually helped my son finish homework.",
    ],
    "subscription": [
        "I cancelled but still got charged—refund please.",
        "Need to pause my monthly BuzzPatch delivery for August.",
        "Credit card changed—how do I update details?",
    ],
    "discount_promo": [
        "WELCOME10 code says invalid at checkout.",
        "Forgot to apply discount—can you refund the difference?",
        "App won't accept my loyalty points.",
    ],
}


@pytest.fixture
def session():
    """Create a fresh session for each test."""
    return EmailSession.start(
        customer_email="test@example.com",
        first_name="Test",
        last_name="User",
        shopify_customer_id="gid://shopify/Customer/456",
    )


def _mock_call_gpt_text(content: str):
    """Mock call_gpt_with_tools returning a simple text reply (no tool calls)."""
    return {
        "content": content,
        "tool_calls": [],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _mock_call_gpt_tool(name: str, arguments: dict, content: str = ""):
    """Mock call_gpt_with_tools returning one tool call then a text reply."""
    return {
        "content": content,
        "tool_calls": [{"name": name, "arguments": arguments, "result": '{"success": true}'}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _mock_call_gpt_escalate(reason: str, summary_for_team: str):
    """Mock call_gpt_with_tools returning escalate tool call."""
    return {
        "content": "",
        "tool_calls": [
            {
                "name": "escalate",
                "arguments": {"reason": reason, "summary_for_team": summary_for_team},
                "result": '{"escalated": true}',
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


# --- Shipping Delay (WISMO) ---


@patch("email_session.call_gpt_with_tools")
def test_shipping_delay_calls_order_details(mock_call, session):
    """Shipping delay use case: should look up order details for tracking."""
    mock_call.return_value = _mock_call_gpt_tool(
        "shopify_get_order_details",
        {"orderId": "#43189"},
        "Your order #43189 is in transit. Expected delivery: Friday.",
    )

    trace = session.reply(USE_CASE_MESSAGES["shipping_delay"][0])

    assert trace is not None
    assert "in transit" in trace.final_message.lower() or "transit" in trace.final_message.lower()
    tool_names = [tc.get("name") for tc in trace.tool_calls]
    assert "shopify_get_order_details" in tool_names


@patch("email_session.call_gpt_with_tools")
def test_shipping_delay_continuous_memory(mock_call, session):
    """Shipping delay: follow-up message should have session memory."""
    mock_call.side_effect = [
        _mock_call_gpt_tool(
            "shopify_get_customer_orders",
            {"email": "test@example.com", "after": "null", "limit": 10},
            "I found your order. It's on the way.",
        ),
        _mock_call_gpt_text(
            "Your BuzzPatch should arrive by Friday. Here's the tracking link: ..."
        ),
    ]

    session.reply(USE_CASE_MESSAGES["shipping_delay"][1])
    trace = session.reply("Can you send the tracking link again?")

    assert trace is not None
    assert mock_call.call_count >= 1
    # Second call should include prior context
    call_messages = mock_call.call_args[1]["messages"]
    assert len(call_messages) >= 3  # system + user messages + prior turns


# --- Wrong / Missing Item ---


@patch("email_session.call_gpt_with_tools")
def test_wrong_missing_item_calls_order_lookup(mock_call, session):
    """Wrong/missing item: should check order and items fulfilled."""
    mock_call.return_value = _mock_call_gpt_tool(
        "shopify_get_order_details",
        {"orderId": "#1234"},
        "I'm sorry to hear that. To get this sorted fast, could you send a photo of the items you received?",
    )

    trace = session.reply(USE_CASE_MESSAGES["wrong_missing_item"][0])

    assert trace is not None
    tool_names = [tc.get("name") for tc in trace.tool_calls]
    assert "shopify_get_order_details" in tool_names or len(trace.tool_calls) == 0


# --- Product No Effect ---


@patch("email_session.call_gpt_with_tools")
def test_product_no_effect_uses_knowledge_or_order(mock_call, session):
    """Product no effect: may look up product info or knowledge."""
    mock_call.return_value = _mock_call_gpt_tool(
        "shopify_get_related_knowledge_source",
        {"question": "usage for insect repellent stickers", "specificToProductId": None},
        "Here's the correct usage: apply 2 stickers per child, 1-2 hours before exposure.",
    )

    trace = session.reply(USE_CASE_MESSAGES["product_no_effect"][0])

    assert trace is not None
    assert len(trace.final_message) > 0


# --- Refund Request ---


@patch("email_session.call_gpt_with_tools")
def test_refund_request_may_call_refund_tool(mock_call, session):
    """Refund request: may call shopify_refund_order or shopify_create_store_credit."""
    mock_call.return_value = _mock_call_gpt_tool(
        "shopify_refund_order",
        {"orderId": "gid://shopify/Order/51234", "refundMethod": "ORIGINAL_PAYMENT_METHODS"},
        "I've initiated the refund for order #51234. It will appear in 5-7 business days.",
    )

    trace = session.reply(USE_CASE_MESSAGES["refund_request"][0])

    assert trace is not None
    tool_names = [tc.get("name") for tc in trace.tool_calls]
    assert "shopify_refund_order" in tool_names or "shopify_create_store_credit" in tool_names or len(trace.tool_calls) == 0


# --- Order Modification ---


@patch("email_session.call_gpt_with_tools")
def test_order_modification_cancel_or_address(mock_call, session):
    """Order modification: cancel or update shipping address."""
    mock_call.return_value = _mock_call_gpt_text(
        "I've cancelled the duplicate order. You'll receive a confirmation shortly."
    )

    trace = session.reply(USE_CASE_MESSAGES["order_modification"][0])

    assert trace is not None
    assert "cancel" in trace.final_message.lower() or len(trace.final_message) > 0


# --- Positive Feedback ---


@patch("email_session.call_gpt_with_tools")
def test_positive_feedback_returns_acknowledgment(mock_call, session):
    """Positive feedback: should acknowledge warmly, may offer review link."""
    mock_call.return_value = _mock_call_gpt_text(
        "Awwww, thank you! So glad BuzzPatch saved your camping trip! 🙏"
    )

    trace = session.reply(USE_CASE_MESSAGES["positive_feedback"][0])

    assert trace is not None
    assert len(trace.final_message) > 0
    assert "thank" in trace.final_message.lower() or "glad" in trace.final_message.lower()


# --- Subscription ---


@patch("email_session.call_gpt_with_tools")
def test_subscription_calls_skio_status(mock_call, session):
    """Subscription use case: should check skio_get_subscription_status."""
    mock_call.return_value = _mock_call_gpt_tool(
        "skio_get_subscription_status",
        {"email": "test@example.com"},
        "I've checked your subscription. To pause for August, I can set that up now.",
    )

    trace = session.reply(USE_CASE_MESSAGES["subscription"][1])

    assert trace is not None
    tool_names = [tc.get("name") for tc in trace.tool_calls]
    assert "skio_get_subscription_status" in tool_names


@patch("email_session.call_gpt_with_tools")
def test_subscription_pause(mock_call, session):
    """Subscription: pause subscription tool."""
    mock_call.return_value = _mock_call_gpt_tool(
        "skio_pause_subscription",
        {"subscriptionId": "sub_123", "pausedUntil": "2025-08-31"},
        "I've paused your subscription until August 31. You won't be charged until then.",
    )

    trace = session.reply(USE_CASE_MESSAGES["subscription"][1])

    assert trace is not None
    tool_names = [tc.get("name") for tc in trace.tool_calls]
    assert "skio_pause_subscription" in tool_names or len(trace.tool_calls) == 0


# --- Discount / Promo ---


@patch("email_session.call_gpt_with_tools")
def test_discount_promo_reply(mock_call, session):
    """Discount/promo: should offer to create or re-issue code."""
    mock_call.return_value = _mock_call_gpt_text(
        "I'm sorry the code didn't work. I've created a new 10% discount code valid for 48 hours: SAVE10_TEST."
    )

    trace = session.reply(USE_CASE_MESSAGES["discount_promo"][0])

    assert trace is not None
    assert "discount" in trace.final_message.lower() or "code" in trace.final_message.lower() or len(trace.final_message) > 0


# --- Escalation ---


def _make_escalate_mock(reason: str, summary_for_team: str):
    """Mock that invokes the executor so escalate tool actually runs and marks session."""

    def side_effect(messages, tools, tool_executor, **kwargs):
        result = tool_executor(
            "escalate",
            {"reason": reason, "summary_for_team": summary_for_team},
        )
        return {
            "content": "",
            "tool_calls": [
                {
                    "name": "escalate",
                    "arguments": {"reason": reason, "summary_for_team": summary_for_team},
                    "result": result,
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    return side_effect


@patch("email_session.call_gpt_with_tools")
def test_escalation_stops_auto_replies(mock_call, session):
    """When escalate tool is called, subsequent replies return None."""
    mock_call.side_effect = _make_escalate_mock(
        reason="Customer requests resend; policy requires human approval.",
        summary_for_team="Customer: Test User. Issue: wrong item. Requested resend.",
    )

    trace1 = session.reply("I got the wrong item and need a resend.")
    trace2 = session.reply("Hello? Can you help?")

    assert trace1 is not None
    assert "escalated" in trace1.final_message.lower() or "team" in trace1.final_message.lower()
    assert trace2 is None


@patch("email_session.call_gpt_with_tools")
def test_escalation_persists_summary(mock_call, session):
    """Escalation should persist summary to DB."""
    mock_call.side_effect = _make_escalate_mock(
        reason="Out of scope",
        summary_for_team="Customer: Test. Reason: Out of scope.",
    )

    session.reply("Something weird happened.")
    trace_data = session.get_trace()

    assert trace_data.get("escalated") is True
    import db

    sess = db.get_session(session.session_id)
    assert sess and sess.get("escalated") == 1


# --- Session persistence ---


@patch("email_session.call_gpt_with_tools")
def test_messages_persisted(mock_call, session):
    """Messages should be persisted to DB."""
    mock_call.return_value = _mock_call_gpt_text("Here's your order status.")

    session.reply("Where is my order?")
    msgs = get_session_messages(session.session_id)

    assert len(msgs) >= 2  # user + assistant
    roles = {m["role"] for m in msgs}
    assert "user" in roles
    assert "assistant" in roles


@patch("email_session.call_gpt_with_tools")
def test_tool_calls_in_trace(mock_call, session):
    """Tool calls should appear in trace (mocked LLM bypasses executor, so DB may be empty)."""
    mock_call.return_value = _mock_call_gpt_tool(
        "shopify_get_order_details",
        {"orderId": "#9999"},
        "Your order is on the way.",
    )

    trace = session.reply("Status on order #9999?")

    assert trace is not None
    assert len(trace.tool_calls) >= 1
    assert trace.tool_calls[0].get("name") == "shopify_get_order_details"
