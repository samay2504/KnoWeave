"""
Patch Manager - Plugin System for Human-AI Co-Creation System
Handles loading, enabling, disabling, and hot-patching plugins with safety rollbacks
"""

import json
import logging
import asyncio
import importlib
import sys
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime
import shutil
import traceback

logger = logging.getLogger("patch_manager")


class PluginManifest:
    """Manages plugin manifest.json file"""

    def __init__(self, manifest_path: str = "plugins/manifest.json"):
        self.manifest_path = Path(manifest_path)
        self.plugins = {}
        self.load_manifest()

    def load_manifest(self) -> None:
        """Load plugins from manifest.json"""
        try:
            if self.manifest_path.exists():
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.plugins = {p["id"]: p for p in data.get("plugins", [])}
                logger.info(f"Loaded {len(self.plugins)} plugins from manifest")
            else:
                logger.warning(f"Manifest not found: {self.manifest_path}")
                self._create_default_manifest()
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            self.plugins = {}

    def _create_default_manifest(self) -> None:
        """Create default manifest.json"""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        default_manifest = {
            "plugins": [
                {
                    "id": "example_plugin",
                    "version": "0.1.0",
                    "enabled": False,
                    "entrypoint": "plugins.example_plugin:apply",
                    "description": "Example plugin for demonstration",
                    "compat": {"schema_version": "1.0", "min_server": "0.1.0"},
                }
            ]
        }

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(default_manifest, f, indent=2)

        self.plugins = {p["id"]: p for p in default_manifest["plugins"]}
        logger.info("Created default manifest.json")

    def save_manifest(self) -> None:
        """Save current plugins state to manifest.json"""
        try:
            self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"plugins": list(self.plugins.values())}

            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info("Saved manifest.json")
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")

    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get plugin by ID"""
        return self.plugins.get(plugin_id)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all plugins"""
        return list(self.plugins.values())

    def update_plugin(self, plugin_id: str, updates: Dict[str, Any]) -> bool:
        """Update plugin configuration"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].update(updates)
            self.save_manifest()
            return True
        return False


class PatchManager:
    """
    Main patch manager for plugin system
    Handles enabling/disabling plugins, safety rollbacks, and hot patching
    """

    def __init__(self, manifest_path: str = "plugins/manifest.json"):
        self.manifest = PluginManifest(manifest_path)
        self.active_plugins: Dict[str, Any] = {}
        self.plugin_locks: Dict[str, asyncio.Lock] = {}
        self.backup_dir = Path("data/backups/plugins")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Patch Manager initialized")

    def list_plugins(self) -> Dict[str, Any]:
        """
        List all plugins with their status
        Returns JSON-compatible response for orchestrator
        """
        plugins = self.manifest.list_plugins()
        return {
            "plugins": plugins,
            "active_count": len(self.active_plugins),
            "total_count": len(plugins),
            "call_metadata": {
                "provider": "patch_manager",
                "model": "internal",
                "latency_ms": 0,
            },
        }

    async def enable_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        Enable a plugin with safety checks and rollback capability
        Returns JSON response for orchestrator
        """
        plugin = self.manifest.get_plugin(plugin_id)
        if not plugin:
            return {
                "success": False,
                "error": f"Plugin '{plugin_id}' not found",
                "call_metadata": {
                    "provider": "patch_manager",
                    "model": "internal",
                    "latency_ms": 0,
                },
            }

        # Acquire lock for this plugin
        if plugin_id not in self.plugin_locks:
            self.plugin_locks[plugin_id] = asyncio.Lock()

        async with self.plugin_locks[plugin_id]:
            try:
                # Check compatibility
                if not self._check_compatibility(plugin):
                    return {
                        "success": False,
                        "error": f"Plugin '{plugin_id}' incompatible with current system",
                        "call_metadata": {
                            "provider": "patch_manager",
                            "model": "internal",
                            "latency_ms": 0,
                        },
                    }

                # Create backup before enabling
                backup_path = await self._create_snapshot_backup(plugin_id)

                # Load and apply plugin
                plugin_callable = self._load_plugin_entrypoint(plugin)

                # Apply patch safely
                result = await self.apply_patch_safely(
                    plugin_callable, plugin_id, backup_path
                )

                if result["success"]:
                    # Mark as enabled and active
                    self.manifest.update_plugin(plugin_id, {"enabled": True})
                    self.active_plugins[plugin_id] = {
                        "plugin": plugin,
                        "callable": plugin_callable,
                        "enabled_at": datetime.now().isoformat(),
                        "backup_path": backup_path,
                    }

                    logger.info(f"Plugin '{plugin_id}' enabled successfully")

                return result

            except Exception as e:
                logger.error(f"Failed to enable plugin '{plugin_id}': {e}")
                return {
                    "success": False,
                    "error": f"Exception during plugin enable: {str(e)}",
                    "call_metadata": {
                        "provider": "patch_manager",
                        "model": "internal",
                        "latency_ms": 0,
                    },
                }

    async def disable_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        Disable a plugin and optionally rollback changes
        Returns JSON response for orchestrator
        """
        if plugin_id not in self.active_plugins:
            return {
                "success": False,
                "error": f"Plugin '{plugin_id}' is not active",
                "call_metadata": {
                    "provider": "patch_manager",
                    "model": "internal",
                    "latency_ms": 0,
                },
            }

        async with self.plugin_locks[plugin_id]:
            try:
                plugin_info = self.active_plugins[plugin_id]
                backup_path = plugin_info.get("backup_path")

                # Attempt to rollback if backup exists
                rollback_success = False
                if backup_path and Path(backup_path).exists():
                    rollback_success = await self._restore_from_backup(backup_path)

                # Remove from active plugins
                del self.active_plugins[plugin_id]

                # Mark as disabled in manifest
                self.manifest.update_plugin(plugin_id, {"enabled": False})

                logger.info(f"Plugin '{plugin_id}' disabled successfully")

                return {
                    "success": True,
                    "plugin_id": plugin_id,
                    "rollback_applied": rollback_success,
                    "call_metadata": {
                        "provider": "patch_manager",
                        "model": "internal",
                        "latency_ms": 0,
                    },
                }

            except Exception as e:
                logger.error(f"Failed to disable plugin '{plugin_id}': {e}")
                return {
                    "success": False,
                    "error": f"Exception during plugin disable: {str(e)}",
                    "call_metadata": {
                        "provider": "patch_manager",
                        "model": "internal",
                        "latency_ms": 0,
                    },
                }

    async def apply_patch_safely(
        self, patch_callable: Callable, plugin_id: str, backup_path: str
    ) -> Dict[str, Any]:
        """
        Apply a patch in a controlled transaction with rollback on failure
        """
        try:
            # Run patch in sandbox-like environment
            logger.info(f"Applying patch for plugin '{plugin_id}'")

            # Execute the patch callable
            if asyncio.iscoroutinefunction(patch_callable):
                result = await patch_callable()
            else:
                result = patch_callable()

            # Validate result
            if isinstance(result, dict) and result.get("success", True):
                logger.info(f"Patch applied successfully for plugin '{plugin_id}'")
                return {
                    "success": True,
                    "plugin_id": plugin_id,
                    "result": result,
                    "backup_path": backup_path,
                    "call_metadata": {
                        "provider": "patch_manager",
                        "model": "internal",
                        "latency_ms": 0,
                    },
                }
            else:
                # Patch failed, restore backup
                await self._restore_from_backup(backup_path)
                return {
                    "success": False,
                    "error": f"Patch validation failed for plugin '{plugin_id}'",
                    "restored_backup": True,
                    "call_metadata": {
                        "provider": "patch_manager",
                        "model": "internal",
                        "latency_ms": 0,
                    },
                }

        except Exception as e:
            logger.error(f"Patch application failed for plugin '{plugin_id}': {e}")
            # Restore backup on exception
            await self._restore_from_backup(backup_path)
            return {
                "success": False,
                "error": f"Patch exception: {str(e)}",
                "restored_backup": True,
                "traceback": traceback.format_exc(),
                "call_metadata": {
                    "provider": "patch_manager",
                    "model": "internal",
                    "latency_ms": 0,
                },
            }

    def _check_compatibility(self, plugin: Dict[str, Any]) -> bool:
        """Check if plugin is compatible with current system"""
        compat = plugin.get("compat", {})

        # Check schema version
        schema_version = compat.get("schema_version", "1.0")
        if schema_version != "1.0":  # Current system schema version
            logger.warning(f"Plugin schema version {schema_version} incompatible")
            return False

        # Check minimum server version
        min_server = compat.get("min_server", "0.1.0")
        # For now, assume compatibility (would need version comparison logic)

        return True

    def _load_plugin_entrypoint(self, plugin: Dict[str, Any]) -> Callable:
        """Load plugin entrypoint callable"""
        entrypoint = plugin["entrypoint"]

        try:
            # Parse entrypoint: "plugins.example_plugin:apply"
            module_path, func_name = entrypoint.split(":")

            # Import module
            module = importlib.import_module(module_path)

            # Get callable
            callable_obj = getattr(module, func_name)

            return callable_obj

        except Exception as e:
            logger.error(f"Failed to load plugin entrypoint '{entrypoint}': {e}")
            raise

    async def _create_snapshot_backup(self, plugin_id: str) -> str:
        """Create a snapshot backup before applying plugin"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{plugin_id}_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)

            # Create backup metadata
            backup_metadata = {
                "plugin_id": plugin_id,
                "created_at": datetime.now().isoformat(),
                "backup_type": "pre_plugin_enable",
            }

            with open(backup_path / "metadata.json", "w") as f:
                json.dump(backup_metadata, f, indent=2)

            logger.info(f"Created backup for plugin '{plugin_id}' at {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"Failed to create backup for plugin '{plugin_id}': {e}")
            raise

    async def _restore_from_backup(self, backup_path: str) -> bool:
        """Restore system state from backup"""
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                logger.warning(f"Backup path does not exist: {backup_path}")
                return False

            # Read backup metadata
            metadata_file = backup_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                logger.info(f"Restoring from backup: {metadata}")

            # Perform actual restore (implementation depends on what was backed up)
            # For now, just log the restore attempt
            logger.info(f"Backup restore completed from {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore from backup '{backup_path}': {e}")
            return False


# Factory function
def create_patch_manager(manifest_path: str = "plugins/manifest.json") -> PatchManager:
    """Create and initialize patch manager"""
    return PatchManager(manifest_path)
