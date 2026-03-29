import os
import pytest
from pydantic import ValidationError
from src.core.config import Settings, settings

def test_settings_default_values():
    # settings object from app should have some values populated
    assert settings.IP_ADDRESS is not None
    assert settings.PORT is not None
    assert settings.LOG_LEVEL is not None
    assert settings.GITHUB_API_URL == "https://api.github.com"
    # OAUTH_SECRET and CLIENT_ID should be loaded from env or .env

def test_settings_override_via_env(monkeypatch):
    monkeypatch.setenv("IP_ADDRESS", "0.0.0.0")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("OAUTH_SECRET", "test_secret")
    monkeypatch.setenv("OAUTH_CLIENT_ID", "test_client")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "http://localhost/callback")

    test_settings = Settings()
    
    assert test_settings.IP_ADDRESS == "0.0.0.0"
    assert test_settings.PORT == 9000
    assert test_settings.LOG_LEVEL == "debug"
    assert test_settings.OAUTH_SECRET == "test_secret"

def test_settings_validation_error(monkeypatch):
    monkeypatch.setenv("PORT", "not_an_int")
    monkeypatch.setenv("OAUTH_SECRET", "test")
    monkeypatch.setenv("OAUTH_CLIENT_ID", "test")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "test")
    
    with pytest.raises(ValidationError):
        Settings()
