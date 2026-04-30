#!/usr/bin/env python3
"""Seed one or more HITL review queue items via Event Hub `hitl-jobs`."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

from azure.identity.aio import DefaultAzureCredential
from azure.eventhub import EventData, TransportType
from azure.eventhub.aio import EventHubProducerClient


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish deterministic HITL queue events to Event Hub."
    )
    parser.add_argument(
        "--connection-string",
        default=_first_env("EVENT_HUB_CONNECTION_STRING", "EVENTHUB_CONNECTION_STRING"),
        help=(
            "Event Hub namespace connection string. "
            "Defaults to EVENT_HUB_CONNECTION_STRING or EVENTHUB_CONNECTION_STRING."
        ),
    )
    parser.add_argument(
        "--namespace",
        default=_first_env("EVENT_HUB_NAMESPACE", "EVENTHUB_NAMESPACE"),
        help=(
            "Event Hub namespace name (for example: myns-dev-eventhub). "
            "Defaults to EVENT_HUB_NAMESPACE or EVENTHUB_NAMESPACE."
        ),
    )
    parser.add_argument(
        "--auth-mode",
        choices=("auto", "connection-string", "identity"),
        default="auto",
        help="Authentication mode. auto prefers connection string, then identity. Defaults to auto.",
    )
    parser.add_argument(
        "--topic",
        default=_first_env("EVENT_HUB_TOPIC", "EVENTHUB_TOPIC") or "hitl-jobs",
        help="Event Hub topic name. Defaults to hitl-jobs.",
    )
    parser.add_argument(
        "--transport",
        choices=("amqp", "websocket"),
        default="websocket",
        help=(
            "Event Hubs transport mode. Use websocket when 5671 outbound is restricted. "
            "Defaults to websocket."
        ),
    )
    parser.add_argument(
        "--entity-id",
        required=True,
        help="Entity/product ID to appear in review queue.",
    )
    parser.add_argument(
        "--field-name",
        required=True,
        help="Proposed field name (for example: material, color, dimensions).",
    )
    parser.add_argument(
        "--proposed-value",
        required=True,
        help="Proposed value for the target field.",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.42,
        help="Confidence score to attach. Defaults to 0.42.",
    )
    parser.add_argument(
        "--current-value",
        default="",
        help="Current value for the field. Empty string maps to null.",
    )
    parser.add_argument(
        "--product-title",
        default="",
        help="Optional product title shown in queue detail.",
    )
    parser.add_argument(
        "--category-label",
        default="",
        help="Optional category label shown in queue detail.",
    )
    parser.add_argument(
        "--source",
        default="ai",
        help="Source label. Defaults to ai.",
    )
    parser.add_argument(
        "--source-type",
        default="text_enrichment",
        help="Source type label. Defaults to text_enrichment.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of events to publish. Defaults to 1.",
    )
    parser.add_argument(
        "--attr-prefix",
        default="demo-attr",
        help="Prefix for generated attr_id values. Defaults to demo-attr.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print payload(s) without publishing.",
    )
    return parser.parse_args()


def build_payload(args: argparse.Namespace, attr_id: str) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    current_value: object | None = args.current_value if args.current_value else None

    return {
        "event_type": "attribute.proposed",
        "data": {
            "entity_id": args.entity_id,
            "attr_id": attr_id,
            "field_name": args.field_name,
            "proposed_value": args.proposed_value,
            "confidence": args.confidence,
            "current_value": current_value,
            "source": args.source,
            "proposed_at": now,
            "product_title": args.product_title,
            "category_label": args.category_label,
            "source_type": args.source_type,
        },
    }


async def publish_events(args: argparse.Namespace, payloads: list[dict[str, Any]]) -> None:
    transport_type = (
        TransportType.Amqp
        if args.transport == "amqp"
        else TransportType.AmqpOverWebsocket
    )

    use_connection_string = False

    if args.auth_mode == "connection-string":
        use_connection_string = True
    elif args.auth_mode == "identity":
        pass
    else:
        use_connection_string = bool(args.connection_string)

    if use_connection_string:
        async with EventHubProducerClient.from_connection_string(
            args.connection_string,
            eventhub_name=args.topic,
            transport_type=transport_type,
        ) as producer:
            batch = await producer.create_batch()
            for payload in payloads:
                batch.add(EventData(json.dumps(payload)))
            await producer.send_batch(batch)
        return

    if not args.namespace:
        raise RuntimeError(
            "Missing Event Hub namespace. Set EVENT_HUB_NAMESPACE or pass --namespace."
        )

    fully_qualified_namespace = (
        args.namespace
        if "." in args.namespace
        else f"{args.namespace}.servicebus.windows.net"
    )

    credential = DefaultAzureCredential()
    try:
        async with EventHubProducerClient(
            fully_qualified_namespace=fully_qualified_namespace,
            eventhub_name=args.topic,
            credential=credential,
            transport_type=transport_type,
        ) as producer:
            batch = await producer.create_batch()
            for payload in payloads:
                batch.add(EventData(json.dumps(payload)))
            await producer.send_batch(batch)
    finally:
        await credential.close()


def main() -> int:
    args = parse_args()

    if args.count < 1:
        print("--count must be >= 1", file=sys.stderr)
        return 2

    if not args.dry_run:
        if args.auth_mode == "connection-string" and not args.connection_string:
            print(
                "Missing Event Hub connection string. Set EVENT_HUB_CONNECTION_STRING or pass --connection-string.",
                file=sys.stderr,
            )
            return 2
        if args.auth_mode == "identity" and not args.namespace:
            print(
                "Missing Event Hub namespace. Set EVENT_HUB_NAMESPACE or pass --namespace.",
                file=sys.stderr,
            )
            return 2
        if args.auth_mode == "auto" and not args.connection_string and not args.namespace:
            print(
                (
                    "Missing Event Hub auth settings. Provide EVENT_HUB_CONNECTION_STRING/"
                    "EVENTHUB_CONNECTION_STRING or EVENT_HUB_NAMESPACE/EVENTHUB_NAMESPACE."
                ),
                file=sys.stderr,
            )
            return 2

    payloads: list[dict[str, Any]] = []
    attr_ids: list[str] = []
    for index in range(args.count):
        suffix = uuid.uuid4().hex[:10]
        attr_id = f"{args.attr_prefix}-{index + 1:03d}-{suffix}"
        attr_ids.append(attr_id)
        payloads.append(build_payload(args, attr_id))

    if args.dry_run:
        print(json.dumps(payloads, indent=2))
        return 0

    asyncio.run(publish_events(args, payloads))

    print(
        "Published hitl-jobs events:",
        json.dumps(
            {
                "topic": args.topic,
                "count": len(payloads),
                "entity_id": args.entity_id,
                "field_name": args.field_name,
                "attr_ids": attr_ids,
            },
            indent=2,
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
