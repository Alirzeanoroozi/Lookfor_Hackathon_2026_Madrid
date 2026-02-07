
# Install and run
   ```bash
   cd api
   pip install -r requirements.txt
   python3 -m uvicorn api:app --reload
   ```

---

# High-Level Architecture
<img src="image.png" alt="High-Level Architecture Diagram" width="700"/>


### Agents

The system uses a **multi-agent pipeline** (Router → Policy → Executor):

- **RouterAgent**: Classifies the request and gathers context. Calls `get_order_details`, `get_customer_orders`, `get_subscription_status`. Outputs workflow type (e.g. SHIPPING_DELAY, REFUND_REQUEST).

- **PolicyAgent**: Checks workflow rules via `get_related_knowledge_source`. Can call `escalate` when policy requires human review. Outputs PROCEED or escalation.

- **ExecutorAgent**: Executes actions (refunds, store credit, subscription pause/cancel, order lookup) and produces the final customer-facing reply.

### Routing

**RouterAgent** explicitly classifies and routes:

- Gathers order/subscription context via tools
- Passes classification to Policy and Executor

### Retrieval

- **Knowledge retrieval**: `get_related_knowledge_source` returns FAQs, PDFs, blog articles, and Shopify pages given a question and optional product ID.
- **Order / product data**: `get_order_details`, `get_customer_orders`, `get_product_details`, `get_product_recommendations`, `get_collection_recommendations` provide structured data from the hackathon API.

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
