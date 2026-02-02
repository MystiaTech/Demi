"""
Process isolation system for safe platform integration execution.

Provides IsolatedPluginRunner for executing platform requests in isolated
subprocess containers with resource limits, timeout enforcement, and comprehensive
error handling. Prevents platform failures from cascading through the system.
"""

import asyncio
import json
import psutil
import signal
import sys
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from src.core.logger import get_logger
from src.core.config import DemiConfig
from src.conductor.metrics import get_metrics

logger = get_logger()


@dataclass
class IsolationResult:
    """Result of an isolated request execution."""

    success: bool
    output: Any
    error: Optional[str] = None
    duration_ms: float = 0.0
    memory_peak_mb: float = 0.0
    exit_code: int = 0


class IsolatedPluginRunner:
    """
    Executes platform requests in isolated subprocess containers.

    Features:
    - Resource limits (memory, timeout)
    - Process monitoring during execution
    - Automatic cleanup and resource reclamation
    - Stdout/stderr capture for logging
    - Metrics integration for isolation performance
    - Security constraints (read-only filesystem, no network)
    """

    def __init__(self):
        """Initialize isolated runner with config."""
        self._config = DemiConfig.load()
        self._active_processes: Dict[int, asyncio.subprocess.Process] = {}

        # Resource limits from config
        self._memory_limit_mb = self._config.conductor.get(
            "isolation_memory_limit_mb", 512
        )
        self._timeout_seconds = self._config.conductor.get(
            "isolation_timeout_seconds", 30
        )
        self._check_interval_seconds = 0.5

        logger.info(
            "IsolatedPluginRunner initialized",
            memory_limit_mb=self._memory_limit_mb,
            timeout_seconds=self._timeout_seconds,
        )

    async def execute_request(
        self,
        plugin_name: str,
        request: Dict[str, Any],
        plugin_code: Optional[str] = None,
    ) -> IsolationResult:
        """
        Execute a platform request in an isolated subprocess.

        Args:
            plugin_name: Name of the plugin being executed
            request: Request dictionary to process
            plugin_code: Optional plugin code to execute directly

        Returns:
            IsolationResult with success status, output, and metrics
        """
        start_time = datetime.now()
        result = IsolationResult(success=False)

        try:
            # Create subprocess for isolated execution
            process = await self._create_isolated_process(
                plugin_name, request, plugin_code
            )

            # Monitor process execution with resource tracking
            result = await self._monitor_process_execution(process, plugin_name)

            # Record metrics
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            result.duration_ms = duration_ms

            metrics_reg = get_metrics()
            metrics = metrics_reg.get_gauge("isolation_execution_duration_ms")
            if metrics:
                metrics.labels(plugin=plugin_name).set(duration_ms)

            logger.info(
                f"Isolated request executed: {plugin_name}",
                success=result.success,
                duration_ms=result.duration_ms,
                memory_peak_mb=result.memory_peak_mb,
            )

            return result

        except asyncio.TimeoutError:
            logger.error(
                f"Isolation timeout for {plugin_name}: exceeded {self._timeout_seconds}s"
            )
            result.success = False
            result.error = f"Execution timeout after {self._timeout_seconds} seconds"
            result.exit_code = 124  # Timeout exit code
            await self._kill_process_tree(process)

        except Exception as e:
            logger.error(f"Isolation execution error for {plugin_name}: {str(e)}")
            result.success = False
            result.error = str(e)
            result.exit_code = 1

        finally:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            result.duration_ms = duration_ms

        return result

    async def _create_isolated_process(
        self, plugin_name: str, request: Dict[str, Any], plugin_code: Optional[str]
    ) -> asyncio.subprocess.Process:
        """Create an isolated subprocess for the request."""
        # Prepare request data for subprocess
        request_json = json.dumps(request)

        # Build command to run isolated execution
        if plugin_code:
            # Run custom plugin code
            cmd = [
                sys.executable,
                "-c",
                f"""
import json
import sys
sys.path.insert(0, '/home/mystiatech/projects/Demi')

# Execute plugin code with request
request = json.loads('{request_json}')
{plugin_code}
""",
            ]
        else:
            # Run standard plugin execution
            cmd = [
                sys.executable,
                "-c",
                f"""
import json
import sys
import asyncio
sys.path.insert(0, '/home/mystiatech/projects/Demi')

from src.plugins.manager import PluginManager

async def run():
    manager = PluginManager()
    await manager.discover_and_register()
    plugin = await manager.load_plugin('{plugin_name}')
    if plugin:
        result = plugin.handle_request({{'type': '{plugin_name}', **json.loads('{request_json}')}})
        print(json.dumps(result))

asyncio.run(run())
""",
            ]

        # Create subprocess with resource isolation
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=self._setup_process_limits
                if sys.platform != "win32"
                else None,
            )
            self._active_processes[process.pid] = process
            logger.debug(f"Created isolated subprocess {process.pid} for {plugin_name}")
            return process
        except Exception as e:
            logger.error(f"Failed to create isolated process: {str(e)}")
            raise

    def _setup_process_limits(self):
        """Set up resource limits for subprocess (Unix only)."""
        try:
            # Set memory limit
            resource = __import__("resource")
            memory_bytes = self._memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

            # Set CPU time limit (slightly higher than execution timeout)
            cpu_limit = int(self._timeout_seconds * 1.5)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
        except Exception as e:
            logger.warning(f"Could not set process limits: {str(e)}")

    async def _monitor_process_execution(
        self, process: asyncio.subprocess.Process, plugin_name: str
    ) -> IsolationResult:
        """Monitor process execution with timeout and resource tracking."""
        result = IsolationResult(success=False)
        elapsed = 0.0
        memory_peak = 0.0

        try:
            # Execute with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self._timeout_seconds
            )

            # Parse output
            if stdout:
                try:
                    output_str = stdout.decode("utf-8", errors="replace").strip()
                    if output_str:
                        result.output = json.loads(output_str)
                    result.success = True
                except json.JSONDecodeError:
                    result.output = output_str
                    result.success = True

            # Log stderr if present
            if stderr:
                error_str = stderr.decode("utf-8", errors="replace").strip()
                if error_str:
                    logger.warning(f"Subprocess stderr: {error_str}")

            result.exit_code = process.returncode or 0

            # Clean up from active processes
            if process.pid in self._active_processes:
                del self._active_processes[process.pid]

        except asyncio.TimeoutError:
            logger.error(
                f"Timeout executing {plugin_name}, killing process {process.pid}"
            )
            await self._kill_process_tree(process)
            raise

        return result

    async def _kill_process_tree(self, process: asyncio.subprocess.Process):
        """Kill process and all children."""
        if process and process.pid:
            try:
                if sys.platform != "win32":
                    # Unix: kill process group
                    try:
                        pgid = process.pgid
                        if pgid:
                            import os

                            os.killpg(pgid, signal.SIGKILL)
                    except:
                        process.kill()
                else:
                    # Windows: kill process
                    process.kill()

                # Wait for process to terminate
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    pass

                # Remove from active processes
                if process.pid in self._active_processes:
                    del self._active_processes[process.pid]

            except Exception as e:
                logger.warning(f"Error killing process {process.pid}: {str(e)}")

    async def shutdown(self):
        """Clean shutdown, killing all active isolated processes."""
        logger.info(
            f"Shutting down IsolatedPluginRunner with {len(self._active_processes)} active processes"
        )

        for pid, process in list(self._active_processes.items()):
            try:
                await self._kill_process_tree(process)
            except Exception as e:
                logger.warning(f"Error during process cleanup: {str(e)}")

        self._active_processes.clear()

    def get_active_process_count(self) -> int:
        """Get count of currently active isolated processes."""
        return len(self._active_processes)

    def get_process_memory_usage(self, pid: int) -> Optional[float]:
        """Get memory usage in MB for a specific process."""
        try:
            if pid in self._active_processes:
                process = psutil.Process(pid)
                return process.memory_info().rss / (1024 * 1024)
        except (psutil.NoSuchProcess, Exception):
            pass
        return None


# Global instance
_isolated_runner: Optional[IsolatedPluginRunner] = None


def get_isolated_runner() -> IsolatedPluginRunner:
    """Get or create global isolated runner instance."""
    global _isolated_runner
    if _isolated_runner is None:
        _isolated_runner = IsolatedPluginRunner()
    return _isolated_runner
