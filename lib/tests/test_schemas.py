"""Tests for CRM schemas."""
import pytest
from datetime import datetime
from holiday_peak_lib.schemas.crm import (
    CRMAccount,
    CRMContact,
    CRMInteraction,
    CRMContext,
)


class TestCRMAccount:
    """Test CRMAccount schema."""

    def test_create_minimal_account(self):
        """Test creating account with minimal fields."""
        account = CRMAccount(account_id="A123", name="Test Corp")
        assert account.account_id == "A123"
        assert account.name == "Test Corp"
        assert account.region is None
        assert account.attributes == {}

    def test_create_full_account(self):
        """Test creating account with all fields."""
        account = CRMAccount(
            account_id="A123",
            name="Test Corp",
            region="US-West",
            owner="john.doe@example.com",
            industry="Technology",
            tier="Enterprise",
            lifecycle_stage="Active",
            attributes={"employees": 500, "revenue": "10M"}
        )
        assert account.account_id == "A123"
        assert account.name == "Test Corp"
        assert account.region == "US-West"
        assert account.industry == "Technology"
        assert account.tier == "Enterprise"
        assert account.attributes["employees"] == 500

    def test_account_defaults(self):
        """Test account default values."""
        account = CRMAccount(account_id="A1", name="Test")
        assert account.attributes == {}
        assert account.region is None
        assert account.owner is None

    def test_account_validation(self):
        """Test account field validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            CRMAccount(account_id="A1")  # Missing name
        
        with pytest.raises(Exception):
            CRMAccount(name="Test")  # Missing account_id


class TestCRMContact:
    """Test CRMContact schema."""

    def test_create_minimal_contact(self):
        """Test creating contact with minimal fields."""
        contact = CRMContact(contact_id="C123", email="test@example.com")
        assert contact.contact_id == "C123"
        assert contact.email == "test@example.com"
        assert contact.marketing_opt_in is False
        assert contact.tags == []

    def test_create_full_contact(self):
        """Test creating contact with all fields."""
        contact = CRMContact(
            contact_id="C123",
            account_id="A456",
            email="john@example.com",
            phone="+1-555-0100",
            locale="en-US",
            timezone="America/Los_Angeles",
            marketing_opt_in=True,
            first_name="John",
            last_name="Doe",
            title="VP Engineering",
            tags=["vip", "technical"],
            preferences={"newsletter": True, "frequency": "weekly"},
            attributes={"linkedin": "johndoe"}
        )
        assert contact.contact_id == "C123"
        assert contact.account_id == "A456"
        assert contact.first_name == "John"
        assert contact.last_name == "Doe"
        assert contact.marketing_opt_in is True
        assert len(contact.tags) == 2
        assert contact.preferences["newsletter"] is True

    def test_contact_defaults(self):
        """Test contact default values."""
        contact = CRMContact(contact_id="C1")
        assert contact.marketing_opt_in is False
        assert contact.tags == []
        assert contact.preferences == {}
        assert contact.attributes == {}

    def test_contact_opt_in_behavior(self):
        """Test marketing opt-in behavior."""
        contact_opted_out = CRMContact(contact_id="C1")
        contact_opted_in = CRMContact(contact_id="C2", marketing_opt_in=True)
        
        assert contact_opted_out.marketing_opt_in is False
        assert contact_opted_in.marketing_opt_in is True


class TestCRMInteraction:
    """Test CRMInteraction schema."""

    def test_create_minimal_interaction(self):
        """Test creating interaction with minimal fields."""
        interaction = CRMInteraction(
            interaction_id="I123",
            channel="email",
            occurred_at=datetime(2024, 1, 15, 10, 30)
        )
        assert interaction.interaction_id == "I123"
        assert interaction.channel == "email"
        assert interaction.occurred_at.year == 2024
        assert interaction.metadata == {}

    def test_create_full_interaction(self):
        """Test creating interaction with all fields."""
        interaction = CRMInteraction(
            interaction_id="I123",
            contact_id="C456",
            account_id="A789",
            channel="phone",
            occurred_at=datetime(2024, 1, 15, 10, 30),
            duration_seconds=300,
            outcome="resolved",
            subject="Support Request",
            summary="Customer needed help with API integration",
            sentiment="positive",
            metadata={"agent": "Jane", "category": "technical"}
        )
        assert interaction.interaction_id == "I123"
        assert interaction.contact_id == "C456"
        assert interaction.channel == "phone"
        assert interaction.duration_seconds == 300
        assert interaction.outcome == "resolved"
        assert interaction.sentiment == "positive"
        assert interaction.metadata["agent"] == "Jane"

    def test_interaction_channels(self):
        """Test different interaction channels."""
        channels = ["email", "phone", "chat", "social", "in-person"]
        for channel in channels:
            interaction = CRMInteraction(
                interaction_id=f"I_{channel}",
                channel=channel,
                occurred_at=datetime.now()
            )
            assert interaction.channel == channel

    def test_interaction_datetime_handling(self):
        """Test datetime handling in interactions."""
        now = datetime(2024, 6, 15, 14, 30, 0)
        interaction = CRMInteraction(
            interaction_id="I1",
            channel="email",
            occurred_at=now
        )
        assert interaction.occurred_at == now
        assert interaction.occurred_at.hour == 14
        assert interaction.occurred_at.minute == 30


class TestCRMContext:
    """Test CRMContext aggregate schema."""

    def test_create_minimal_context(self):
        """Test creating context with minimal fields."""
        contact = CRMContact(contact_id="C123")
        context = CRMContext(contact=contact)
        assert context.contact.contact_id == "C123"
        assert context.account is None
        assert context.interactions == []

    def test_create_full_context(self):
        """Test creating context with all fields."""
        contact = CRMContact(
            contact_id="C123",
            email="test@example.com",
            first_name="John"
        )
        account = CRMAccount(
            account_id="A456",
            name="Test Corp",
            tier="Enterprise"
        )
        interactions = [
            CRMInteraction(
                interaction_id="I1",
                channel="email",
                occurred_at=datetime(2024, 1, 10)
            ),
            CRMInteraction(
                interaction_id="I2",
                channel="phone",
                occurred_at=datetime(2024, 1, 12)
            )
        ]
        
        context = CRMContext(
            contact=contact,
            account=account,
            interactions=interactions
        )
        
        assert context.contact.contact_id == "C123"
        assert context.account.account_id == "A456"
        assert len(context.interactions) == 2
        assert context.interactions[0].channel == "email"

    def test_context_with_rich_interaction_history(self):
        """Test context with multiple interactions."""
        contact = CRMContact(contact_id="C1", email="test@example.com")
        interactions = [
            CRMInteraction(
                interaction_id=f"I{i}",
                contact_id="C1",
                channel="email",
                occurred_at=datetime(2024, 1, i + 1),
                sentiment=["positive", "neutral", "negative"][i % 3]
            )
            for i in range(10)
        ]
        
        context = CRMContext(contact=contact, interactions=interactions)
        assert len(context.interactions) == 10
        assert context.interactions[0].sentiment == "positive"
        assert context.interactions[1].sentiment == "neutral"

    def test_context_account_optional(self):
        """Test that account is optional in context."""
        contact = CRMContact(contact_id="C1")
        context = CRMContext(contact=contact)
        assert context.account is None
        
        # Add account later
        account = CRMAccount(account_id="A1", name="Test")
        context2 = CRMContext(contact=contact, account=account)
        assert context2.account is not None
        assert context2.account.name == "Test"

    def test_context_json_serialization(self):
        """Test context JSON serialization."""
        contact = CRMContact(contact_id="C1", email="test@example.com")
        account = CRMAccount(account_id="A1", name="Test Corp")
        context = CRMContext(contact=contact, account=account)
        
        # Test that it can be converted to dict
        context_dict = context.model_dump()
        assert context_dict["contact"]["contact_id"] == "C1"
        assert context_dict["account"]["name"] == "Test Corp"


class TestSchemaValidation:
    """Test schema validation edge cases."""

    def test_account_empty_attributes(self):
        """Test account with empty attributes."""
        account = CRMAccount(
            account_id="A1",
            name="Test",
            attributes={}
        )
        assert account.attributes == {}

    def test_contact_empty_collections(self):
        """Test contact with empty collections."""
        contact = CRMContact(
            contact_id="C1",
            tags=[],
            preferences={},
            attributes={}
        )
        assert contact.tags == []
        assert contact.preferences == {}
        assert contact.attributes == {}

    def test_interaction_metadata_flexibility(self):
        """Test interaction metadata flexibility."""
        interaction = CRMInteraction(
            interaction_id="I1",
            channel="email",
            occurred_at=datetime.now(),
            metadata={
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "bool": True,
                "number": 42
            }
        )
        assert interaction.metadata["nested"]["key"] == "value"
        assert interaction.metadata["list"] == [1, 2, 3]
        assert interaction.metadata["bool"] is True
