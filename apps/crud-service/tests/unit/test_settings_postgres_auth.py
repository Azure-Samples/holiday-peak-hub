"""Tests for PostgreSQL auth mode defaults and overrides in CRUD settings."""

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
