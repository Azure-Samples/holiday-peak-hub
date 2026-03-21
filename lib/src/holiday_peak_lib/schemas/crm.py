"""Canonical CRM schemas.

Standardizes account, contact, and interaction data so agents can build
customer context for the engagement scenarios described in the business
summary. Doctests illustrate validation and defaults.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CRMAccount(BaseModel):
    """Canonical representation of a CRM account/organization.

    >>> CRMAccount(account_id="A1", name="Acme").name
    'Acme'
    >>> CRMAccount(account_id="A2", name="Beta", attributes={"plan": "pro"}).attributes["plan"]
    'pro'
    """

    account_id: str
    name: str
    region: str | None = None
    owner: str | None = None
    industry: str | None = None
    tier: str | None = None
    lifecycle_stage: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class CRMContact(BaseModel):
    """Canonical representation of a CRM contact/person.

    >>> CRMContact(contact_id="C1", email="u@example.com").contact_id
    'C1'
    >>> CRMContact(contact_id="C2", marketing_opt_in=True).marketing_opt_in
    True
    """

    contact_id: str
    account_id: str | None = None
    email: str | None = None
    phone: str | None = None
    locale: str | None = None
    timezone: str | None = None
    marketing_opt_in: bool = False
    first_name: str | None = None
    last_name: str | None = None
    title: str | None = None
    tags: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)


class CRMInteraction(BaseModel):
    """Canonical representation of a CRM interaction/event.

    >>> CRMInteraction(
    ...     interaction_id="I1",
    ...     channel="email",
    ...     occurred_at=datetime(2024, 1, 1),
    ... ).channel
    'email'
    """

    interaction_id: str
    contact_id: str | None = None
    account_id: str | None = None
    channel: str
    occurred_at: datetime
    duration_seconds: int | None = None
    outcome: str | None = None
    subject: str | None = None
    summary: str | None = None
    sentiment: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CRMContext(BaseModel):
    """Aggregate context the agent can consume.

    >>> contact = CRMContact(contact_id="C1")
    >>> account = CRMAccount(account_id="A1", name="Acme")
    >>> CRMContext(contact=contact, account=account).account.name
    'Acme'
    """

    contact: CRMContact
    account: CRMAccount | None = None
    interactions: list[CRMInteraction] = Field(default_factory=list)
