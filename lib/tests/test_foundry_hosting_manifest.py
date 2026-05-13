"""Tests for the Foundry hosted-agent manifest parser."""

from __future__ import annotations

from pathlib import Path

import pytest
from holiday_peak_lib.foundry_hosting.manifest import (
    HostedAgentManifest,
    load_manifest,
    resolve_environment_variables,
)

CANONICAL_YAML = """\
name: sample-hosted-agent
description: hosted-agent under test
metadata:
  tags: [unit-test]
template:
  name: sample-hosted-agent
  kind: hosted
  protocols:
    - protocol: responses
      version: "1.0.0"
  environment_variables:
    - name: AZURE_AI_MODEL_DEPLOYMENT_NAME
      value: "{{AZURE_AI_MODEL_DEPLOYMENT_NAME}}"
    - name: LITERAL_VAR
      value: literal-value
container:
  cpu: "1"
  memory: 2Gi
resources:
  - kind: model
    id: gpt-5-nano
    name: AZURE_AI_MODEL_DEPLOYMENT_NAME
"""


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "agent.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def test_load_manifest_accepts_canonical_shape(tmp_path: Path) -> None:
    manifest = load_manifest(_write(tmp_path, CANONICAL_YAML))
    assert isinstance(manifest, HostedAgentManifest)
    assert manifest.name == "sample-hosted-agent"
    assert manifest.template.kind == "hosted"
    assert manifest.template.protocols[0].protocol == "responses"
    assert manifest.template.protocols[0].version == "1.0.0"
    assert manifest.container.cpu == "1"
    assert manifest.container.memory == "2Gi"
    assert manifest.resources[0].id == "gpt-5-nano"


def test_load_manifest_accepts_directory(tmp_path: Path) -> None:
    _write(tmp_path, CANONICAL_YAML)
    manifest = load_manifest(tmp_path)
    assert manifest.name == "sample-hosted-agent"


def test_load_manifest_prefers_canonical_filename_in_directory(tmp_path: Path) -> None:
    # When canonical ``agent.manifest.yaml`` is present alongside any other
    # candidate it must win (it is the name the official Microsoft
    # foundry-samples repository and ``azd ai agent init -m`` use).
    (tmp_path / "agent.yaml").write_text(
        CANONICAL_YAML.replace("sample-hosted-agent", "tracking-only-name"), encoding="utf-8"
    )
    (tmp_path / "agent.hosted.yaml").write_text(
        CANONICAL_YAML.replace("sample-hosted-agent", "hosted-fallback-name"), encoding="utf-8"
    )
    (tmp_path / "agent.manifest.yaml").write_text(CANONICAL_YAML, encoding="utf-8")
    manifest = load_manifest(tmp_path)
    assert manifest.name == "sample-hosted-agent"


def test_load_manifest_prefers_agent_hosted_yaml_when_canonical_missing(tmp_path: Path) -> None:
    # When ``agent.manifest.yaml`` is absent the loader must still prefer
    # the project-internal ``agent.hosted.yaml`` over the legacy
    # ``agent.yaml`` portal-tracking shape.
    (tmp_path / "agent.yaml").write_text(
        CANONICAL_YAML.replace("sample-hosted-agent", "tracking-only-name"), encoding="utf-8"
    )
    (tmp_path / "agent.hosted.yaml").write_text(CANONICAL_YAML, encoding="utf-8")
    manifest = load_manifest(tmp_path)
    assert manifest.name == "sample-hosted-agent"


def test_load_manifest_directory_without_any_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="agent.manifest.yaml, agent.hosted.yaml or agent.yaml",
    ):
        load_manifest(tmp_path)


def test_load_manifest_rejects_direct_model_kind(tmp_path: Path) -> None:
    bad = CANONICAL_YAML.replace("kind: hosted", "kind: direct-model")
    with pytest.raises(Exception) as exc:
        load_manifest(_write(tmp_path, bad))
    assert "hosted" in str(exc.value)


def test_load_manifest_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "does-not-exist.yaml")


def test_resolve_environment_variables_substitutes_placeholder(tmp_path: Path) -> None:
    manifest = load_manifest(_write(tmp_path, CANONICAL_YAML))
    env = {"AZURE_AI_MODEL_DEPLOYMENT_NAME": "gpt-5-nano-deployment"}
    resolved = resolve_environment_variables(manifest, env=env)
    assert resolved["AZURE_AI_MODEL_DEPLOYMENT_NAME"] == "gpt-5-nano-deployment"
    assert resolved["LITERAL_VAR"] == "literal-value"


def test_resolve_environment_variables_strict_raises_on_missing(tmp_path: Path) -> None:
    manifest = load_manifest(_write(tmp_path, CANONICAL_YAML))
    with pytest.raises(KeyError, match="AZURE_AI_MODEL_DEPLOYMENT_NAME"):
        resolve_environment_variables(manifest, env={})


def test_resolve_environment_variables_non_strict_keeps_placeholder(tmp_path: Path) -> None:
    manifest = load_manifest(_write(tmp_path, CANONICAL_YAML))
    resolved = resolve_environment_variables(manifest, env={}, strict=False)
    assert resolved["AZURE_AI_MODEL_DEPLOYMENT_NAME"] == "{{AZURE_AI_MODEL_DEPLOYMENT_NAME}}"
