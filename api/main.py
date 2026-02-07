from __future__ import annotations

"""
Email support session demo.

1) Start a session with customer info
2) Send messages (continuous memory)
3) Observe final message, tool calls, actions
4) Escalation stops auto-replies
"""

from dotenv import load_dotenv
load_dotenv()

from db import init_db
from email_session import EmailSession, SessionTrace

def print_trace(trace: SessionTrace | None) -> None:
    """Print observable trace to console."""
    if trace is None:
        print("[Session escalated - no automatic reply]\n")
        return
    print("--- Final message to customer ---")
    print(trace.final_message)
    print("\n--- Tool calls ---")
    for tc in trace.tool_calls:
        print(f"  {tc.get('name')}: in={tc.get('arguments')} -> out={str(tc.get('result', ''))[:200]}...")
    print("\n--- Actions taken ---")
    for a in trace.actions_taken:
        print(f"  - {a}")
    print()

def main():
    init_db()

    # 1) Session start
    session = EmailSession.start(
        customer_email="alice@example.com",
        first_name="Alice",
        last_name="Smith",
        shopify_customer_id="gid://shopify/Customer/7424155189325",
    )
    print(f"Started session {session.session_id}\n")

    # 2) First message
    print(">>> Customer: Where is my order #1001?")
    trace = session.reply("Where is my order #1001?")
    print_trace(trace)

    # 3) Follow-up (continuous memory)
    print(">>> Customer: Can you refund it instead?")
    trace = session.reply("Can you refund it instead?")
    print_trace(trace)

    # 4) Full trace for inspection
    full = session.get_trace()
    print("--- Full session trace ---")
    print(f"Session {full['session_id']}, escalated: {full['escalated']}")
    print(f"Messages: {len(full['messages'])}")
    print(f"Tool calls: {len(full['tool_calls'])}")

if __name__ == "__main__":
    main()
