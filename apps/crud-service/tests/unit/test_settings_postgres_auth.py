"""Tests for PostgreSQL auth mode defaults and overrides in CRUD settings."""

from urllib.parse import quote

from crud_service.config.settings import Settings

REQUIRED_ENV = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_USER": "test-user",
    "EVENT_HUB_NAMESPACE": "test-namespace.servicebus.windows.net",
    "KEY_VAULT_URI": "https://test-vault.vault.azure.net/",
    "REDIS_HOST": "localhost",
}


def _set_required_env(monkeypatch) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)


def test_postgres_auth_mode_defaults_to_password(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.delenv("POSTGRES_AUTH_MODE", raising=False)
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")

    settings = Settings()

    assert settings.postgres_auth_mode == "password"
    assert settings.postgres_dsn.startswith("postgresql://test-user:test-password@")


def test_postgres_password_mode_is_explicit_opt_in(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("POSTGRES_AUTH_MODE", "password")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")

    settings = Settings()

    assert settings.postgres_auth_mode == "password"
    assert settings.postgres_dsn.startswith("postgresql://test-user:test-password@")


def test_postgres_entra_mode_is_explicit_opt_in(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("POSTGRES_AUTH_MODE", "entra")

    settings = Settings()

    assert settings.postgres_auth_mode == "entra"


def test_redis_password_secret_name_defaults_to_infra_secret(monkeypatch) -> None:
    _set_required_env(monkeypatch)

    settings = Settings()

    assert settings.redis_password_secret_name == "redis-primary-key"


def test_redis_url_includes_url_encoded_password_when_present(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    raw_password = "p@ss:/ with?#[]"
    monkeypatch.setenv("REDIS_PASSWORD", raw_password)

    settings = Settings()

    expected_password = quote(raw_password, safe="")
    assert settings.redis_url == f"rediss://:{expected_password}@localhost:6380/0"


def test_redis_url_omits_auth_segment_without_password(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.delenv("REDIS_PASSWORD", raising=False)

    settings = Settings()

    assert settings.redis_url == "rediss://localhost:6380/0"
