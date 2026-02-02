"""Plugin lifecycle management system."""

import asyncio
from datetime import datetime
from typing import Dict, Optional, List
from src.core.logger import get_logger
from src.core.config import DemiConfig
from src.plugins.discovery import discover_plugins
from src.plugins.base import PluginState, PluginMetadata
from src.platforms.base import BasePlatform, PluginHealth


logger = get_logger()


class PluginManager:
    """Manages plugin discovery, loading, unloading, and health monitoring."""

    def __init__(self):
        """Initialize plugin manager."""
        self.registry: Dict[str, PluginMetadata] = {}
        self._config = DemiConfig()
        self._discovered_plugins: Dict[str, type] = {}

    async def discover_and_register(self) -> None:
        """Discover plugins and register them in the registry.

        This scans for available plugins via entry points and registers
        their metadata without loading them yet.
        """
        logger.debug("Starting plugin discovery...")

        # Discover available plugins
        self._discovered_plugins = discover_plugins()

        # Register discovered plugins
        for plugin_name, plugin_class in self._discovered_plugins.items():
            metadata = PluginMetadata(
                name=plugin_name,
                state=PluginState.REGISTERED,
                plugin_class=plugin_class,
            )
            self.registry[plugin_name] = metadata
            logger.info(f"Registered plugin: {plugin_name}")

        logger.info(
            f"Plugin discovery complete: {len(self.registry)} plugins registered"
        )

    async def load_plugin(
        self, name: str, config: Optional[dict] = None
    ) -> Optional[BasePlatform]:
        """Load and initialize a plugin.

        Args:
            name: Plugin name to load
            config: Optional configuration dict for the plugin

        Returns:
            Instance of loaded plugin, or None if loading failed
        """
        if name not in self.registry:
            logger.error(f"Plugin not found: {name}")
            return None

        metadata = self.registry[name]

        if metadata.is_loaded():
            logger.warning(f"Plugin already loaded: {name}")
            return metadata.instance

        try:
            metadata.state = PluginState.LOADING
            logger.debug(f"Loading plugin: {name}")

            # Get plugin config from system config or use provided
            if config is None:
                config = self._config.get(f"plugins.{name}", {})

            metadata.config = config

            # Instantiate plugin
            plugin_instance: BasePlatform = metadata.plugin_class()
            logger.debug(f"Instantiated {name}: {plugin_instance.__class__.__name__}")

            # Initialize plugin
            if not plugin_instance.initialize(config):
                raise RuntimeError(f"Plugin initialization failed: {name}")

            logger.debug(f"Plugin initialized: {name}")

            # Update metadata
            metadata.instance = plugin_instance
            metadata.state = PluginState.ACTIVE
            metadata.loaded_at = datetime.now()
            metadata.error_message = None

            logger.info(f"✓ Plugin loaded successfully: {name}")
            return plugin_instance

        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {str(e)}", exc_info=True)
            metadata.state = PluginState.ERROR
            metadata.error_message = str(e)
            return None

    async def unload_plugin(self, name: str) -> bool:
        """Unload a plugin with proper cleanup.

        Args:
            name: Plugin name to unload

        Returns:
            True if unload successful, False otherwise
        """
        if name not in self.registry:
            logger.warning(f"Plugin not found for unload: {name}")
            return False

        metadata = self.registry[name]

        if not metadata.is_loaded():
            logger.warning(f"Plugin not loaded: {name}")
            return True

        try:
            metadata.state = PluginState.UNLOADING
            logger.debug(f"Unloading plugin: {name}")

            if metadata.instance:
                metadata.instance.shutdown()
                logger.debug(f"Plugin shutdown complete: {name}")

            metadata.instance = None
            metadata.state = PluginState.REGISTERED
            metadata.error_message = None

            logger.info(f"✓ Plugin unloaded successfully: {name}")
            return True

        except Exception as e:
            logger.error(f"Error unloading plugin {name}: {str(e)}", exc_info=True)
            metadata.state = PluginState.ERROR
            metadata.error_message = f"Unload error: {str(e)}"
            return False

    def get_plugin(self, name: str) -> Optional[BasePlatform]:
        """Get a loaded plugin instance.

        Args:
            name: Plugin name

        Returns:
            Plugin instance if loaded, None otherwise
        """
        if name not in self.registry:
            return None

        metadata = self.registry[name]
        return metadata.instance if metadata.is_loaded() else None

    def list_plugins(self) -> List[PluginMetadata]:
        """List all registered plugins and their metadata.

        Returns:
            List of PluginMetadata objects
        """
        return list(self.registry.values())

    async def health_check_all(self) -> Dict[str, PluginHealth]:
        """Run health checks on all loaded plugins.

        Returns:
            Dict mapping plugin names to their health status
        """
        results: Dict[str, PluginHealth] = {}

        logger.debug("Starting health check for all plugins...")

        for metadata in self.list_plugins():
            if not metadata.is_loaded() or not metadata.instance:
                continue

            try:
                logger.debug(f"Health check: {metadata.name}")
                health = await asyncio.to_thread(metadata.instance.health_check)
                results[metadata.name] = health

                # Update metadata
                metadata.health_status = health.status
                metadata.last_health_check = datetime.now()

                if health.is_healthy():
                    logger.debug(
                        f"Health: {metadata.name} -> healthy ({health.response_time_ms:.2f}ms)"
                    )
                else:
                    logger.warning(
                        f"Health: {metadata.name} -> {health.status} ({health.error_message})"
                    )

            except Exception as e:
                logger.error(
                    f"Health check failed for {metadata.name}: {str(e)}", exc_info=True
                )
                results[metadata.name] = PluginHealth(
                    status="unhealthy",
                    response_time_ms=-1,
                    last_check=datetime.now(),
                    error_message=str(e),
                )

        return results

    async def shutdown_all(self) -> None:
        """Shutdown all loaded plugins gracefully."""
        logger.info("Shutting down all plugins...")

        # Unload in reverse order of registration
        for name in list(reversed(list(self.registry.keys()))):
            if self.registry[name].is_loaded():
                await self.unload_plugin(name)

        logger.info("All plugins shut down")
