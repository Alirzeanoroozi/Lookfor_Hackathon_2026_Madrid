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

This hackathon is about building step one properly: taking messy real-world inputs (tickets plus workflow manual) and producing a multi-agent system that can reliably automate a brand's email workflows, with correct tool usage, correct boundaries, continuous memory, and safe escalation.

---

## How to Run

### Docker (recommended)

Docker makes evaluation easy and reproducible.

1. **Build the image:**
   ```bash
   docker build -t lookfor .
   ```

2. **Run the API server:**
   ```bash
   docker run -p 8000:8000 \
     -e OPENAI_API_KEY=your_openai_key \
     -e API_URL=https://your-hackathon-api.com \
     lookfor
   ```

3. **Verify:**
   - Health: `curl http://localhost:8000/health`
   - Docs: http://localhost:8000/docs

### Local (without Docker)

1. **Create `.env`** in the project root:
   ```
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   API_URL=https://your-hackathon-api.com
   ```

2. **Install and run:**
   ```bash
   pip install -r requirements.txt
   uvicorn api:app --reload --host 0.0.0.0 --port 8000
   ```

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI (api.py)                             │
│  POST /sessions  │  POST /sessions/:id/reply  │  GET /sessions/:id   │
└─────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EmailSession (email_session.py)                   │
│  - Session start (customer email, name, shopify_customer_id)         │
│  - Continuous memory via DB                                          │
│  - Orchestrates LLM + tools + escalation                             │
└─────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  call_gpt    │    │  tools.py        │    │  db.py (SQLite)   │
│  (OpenAI)    │    │  Shopify, Skio   │    │  sessions, msgs,  │
│  + tools     │    │  knowledge       │    │  tool_calls,      │
└──────────────┘    └──────────────────┘    │  escalations      │
                                            └──────────────────┘
```

### Agents

The system uses a **single LLM agent** (GPT via `call_gpt.py`) that:

- Receives full conversation history and customer context (email, name, Shopify ID)
- Decides which tools to call and when to escalate
- Produces the final reply to the customer

The `agents.py` module defines a `MultiAgentSystem` and `SimpleAgent` protocol for optional multi-agent collaboration (round-robin, specialized agents); the production email flow currently uses the single LLM + tools pattern.

### Routing

Routing is **implicit**: the LLM chooses actions based on the customer message:

- Order lookup → `shopify_get_order_details` or `shopify_get_customer_orders`
- Refund / store credit → `shopify_refund_order`, `shopify_create_store_credit`
- Subscription status or changes → `skio_*` tools
- Policy / FAQ questions → `shopify_get_related_knowledge_source`
- Unsafe or out-of-scope → `escalate`

### Retrieval

- **Knowledge retrieval**: `shopify_get_related_knowledge_source` returns FAQs, PDFs, blog articles, and Shopify pages given a question and optional product ID.
- **Order / product data**: `shopify_get_order_details`, `shopify_get_customer_orders`, `shopify_get_product_details`, `shopify_get_product_recommendations`, `shopify_get_collection_recommendations` provide structured data from the hackathon API.

### Tool Calls

- Tools are defined in `tools.py` and follow the hackathon API contract (`success`, `data`, `error`).
- `call_gpt_with_tools` in `call_gpt.py` uses OpenAI function calling: the model requests tool calls, we execute them via `tool_executor`, and feed results back until the model returns a final text reply.
- Every tool call is persisted in `tool_calls` for observability.

---

## Escalation

### When It Happens

The LLM can call the `escalate` tool when:

- It cannot safely proceed (e.g., ambiguous request, policy edge case)
- The workflow manual requires human review
- The request is outside automation scope

### How It’s Implemented

1. **Tool invocation**  
   The model chooses the `escalate` tool with `reason` and `summary_for_team`.

2. **Processing** (`email_session._tool_executor`):
   - Marks the session as escalated in `email_sessions`
   - Inserts a row in `escalations` with structured summary: customer info, reason, suggested next steps

3. **Customer message**  
   A standard escalation message is returned, e.g.:
   > "Thank you for reaching out. We've escalated your request to our team. A team member will follow up with you shortly."

4. **No further auto-replies**  
   On later `reply` calls, if `db.is_session_escalated(session_id)` is true, the function returns `None` and no LLM reply is generated.

### Traceability

- `GET /sessions/{id}/trace` returns messages, tool calls, and escalation status
- The `escalations` table stores summaries for team handoff
