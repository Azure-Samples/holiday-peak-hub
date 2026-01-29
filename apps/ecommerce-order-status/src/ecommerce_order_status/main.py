"""Ecommerce Order Status service entrypoint."""
import os

from holiday_peak_lib.agents import FoundryAgentConfig
from holiday_peak_lib.agents.memory import ColdMemory, HotMemory, WarmMemory
from holiday_peak_lib.app_factory import build_service_app
from holiday_peak_lib.config import MemorySettings

from ecommerce_order_status.agents import OrderStatusAgent, register_mcp_tools

SERVICE_NAME = "ecommerce-order-status"
memory_settings = MemorySettings()
endpoint = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
project_name = os.getenv("PROJECT_NAME") or os.getenv("FOUNDRY_PROJECT_NAME")
stream = (os.getenv("FOUNDRY_STREAM") or "").lower() in {"1", "true", "yes"}
slm_agent_id = os.getenv("FOUNDRY_AGENT_ID_FAST")
llm_agent_id = os.getenv("FOUNDRY_AGENT_ID_RICH")
slm_deployment = os.getenv("MODEL_DEPLOYMENT_NAME_FAST")
llm_deployment = os.getenv("MODEL_DEPLOYMENT_NAME_RICH")

slm_config = (
	FoundryAgentConfig(
		endpoint=endpoint,
		agent_id=slm_agent_id,
		deployment_name=slm_deployment,
		project_name=project_name,
		stream=stream,
	)
	if endpoint and slm_agent_id
	else None
)

llm_config = (
	FoundryAgentConfig(
		endpoint=endpoint,
		agent_id=llm_agent_id,
		deployment_name=llm_deployment,
		project_name=project_name,
		stream=stream,
	)
	if endpoint and llm_agent_id
	else None
)
app = build_service_app(
	SERVICE_NAME,
	agent_class=OrderStatusAgent,
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
	slm_config=slm_config,
	llm_config=llm_config,
	mcp_setup=register_mcp_tools,
)
