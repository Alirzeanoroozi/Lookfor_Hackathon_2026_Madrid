import json

def create_examples_prompts():
    with open("anonymized_tickets.json", "r") as f, open("examples_prompts.txt", "w") as f_prompts:
        tickets = json.load(f)
        for ticket in tickets:
            conversation = ticket["conversation"]
            subject = ticket["subject"]
            f_prompts.write(f"Subject: {subject}\n")
            f_prompts.write(f"Conversation: {conversation}\n")
            f_prompts.write("\n")

create_examples_prompts()