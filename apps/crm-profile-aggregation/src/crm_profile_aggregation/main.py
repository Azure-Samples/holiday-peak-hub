"""CRM profile aggregation service."""
from holiday_peak_lib.agents.memory import ColdMemory, HotMemory, WarmMemory
from holiday_peak_lib.agents.service_agent import ServiceAgent
from holiday_peak_lib.app_factory import build_service_app
from holiday_peak_lib.config import MemorySettings

SERVICE_NAME = "crm-profile-aggregation"
memory_settings = MemorySettings()
app = build_service_app(
	SERVICE_NAME,
	agent_class=ServiceAgent,
	hot_memory=HotMemory(memory_settings.redis_url),
	warm_memory=WarmMemory(
		memory_settings.cosmos_account_uri,
		memory_settings.cosmos_database,
		memory_settings.cosmos_container,
	),
	cold_memory=ColdMemory(
		memory_settings.blob_account_url,
		memory_settings.blob_container,
	),
)
