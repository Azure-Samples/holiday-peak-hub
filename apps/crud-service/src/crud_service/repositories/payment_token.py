"""Payment token repository."""

from crud_service.repositories.base import BaseRepository


class PaymentTokenRepository(BaseRepository):
    """Repository for delegated payment tokens."""

    def __init__(self):
        super().__init__(container_name="payment_tokens")
