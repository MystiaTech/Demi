"""Plugin discovery system using Python entry points."""

import importlib.metadata
from typing import Dict, Type
from src.core.logger import get_logger
from src.platforms.base import BasePlatform


logger = get_logger()


def validate_plugin_class(plugin_class: Type) -> bool:
    """Validate that a plugin class properly inherits from BasePlatform.

    Args:
        plugin_class: Class to validate

    Returns:
        True if class is valid BasePlatform subclass
    """
    try:
        return issubclass(plugin_class, BasePlatform)
    except TypeError:
        return False


def discover_plugins() -> Dict[str, Type[BasePlatform]]:
    """Discover available platform plugins via entry points.

    Scans for 'demi.platforms' entry points and loads valid plugins.
    Handles discovery errors gracefully.

    Returns:
        Dictionary mapping plugin names to their classes
    """
    plugins: Dict[str, Type[BasePlatform]] = {}

    try:
        # Get all entry points for demi.platforms group
        entry_points = importlib.metadata.entry_points()

        # Handle both old (dict-based) and new (SelectableGroups) API
        if hasattr(entry_points, "select"):
            # Python 3.10+ API
            demi_eps = entry_points.select(group="demi.platforms")
        elif isinstance(entry_points, dict):
            # Python 3.9 API
            demi_eps = entry_points.get("demi.platforms", [])
        else:
            # Fallback
            demi_eps = []

        logger.debug(f"Discovered {len(demi_eps)} entry point(s) in demi.platforms")

        for ep in demi_eps:
            try:
                plugin_name = ep.name
                logger.debug(f"Loading plugin: {plugin_name} from {ep.value}")

                # Load the plugin class
                plugin_class = ep.load()

                # Validate plugin
                if not validate_plugin_class(plugin_class):
                    logger.warning(
                        f"Plugin {plugin_name} does not inherit from BasePlatform, skipping"
                    )
                    continue

                plugins[plugin_name] = plugin_class
                logger.info(f"✓ Loaded plugin: {plugin_name}")

            except Exception as e:
                logger.error(
                    f"Failed to load plugin {ep.name}: {str(e)}", exc_info=True
                )
                continue

        logger.info(f"Discovery complete: {len(plugins)} valid plugins loaded")

    except Exception as e:
        logger.error(f"Plugin discovery failed: {str(e)}", exc_info=True)
        # Return empty dict on discovery failure - non-fatal
        return {}

    return plugins
