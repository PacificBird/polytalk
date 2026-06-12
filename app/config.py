# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Configuration loader for PolyTalk application.

Loads configuration from YAML file and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Any
from dotenv import load_dotenv


class Config:
    """
    Application configuration manager.

    Loads configuration from config.yaml and environment variables.
    Environment variables in config values are expanded using ${VAR_NAME} syntax.
    """

    _instance: "Config | None" = None

    def __new__(cls) -> "Config":
        """Singleton pattern to ensure single config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize configuration if not already initialized."""
        if self._initialized:
            return

        # Load .env file
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        # Load config file
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        if not config_path.exists():
            config_path = (
                Path(__file__).parent.parent / "config" / "config.yaml.example"
            )

        if config_path.exists():
            with open(config_path, "r") as f:
                self._raw_config = yaml.safe_load(f)
        else:
            self._raw_config = {}

        # Expand environment variables in config
        self._config = self._expand_env_vars(self._raw_config)

        self._initialized = True

    def _expand_env_vars(self, obj: Any) -> Any:
        """
        Recursively expand environment variables in configuration.

        Args:
            obj: Configuration object (dict, list, or string)

        Returns:
            Configuration with environment variables expanded
        """
        if isinstance(obj, str):
            return self._expand_string(obj)
        elif isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        else:
            return obj

    def _expand_string(self, value: str) -> Any:
        """
        Expand environment variables in a string value.

        Args:
            value: String value that may contain ${VAR_NAME} patterns

        Returns:
            String with environment variables replaced, or original value if not a template
        """
        import re

        pattern = r"\$\{([^}]+)\}"

        def replace(match: Any) -> str:
            var_name = match.group(1)
            # Get value from environment, return original if not found
            env_value = os.environ.get(var_name)
            if env_value is not None:
                return env_value
            return match.group(0)

        result = re.sub(pattern, replace, value)

        # If no expansion happened, try to convert to appropriate type
        if result == value:
            if value.lower() == "true":
                return True
            elif value.lower() == "false":
                return False
            elif value.isdigit():
                return int(value)
            elif value.replace(".", "").isdigit() and value.count(".") == 1:
                return float(value)

        return result

    @property
    def whisper(self) -> dict:
        """Get Whisper configuration."""
        return self._config.get("whisper", {})

    @property
    def translation(self) -> dict:
        """Get translation AI configuration."""
        return self._config.get("translation", {})

    @property
    def visual_context(self) -> dict:
        """Get shared tab/page visual context configuration."""
        return self._config.get("visual_context", {})

    @property
    def tts(self) -> dict:
        """Get TTS configuration."""
        return self._config.get("tts", {})

    @property
    def app(self) -> dict:
        """Get application configuration."""
        return self._config.get("app", {})

    @property
    def media_output_dir(self) -> Path:
        """Get media output directory path."""
        return Path(self.app.get("media_output_dir", "media/output"))

    @property
    def debug(self) -> bool:
        """Get debug mode setting."""
        return bool(self.app.get("debug", False))

    @property
    def host(self) -> str:
        """Get application host."""
        return str(self.app.get("host", "0.0.0.0"))

    @property
    def port(self) -> int:
        """Get application port."""
        value = self.app.get("port", 8000)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 8000


def get_config() -> Config:
    """
    Get the singleton configuration instance.

    Returns:
        Config instance
    """
    return Config()
