from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol
import json
import os
from urllib import error, request


def _post_json(path: str, payload: Dict[str, Any], api_url: str | None = None) -> Dict[str, Any]:
    """
    Helper to call the hackathon API and normalize responses to the standard contract:
      - success: true | false
      - data: {...} (optional, on success)
      - error: string (on failure)
    """
    base = api_url or os.environ.get("API_URL")
    if not base:
        return {
            "success": False,
            "error": "API_URL is not configured. Set env var API_URL or pass api_url.",
        }

    url = base.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req) as resp:
            body = resp.read().decode("utf-8") or "{}"
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Invalid JSON response from API.",
                    "body": body,
                }

            # API is expected to already follow the {success, data?, error?} contract.
            if isinstance(parsed, dict) and "success" in parsed:
                return parsed

            return {
                "success": False,
                "error": "Unexpected response format from API.",
                "body": parsed,
            }
    except error.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return {
            "success": False,
            "error": f"HTTP error when calling API: {e}",
            "body": body,
        }
    except error.URLError as e:
        return {
            "success": False,
            "error": f"Network error when calling API: {e}",
        }


class Tool(Protocol):
    """
    Generic interface for tools that agents can call.

    Tools are thin, testable wrappers around external systems (APIs, DBs, etc.).
    Every concrete tool should:
      - expose a `name` and `description`
      - implement `run` with a well‑defined input / output contract
    """

    name: str
    description: str

    def run(self, **kwargs: Any) -> Dict[str, Any]:  # pragma: no cover - interface
        ...


@dataclass
class EmailTool:
    """
    Example email tool.

    In a real implementation you would:
      - configure an SMTP client or provider SDK (e.g. SendGrid)
      - plug in brand‑specific "from" addresses, templates, etc.
    For now, it just simulates sending and returns a structured result.
    """

    name: str = "email_tool"
    description: str = "Send customer‑facing emails on behalf of the brand."

    def run(
        self,
        to: str,
        subject: str,
        body: str,
        from_address: str | None = None,
    ) -> Dict[str, Any]:
        # TODO: replace with real email integration.
        # For hackathon purposes, we just echo what would have been sent.
        return {
            "status": "SIMULATED",
            "to": to,
            "from": from_address or "no-reply@example.com",
            "subject": subject,
            "body": body,
        }


@dataclass
class TicketingTool:
    """
    Example ticketing / CRM tool.

    Intended to wrap an external ticketing system:
      - create / update tickets
      - add internal notes
      - change status, assignee, etc.
    """

    name: str = "ticketing_tool"
    description: str = "Create and update tickets in the brand's ticketing system."

    def run(
        self,
        action: str,
        ticket_id: str | None = None,
        payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        payload = payload or {}

        # In a real implementation, route to concrete API calls.
        if action == "create":
            # Simulate ticket creation
            return {
                "status": "SIMULATED",
                "action": "create",
                "ticket_id": "TICKET-123",
                "payload": payload,
            }
        elif action == "update" and ticket_id:
            return {
                "status": "SIMULATED",
                "action": "update",
                "ticket_id": ticket_id,
                "payload": payload,
            }
        else:
            return {
                "status": "ERROR",
                "message": f"Unsupported action '{action}' or missing ticket_id.",
            }


@dataclass
class PolicyTool:
    """
    Example tool for querying workflow manuals / policy docs.

    For the hackathon, this could be wired to:
      - a local vector store
      - a simple keyword search over PDFs / text
    """

    name: str = "policy_tool"
    description: str = "Look up brand policies, constraints, and workflow rules."

    def run(self, query: str) -> Dict[str, Any]:
        # TODO: replace with real retrieval over the workflow manual.
        # We return a placeholder answer so agents have a clear contract.
        return {
            "status": "SIMULATED",
            "query": query,
            "answer": "Policy lookup is not yet implemented. This is a stub response.",
        }


@dataclass
class MemoryTool:
    """
    Example tool for long‑term memory about tickets / customers.

    You can back this by your SQLite DB (`db.py`) or any other store.
    For now it's a stub with a simple interface.
    """

    name: str = "memory_tool"
    description: str = "Store and retrieve long‑term memory about customers and tickets."

    def run(
        self,
        action: str,
        key: str,
        value: Any | None = None,
    ) -> Dict[str, Any]:
        if action == "put":
            # TODO: persist `key`/`value` into a real DB.
            return {
                "status": "SIMULATED",
                "action": "put",
                "key": key,
                "value": value,
            }
        elif action == "get":
            return {
                "status": "SIMULATED",
                "action": "get",
                "key": key,
                "value": None,
                "message": "Memory lookup not yet implemented.",
            }
        else:
            return {
                "status": "ERROR",
                "message": f"Unsupported action '{action}'.",
            }


@dataclass
class ShopifyAddTagsTool:
    """
    Tool: `shopify_add_tags`

    Add tags to a Shopify resource (order, draft order, customer, product, etc.)
    using the hackathon API:

        POST {API_URL}/hackhaton/add_tags
        Headers: Content-Type: application/json

    Params:
        - id: Shopify resource GID (string)
        - tags: list of strings

    `api_url` can be passed explicitly or taken from the `API_URL` env var.
    """

    name: str = "shopify_add_tags"
    description: str = "Add tags to a Shopify resource via the hackathon API."
    api_url: str | None = None

    def run(self, id: str, tags: list[str]) -> Dict[str, Any]:
        if not tags:
            return {
                "success": False,
                "error": "At least one tag is required.",
            }

        payload = {"id": id, "tags": tags}
        return _post_json("/hackhaton/add_tags", payload, api_url=self.api_url)


@dataclass
class ShopifyCancelOrderTool:
    """
    Tool: `shopify_cancel_order`

    Cancel an order based on order ID and reason.
    """

    name: str = "shopify_cancel_order"
    description: str = "Cancel an order via the hackathon API."
    api_url: str | None = None

    def run(
        self,
        orderId: str,
        reason: str,
        notifyCustomer: bool,
        restock: bool,
        staffNote: str,
        refundMode: str,
        storeCredit: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "orderId": orderId,
            "reason": reason,
            "notifyCustomer": notifyCustomer,
            "restock": restock,
            "staffNote": staffNote,
            "refundMode": refundMode,
        }
        if storeCredit is not None:
            payload["storeCredit"] = storeCredit

        return _post_json("/hackhaton/cancel_order", payload, api_url=self.api_url)


@dataclass
class ShopifyCreateDiscountCodeTool:
    """
    Tool: `shopify_create_discount_code`

    Create a discount code for the customer.
    """

    name: str = "shopify_create_discount_code"
    description: str = "Create a discount code via the hackathon API."
    api_url: str | None = None

    def run(
        self,
        discount_type: str,
        value: float,
        duration: int,
        productIds: list[str],
    ) -> Dict[str, Any]:
        payload = {
            "type": discount_type,
            "value": value,
            "duration": duration,
            "productIds": productIds,
        }
        return _post_json("/hackhaton/create_discount_code", payload, api_url=self.api_url)


@dataclass
class ShopifyCreateDraftOrderTool:
    """
    Tool: `shopify_create_draft_order`

    Create a draft order. The exact params schema is defined in the external spec;
    this wrapper forwards any provided keyword args directly as JSON.
    """

    name: str = "shopify_create_draft_order"
    description: str = "Create a draft order via the hackathon API."
    api_url: str | None = None

    def run(self, **payload: Any) -> Dict[str, Any]:
        return _post_json("/hackhaton/create_draft_order", payload, api_url=self.api_url)


@dataclass
class ShopifyCreateReturnTool:
    """
    Tool: `shopify_create_return`

    Create a Return for a given order.
    """

    name: str = "shopify_create_return"
    description: str = "Create a return via the hackathon API."
    api_url: str | None = None

    def run(self, orderId: str) -> Dict[str, Any]:
        payload = {"orderId": orderId}
        return _post_json("/hackhaton/create_return", payload, api_url=self.api_url)


@dataclass
class ShopifyCreateStoreCreditTool:
    """
    Tool: `shopify_create_store_credit`

    Credit store credit to a customer or StoreCreditAccount.
    """

    name: str = "shopify_create_store_credit"
    description: str = "Create store credit via the hackathon API."
    api_url: str | None = None

    def run(
        self,
        id: str,
        creditAmount: Dict[str, Any],
        expiresAt: str | None,
    ) -> Dict[str, Any]:
        payload = {
            "id": id,
            "creditAmount": creditAmount,
            "expiresAt": expiresAt,
        }
        return _post_json("/hackhaton/create_store_credit", payload, api_url=self.api_url)


@dataclass
class ShopifyGetCollectionRecommendationsTool:
    """
    Tool: `shopify_get_collection_recommendations`

    Generate collection recommendations based on text queries.
    """

    name: str = "shopify_get_collection_recommendations"
    description: str = "Get collection recommendations via the hackathon API."
    api_url: str | None = None

    def run(self, queryKeys: list[str]) -> Dict[str, Any]:
        payload = {"queryKeys": queryKeys}
        return _post_json(
            "/hackhaton/get_collection_recommendations",
            payload,
            api_url=self.api_url,
        )


@dataclass
class ShopifyGetCustomerOrdersTool:
    """
    Tool: `shopify_get_customer_orders`

    Get customer orders.
    """

    name: str = "shopify_get_customer_orders"
    description: str = "Get customer orders via the hackathon API."
    api_url: str | None = None

    def run(self, email: str, after: str, limit: int) -> Dict[str, Any]:
        payload = {
            "email": email,
            "after": after,
            "limit": limit,
        }
        return _post_json("/hackhaton/get_customer_orders", payload, api_url=self.api_url)


@dataclass
class ShopifyGetOrderDetailsTool:
    """
    Tool: `shopify_get_order_details`

    Fetch detailed information for a single order by ID.
    """

    name: str = "shopify_get_order_details"
    description: str = "Get order details via the hackathon API."
    api_url: str | None = None

    def run(self, orderId: str) -> Dict[str, Any]:
        payload = {"orderId": orderId}
        return _post_json("/hackhaton/get_order_details", payload, api_url=self.api_url)


@dataclass
class ShopifyGetProductDetailsTool:
    """
    Tool: `shopify_get_product_details`

    Retrieve product information by product ID, name, or key feature.
    """

    name: str = "shopify_get_product_details"
    description: str = "Get product details via the hackathon API."
    api_url: str | None = None

    def run(self, queryType: str, queryKey: str) -> Dict[str, Any]:
        payload = {
            "queryType": queryType,
            "queryKey": queryKey,
        }
        return _post_json("/hackhaton/get_product_details", payload, api_url=self.api_url)


@dataclass
class ShopifyGetProductRecommendationsTool:
    """
    Tool: `shopify_get_product_recommendations`

    Generate product recommendations based on keyword intents.
    """

    name: str = "shopify_get_product_recommendations"
    description: str = "Get product recommendations via the hackathon API."
    api_url: str | None = None

    def run(self, queryKeys: list[str]) -> Dict[str, Any]:
        payload = {"queryKeys": queryKeys}
        return _post_json(
            "/hackhaton/get_product_recommendations",
            payload,
            api_url=self.api_url,
        )


@dataclass
class ShopifyGetRelatedKnowledgeSourceTool:
    """
    Tool: `shopify_get_related_knowledge_source`

    Retrieve related FAQs, PDFs, blog articles, and Shopify pages.
    """

    name: str = "shopify_get_related_knowledge_source"
    description: str = "Get related knowledge sources via the hackathon API."
    api_url: str | None = None

    def run(self, question: str, specificToProductId: str | None) -> Dict[str, Any]:
        payload = {
            "question": question,
            "specificToProductId": specificToProductId,
        }
        return _post_json(
            "/hackhaton/get_related_knowledge_source",
            payload,
            api_url=self.api_url,
        )


@dataclass
class ShopifyRefundOrderTool:
    """
    Tool: `shopify_refund_order`

    Refund an order.
    """

    name: str = "shopify_refund_order"
    description: str = "Refund an order via the hackathon API."
    api_url: str | None = None

    def run(self, orderId: str, refundMethod: str) -> Dict[str, Any]:
        payload = {
            "orderId": orderId,
            "refundMethod": refundMethod,
        }
        return _post_json("/hackhaton/refund_order", payload, api_url=self.api_url)


@dataclass
class ShopifyUpdateOrderShippingAddressTool:
    """
    Tool: `shopify_update_order_shipping_address`

    Update an order's shipping address.
    """

    name: str = "shopify_update_order_shipping_address"
    description: str = "Update order shipping address via the hackathon API."
    api_url: str | None = None

    def run(self, orderId: str, shippingAddress: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "orderId": orderId,
            "shippingAddress": shippingAddress,
        }
        return _post_json(
            "/hackhaton/update_order_shipping_address",
            payload,
            api_url=self.api_url,
        )


@dataclass
class SkioCancelSubscriptionTool:
    """
    Tool: `skio_cancel_subscription`

    Cancel a subscription, with reasons.
    """

    name: str = "skio_cancel_subscription"
    description: str = "Cancel a Skio subscription via the hackathon API."
    api_url: str | None = None

    def run(self, subscriptionId: str, cancellationReasons: list[str]) -> Dict[str, Any]:
        payload = {
            "subscriptionId": subscriptionId,
            "cancellationReasons": cancellationReasons,
        }
        return _post_json(
            "/hackhaton/cancel-subscription",
            payload,
            api_url=self.api_url,
        )


@dataclass
class SkioGetSubscriptionStatusTool:
    """
    Tool: `skio_get_subscription_status`

    Get the subscription status of a customer.
    """

    name: str = "skio_get_subscription_status"
    description: str = "Get Skio subscription status via the hackathon API."
    api_url: str | None = None

    def run(self, email: str) -> Dict[str, Any]:
        payload = {"email": email}
        return _post_json(
            "/hackhaton/get-subscription-status",
            payload,
            api_url=self.api_url,
        )


@dataclass
class SkioPauseSubscriptionTool:
    """
    Tool: `skio_pause_subscription`

    Pause a subscription.
    """

    name: str = "skio_pause_subscription"
    description: str = "Pause a Skio subscription via the hackathon API."
    api_url: str | None = None

    def run(self, subscriptionId: str, pausedUntil: str) -> Dict[str, Any]:
        payload = {
            "subscriptionId": subscriptionId,
            "pausedUntil": pausedUntil,
        }
        return _post_json(
            "/hackhaton/pause-subscription",
            payload,
            api_url=self.api_url,
        )


@dataclass
class SkioSkipNextOrderSubscriptionTool:
    """
    Tool: `skio_skip_next_order_subscription`

    Skip the next order of an ongoing subscription.
    """

    name: str = "skio_skip_next_order_subscription"
    description: str = "Skip the next Skio subscription order via the hackathon API."
    api_url: str | None = None

    def run(self, subscriptionId: str) -> Dict[str, Any]:
        payload = {"subscriptionId": subscriptionId}
        return _post_json(
            "/hackhaton/skip-next-order-subscription",
            payload,
            api_url=self.api_url,
        )


@dataclass
class SkioUnpauseSubscriptionTool:
    """
    Tool: `skio_unpause_subscription`

    Unpause a paused subscription.
    """

    name: str = "skio_unpause_subscription"
    description: str = "Unpause a Skio subscription via the hackathon API."
    api_url: str | None = None

    def run(self, subscriptionId: str) -> Dict[str, Any]:
        payload = {"subscriptionId": subscriptionId}
        return _post_json(
            "/hackhaton/unpause-subscription",
            payload,
            api_url=self.api_url,
        )

