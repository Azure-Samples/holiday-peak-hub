"""Checkout session repository."""

from crud_service.repositories.base import BaseRepository


class CheckoutSessionRepository(BaseRepository):
    """Repository for ACP checkout sessions."""

    def __init__(self):
        super().__init__(container_name="checkout_sessions")
