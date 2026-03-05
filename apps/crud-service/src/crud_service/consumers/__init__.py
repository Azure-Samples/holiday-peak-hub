"""Event consumers for background processing."""

from crud_service.consumers.connector_sync import ConnectorSyncConsumer, get_connector_sync_consumer

__all__ = ["ConnectorSyncConsumer", "get_connector_sync_consumer"]
