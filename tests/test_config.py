# tests/test_config_loader.py
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from config.settings import Settings, load_config
from src.exceptions import ConfigError


def test_load_config_success(tmp_path):
    """
    Tests successful loading of a valid YAML configuration file.
    """
    config_content = {"database": {"user": "test_user", "password": "test_password"}}
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)

    config = load_config(config_file)
    assert config == config_content


def test_load_config_not_found():
    """
    Tests that a ConfigError is raised when the configuration file is not found.
    """
    non_existent_file = Path("non_existent_config.yaml")
    with pytest.raises(ConfigError, match="Configuration file not found"):
        load_config(non_existent_file)


def test_load_config_parsing_error(tmp_path):
    """
    Tests that a ConfigError is raised when the configuration file is malformed.
    """
    malformed_content = "database: { user: test_user"
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        f.write(malformed_content)

    with pytest.raises(ConfigError, match="Error parsing configuration file"):
        load_config(config_file)


def test_settings_load_successfully(monkeypatch):
    """
    Prueba que Settings carga correctamente cuando las variables de entorno existen.
    """
    # 1. ARRANGE: "Inyectamos" variables de entorno falsas en la memoria
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv(
        "DB_PORT", "1521"
    )  # Nota que enviamos string, Pydantic lo convertirá a int
    monkeypatch.setenv("DB_SERVICE_NAME", "ORCL")
    monkeypatch.setenv("DB_USER", "admin")
    monkeypatch.setenv("DB_PASSWORD", "secret")

    # 2. ACT
    settings = Settings()  # type: ignore

    # 3. ASSERT
    assert settings.db_host == "localhost"
    assert settings.db_port == 1521  # ¡Verificamos que se convirtió a entero!
    assert settings.db_password == "secret"


def test_settings_validation_error(monkeypatch):
    """
    Prueba que Pydantic lanza un error si el tipo de dato es incorrecto.
    """
    # Inyectamos un puerto que NO es un número
    monkeypatch.setenv("DB_PORT", "no-es-un-numero")

    # Rellenamos los otros obligatorios para aislar el error del puerto
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_SERVICE_NAME", "ORCL")
    monkeypatch.setenv("DB_USER", "admin")
    monkeypatch.setenv("DB_PASSWORD", "secret")

    # Verificamos que falle con ValidationError
    with pytest.raises(ValidationError) as excinfo:
        Settings()  # type: ignore

    # Opcional: Verificar que el error menciona 'db_port'
    assert "db_port" in str(excinfo.value)


def test_settings_missing_field(monkeypatch):
    """
    Prueba que falla si falta una variable obligatoria.
    """
    # Limpiamos el entorno para asegurar que no haya nada
    monkeypatch.delenv("DB_HOST", raising=False)

    # No definimos DB_HOST intencionalmente
    monkeypatch.setenv("DB_PORT", "1521")
    monkeypatch.setenv("DB_SERVICE_NAME", "ORCL")
    monkeypatch.setenv("DB_USER", "admin")
    monkeypatch.setenv("DB_PASSWORD", "secret")

    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None)  # type: ignore

    assert "Field required" in str(excinfo.value)
    assert "db_host" in str(excinfo.value)
