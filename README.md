# Lookfor

We study their past customer interactions (e.g., tickets in their old customer relations platform), understand their operations, configure the necessary API tools based on their workflow (e.g., subscription management, inventory systems), and eventually design or update their MAS, test it, and deploy it.

- We built a system that automates customer workflows (step one), and we more or less achieved that.
- The next step is to build a system that automates the creation of systems that automate customer workflows.
- But one needs to be proficient at step one before moving to step two.

- They send us their previous tickets
- They send a document explaining the workflows they want to automate, including policies, boundaries, and implementation steps (we call this the **workflow manual**)
- They tell us which external tools they use and need in those workflows

## Tooling Spec
https://lookfor-ai.notion.site/Hackathon-Tooling-Spec-2ff8ec5e9e5d80f1b15ce7aba0c384d7


This hackathon is about building step one properly: taking messy real-world inputs (tickets plus workflow manual) and producing a multi-agent system that can reliably automate a brand’s email workflows, with correct tool usage, correct boundaries, continuous memory, and safe escalation.
