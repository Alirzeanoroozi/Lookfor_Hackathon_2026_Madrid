from __future__ import annotations
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
        model="default",
        prompt="You are a helpful assistant that can answer questions and help with tasks."
    )
    print(f"Started session {session.session_id}\n")

    # 2) First message
    print(">>> Customer: Hello, my order number is  Order #NP6664669  My order was to include 2 packs for adults and i received all packs for kids. Also, the packs were the old version of buzzpatch. The packs barely had a scent as if they were dried out. Alls to say they didn’t work and i would like a refund please.  Thank you Melissa Sent from my iPhone")
    trace = session.reply("Hello, my order number is  Order #NP6664669  My order was to include 2 packs for adults and i received all packs for kids. Also, the packs were the old version of buzzpatch. The packs barely had a scent as if they were dried out. Alls to say they didn’t work and i would like a refund please.  Thank you Melissa Sent from my iPhone")
    print(trace.final_message)
    print([t.get("name") for t in trace.tool_calls])
    print_trace(trace)

    # # 3) Follow-up (continuous memory)
    # print(">>> Customer: Can you refund it instead?")
    # trace = session.reply("Can you refund it instead?")
    # print(trace.final_message)
    # print([t.get("name") for t in trace.tool_calls])
    # # print_trace(trace)
    
    # # Example 4) Escalation scenario
    # # print(">>> Customer: This is terrible, I want to escalate.")
    # # trace = session.reply("This is terrible, I want to escalate.")
    # # print(trace.final_message)
    # # print([t.get("name") for t in trace.tool_calls])
    # # # print_trace(trace)

    # # Example 5) Product issue report
    # print(">>> Customer: The patches won't stick, can I get a replacement?")
    # trace = session.reply("The patches won't stick, can I get a replacement?")
    # print_trace(trace)

    # # Example 6) Return request
    # print(">>> Customer: I'd like to return my order, what's the process?")
    # trace = session.reply("I'd like to return my order, what's the process?")
    # print_trace(trace)

    # # Example 7) Discount code inquiry
    # print(">>> Customer: Can you give me a discount code?")
    # trace = session.reply("Can you give me a discount code?")
    # print_trace(trace)

    # # Example 8) Shipping address update
    # print(">>> Customer: I moved, can I update my shipping address?")
    # trace = session.reply("I moved, can I update my shipping address?")
    # print_trace(trace)
    # # 5) Update profile
    # print(">>> Update profile: model=gpt-4o-mini, prompt=You are a helpful assistant.")
    # session.update_profile("gpt-4o-mini", "You are a helpful assistant.")
    # print(f"Updated profile for session {session.session_id}\n")

    # 4) Full trace for inspection
    full = session.get_trace()
    print("--- Full session trace ---")
    print(f"Session {full['session_id']}, escalated: {full['escalated']}")
    print(f"Messages: {len(full['messages'])}")
    print(f"Tool calls: {len(full['tool_calls'])}")

if __name__ == "__main__":
    main()
