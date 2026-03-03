"""SAP S/4HANA connector for Inventory & SCM.

Environment variables
---------------------
SAP_S4HANA_BASE_URL      Base URL, e.g. https://api.sap.com
SAP_S4HANA_TOKEN_URL     OAuth 2.0 token endpoint
SAP_S4HANA_CLIENT_ID     OAuth 2.0 client ID
SAP_S4HANA_CLIENT_SECRET OAuth 2.0 client secret
SAP_S4HANA_API_KEY       API key (alternative to OAuth 2.0)
"""

from holiday_peak_lib.connectors.inventory_scm.sap_s4hana.connector import SAPS4HANAConnector

__all__ = ["SAPS4HANAConnector"]
