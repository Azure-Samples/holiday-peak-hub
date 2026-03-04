"""Product consistency validation service."""

import os

from holiday_peak_lib.agents import FoundryAgentConfig
from holiday_peak_lib.agents.memory import ColdMemory, HotMemory, WarmMemory
from holiday_peak_lib.app_factory import build_service_app
from holiday_peak_lib.config import MemorySettings
from holiday_peak_lib.utils import EventHubSubscription, create_eventhub_lifespan
from product_management_consistency_validation.agents import (
    ProductConsistencyAgent,
    register_mcp_tools,
)
from product_management_consistency_validation.event_consumer import (
    build_completeness_event_handlers,
)
from product_management_consistency_validation.event_handlers import (
    build_event_handlers,
)

SERVICE_NAME = "product-management-consistency-validation"
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

# Merge product-events handlers (backward compat) with completeness-jobs handlers
_all_handlers = {
    **build_event_handlers(),
    **build_completeness_event_handlers(
        completeness_threshold=float(os.getenv("COMPLETENESS_THRESHOLD", "0.7"))
    ),
}

app = build_service_app(
    SERVICE_NAME,
    agent_class=ProductConsistencyAgent,
    hot_memory=(HotMemory(memory_settings.redis_url) if memory_settings.redis_url else None),
    warm_memory=(
        WarmMemory(
            memory_settings.cosmos_account_uri,
            memory_settings.cosmos_database,
            memory_settings.cosmos_container,
        )
        if memory_settings.cosmos_account_uri
        else None
    ),
    cold_memory=(
        ColdMemory(
            memory_settings.blob_account_url,
            memory_settings.blob_container,
        )
        if memory_settings.blob_account_url
        else None
    ),
    slm_config=slm_config,
    llm_config=llm_config,
    mcp_setup=register_mcp_tools,
    lifespan=create_eventhub_lifespan(
        service_name=SERVICE_NAME,
        subscriptions=[
            EventHubSubscription("product-events", "validation-group"),
            EventHubSubscription("completeness-jobs", "completeness-engine"),
        ],
        handlers=_all_handlers,
    ),
)
