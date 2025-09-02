"""
Example Plugin for Human-AI Co-Creation System
Demonstrates plugin interface and safe patching
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("example_plugin")


def apply() -> Dict[str, Any]:
    """
    Example plugin entry point
    This function is called when the plugin is enabled
    """
    try:
        logger.info("Example plugin: Applying patch...")

        # Example patch: Add a custom greeting function to the system
        # In a real plugin, this might modify agent prompts, add new endpoints, etc.

        # Simulate some plugin work
        patch_result = {
            "greeting_function_added": True,
            "custom_endpoints": ["/api/example/hello"],
            "modified_components": ["session_manager"],
            "patch_version": "0.1.0",
        }

        logger.info("Example plugin: Patch applied successfully")

        return {
            "success": True,
            "message": "Example plugin enabled successfully",
            "changes": patch_result,
            "rollback_info": {
                "can_rollback": True,
                "rollback_method": "remove_greeting_function",
            },
        }

    except Exception as e:
        logger.error(f"Example plugin failed: {e}")
        return {"success": False, "error": str(e)}


def rollback() -> Dict[str, Any]:
    """
    Rollback function for the example plugin
    Called when plugin is disabled or needs to be reverted
    """
    try:
        logger.info("Example plugin: Rolling back changes...")

        # Remove the greeting function and endpoints
        rollback_result = {
            "greeting_function_removed": True,
            "custom_endpoints_removed": ["/api/example/hello"],
            "restored_components": ["session_manager"],
        }

        logger.info("Example plugin: Rollback completed successfully")

        return {
            "success": True,
            "message": "Example plugin rollback completed",
            "changes": rollback_result,
        }

    except Exception as e:
        logger.error(f"Example plugin rollback failed: {e}")
        return {"success": False, "error": str(e)}


# Plugin metadata (not used by patch manager, but good for documentation)
PLUGIN_INFO = {
    "id": "example_plugin",
    "name": "Example Plugin",
    "version": "0.1.0",
    "description": "Demonstrates plugin system capabilities",
    "author": "Human-AI Co-Creation System",
    "compatibility": {"schema_version": "1.0", "min_server": "0.1.0"},
    "capabilities": ["custom_endpoints", "prompt_modification", "safe_rollback"],
}
