from agents import MultiAgentSystem, SimpleAgent


def main():
    # Define some example agents. You will replace/customize these for:
    # - email triage
    # - policy checking
    # - tool-calling / API integration
    # - escalation, etc.
    router = SimpleAgent(
        name="RouterAgent",
        description="Routes user requests to the right workflow.",
    )
    policy = SimpleAgent(
        name="PolicyAgent",
        description="Checks brand policies and constraints.",
    )
    executor = SimpleAgent(
        name="ExecutorAgent",
        description="Executes the final workflow steps.",
    )

    mas = MultiAgentSystem(agents=[router, policy, executor])

    conversation = mas.run("Handle this sample customer email about a late delivery.", max_turns=3)

    for msg in conversation:
        print(f"[{msg['role']}] {msg['sender']}: {msg['content']}")


if __name__ == "__main__":
    main()

