"""Canonical CRM schemas.

Standardizes account, contact, and interaction data so agents can build
customer context for the engagement scenarios described in the business
summary. Doctests illustrate validation and defaults.
"""

from datetime import datetime
from typing import Any, Optional

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
    region: Optional[str] = None
    owner: Optional[str] = None
    industry: Optional[str] = None
    tier: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class CRMContact(BaseModel):
    """Canonical representation of a CRM contact/person.

    >>> CRMContact(contact_id="C1", email="u@example.com").contact_id
    'C1'
    >>> CRMContact(contact_id="C2", marketing_opt_in=True).marketing_opt_in
    True
    """

    contact_id: str
    account_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    marketing_opt_in: bool = False
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
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
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    channel: str
    occurred_at: datetime
    duration_seconds: Optional[int] = None
    outcome: Optional[str] = None
    subject: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CRMContext(BaseModel):
    """Aggregate context the agent can consume.

    >>> contact = CRMContact(contact_id="C1")
    >>> account = CRMAccount(account_id="A1", name="Acme")
    >>> CRMContext(contact=contact, account=account).account.name
    'Acme'
    """

    contact: CRMContact
    account: Optional[CRMAccount] = None
    interactions: list[CRMInteraction] = Field(default_factory=list)