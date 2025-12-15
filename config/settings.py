from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from exceptions import ConfigError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    db_host: str
    db_port: int
    db_service_name: str
    db_user: str
    db_password: str


settings = Settings()  # type: ignore


def load_config(config_path: Path) -> Dict[str, Any]:
    """
    Loads configuration from a YAML file.

    Args:
        config_path: The path to the YAML configuration file.

    Returns:
        A dictionary containing the configuration.

    Raises:
        ConfigError: If the configuration file cannot be found or parsed.
    """
    if not config_path.is_file():
        raise ConfigError(f"Configuration file not found: {config_path}")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing configuration file {config_path}: {e}")
    except Exception as e:
        raise ConfigError(
            f"An unexpected error occurred while loading config {config_path}: {e}"
        )
