"""Register the public Vision Chat Completions interface for ALE-Claw."""

from dataclasses import replace

from ale_run.agents.ale_claw.harness.model.model_config import (
    HelperTransportDefaults,
    get_model_config,
    register_model_config,
)
from ale_run.agents.ale_claw.harness.model.unified_loop import UnifiedAgentConfig, register_agent
from ale_run.cli import main

MODEL_ID = "openai/vispark/vision-large"
MODEL_PATTERN = r"^openai/vispark/vision-large$"

register_agent(models=MODEL_PATTERN, priority=20)(UnifiedAgentConfig)
register_model_config(MODEL_PATTERN, replace(
    get_model_config(MODEL_ID), provider="openai", model_api="chat",
    helper_transport_defaults=HelperTransportDefaults(), context_window=980000,
))

if __name__ == "__main__":
    raise SystemExit(main())
