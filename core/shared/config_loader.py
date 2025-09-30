"""Tenant configuration loader."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class TenantConfig:
    """
    Load and manage tenant-specific configuration.

    Configuration is loaded from tenants/{tenant_id}/config.yaml
    """

    def __init__(self, tenant_id: str, base_path: Optional[Path] = None):
        """
        Initialize tenant configuration loader.

        Args:
            tenant_id: Tenant identifier (slug)
            base_path: Base path for tenant directories (defaults to ./tenants)
        """
        self.tenant_id = tenant_id
        self.base_path = base_path or Path("tenants")
        self.config_path = self.base_path / tenant_id / "config.yaml"
        self._config: Optional[Dict[str, Any]] = None
        self.load()

    def load(self) -> None:
        """Load configuration from disk."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Configuration file not found: {self.config_path}")
                self._config = {}
                return

            with open(self.config_path, "r") as f:
                self._config = yaml.safe_load(f) or {}
            logger.info(f"Loaded configuration for tenant: {self.tenant_id}")
        except Exception as e:
            logger.error(f"Error loading config for {self.tenant_id}: {e}")
            self._config = {}

    def reload(self) -> None:
        """Reload configuration from disk."""
        logger.info(f"Reloading configuration for tenant: {self.tenant_id}")
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Configuration key (supports dot notation, e.g., "ai.model")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            config.get("ai.model")  # Returns "gpt-4"
            config.get("ai.temperature", 0.7)  # Returns 0.7 if not set
        """
        if self._config is None:
            return default

        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @property
    def branding(self) -> Dict[str, Any]:
        """Get branding configuration."""
        return self.get("branding", {})

    @property
    def ai_settings(self) -> Dict[str, Any]:
        """Get AI configuration."""
        return self.get("ai", {})

    @property
    def business_info(self) -> Dict[str, Any]:
        """Get business information."""
        return self.get("business", {})

    @property
    def features(self) -> Dict[str, bool]:
        """Get enabled features."""
        return self.get("features", {})

    @property
    def integrations(self) -> Dict[str, Any]:
        """Get integrations configuration."""
        return self.get("integrations", {})

    @property
    def rate_limiting(self) -> Dict[str, Any]:
        """Get rate limiting configuration."""
        return self.get("rate_limiting", {})

    @property
    def analytics(self) -> Dict[str, Any]:
        """Get analytics configuration."""
        return self.get("analytics", {})

    def __repr__(self) -> str:
        return f"<TenantConfig(tenant_id='{self.tenant_id}', loaded={self._config is not None})>"