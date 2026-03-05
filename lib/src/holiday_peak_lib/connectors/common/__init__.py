"""Common package for connector protocols, versioning utilities, and canonical types."""

from holiday_peak_lib.connectors.common.versioning import (
    BaseConnectorProtocol,
    FieldSpec,
    PIMConnectorProtocol_v1,
    PIMConnectorProtocol_v2,
    ProtocolDiff,
    ProtocolVersion,
    VersionedAdapter,
    diff_protocols,
    negotiate_version,
    register_protocol,
)

__all__ = [
    "BaseConnectorProtocol",
    "FieldSpec",
    "PIMConnectorProtocol_v1",
    "PIMConnectorProtocol_v2",
    "ProtocolDiff",
    "ProtocolVersion",
    "VersionedAdapter",
    "diff_protocols",
    "negotiate_version",
    "register_protocol",
]
