import asyncio
import os
import subprocess
import sys
import time
from dataclasses import dataclass

from simplerun.core import logger
from simplerun.events.action import Action, IPythonRunCellAction
from simplerun.events.observation import Observation, IPythonRunCellObservation
from .execute_server import JupyterKernel
from ..requirement import Plugin, PluginRequirement


def should_continue() -> bool:
    """Simple helper function to check if execution should continue."""
    return True


@dataclass
class JupyterRequirement(PluginRequirement):
    name: str = 'jupyter'


class JupyterPlugin(Plugin):
    name: str = 'jupyter'
    kernel_gateway_port: int
    kernel_id: str
    gateway_process: asyncio.subprocess.Process | subprocess.Popen
    python_interpreter_path: str

    async def initialize(
        self, username: str, kernel_id: str = 'simplerun-default'
    ) -> None:
        # 使用固定端口，避免防火墙问题
        self.kernel_gateway_port = int(os.environ.get('JUPYTER_PORT', '8001'))
        
        # 验证端口是否在合理范围内
        if not (1024 <= self.kernel_gateway_port <= 65535):
            raise ValueError(f"Invalid JUPYTER_PORT: {self.kernel_gateway_port}. Port must be between 1024 and 65535.")
        
        self.kernel_id = kernel_id
        is_local_runtime = os.environ.get('LOCAL_RUNTIME_MODE') == '1'
        is_windows = sys.platform == 'win32'

        if not is_local_runtime:
            # Non-LocalRuntime: 直接以当前用户运行，在 micromamba env + poetry venv 中启动
            poetry_prefix = (
                'cd /simplerun/code\n'
                'export POETRY_VIRTUALENVS_PATH=/simplerun/poetry;\n'
                'export PYTHONPATH=/simplerun/code:/simplerun/code/simplerun:$PYTHONPATH;\n'
                'export MAMBA_ROOT_PREFIX=/simplerun/micromamba;\n'
                '/simplerun/micromamba/bin/micromamba run -n simplerun poetry run '
            )
        else:
            # LocalRuntime
            prefix = ''
            code_repo_path = os.environ.get('SIMPLERUN_REPO_PATH')
            if not code_repo_path:
                raise ValueError(
                    'SIMPLERUN_REPO_PATH environment variable is not set. '
                    'This is required for the jupyter plugin to work with LocalRuntime.'
                )
            # The correct environment is ensured by the PATH in LocalRuntime.
            poetry_prefix = f'cd {code_repo_path}\n'

        if is_windows:
            # Windows-specific command format
            jupyter_launch_command = (
                f'cd /d "{code_repo_path}" && '
                'jupyter server '
                '--ServerApp.ip=0.0.0.0 '
                f'--ServerApp.port={self.kernel_gateway_port} '
                '--ServerApp.token="" '
                '--ServerApp.password="" '
                '--ServerApp.disable_check_xsrf=True '
                '--ServerApp.allow_origin="*"'
            )
            logger.debug(f'Jupyter launch command (Windows): {jupyter_launch_command}')

            # Using synchronous subprocess.Popen for Windows as asyncio.create_subprocess_shell
            # has limitations on Windows platforms
            self.gateway_process = subprocess.Popen(  # type: ignore[ASYNC101] # noqa: ASYNC101
                jupyter_launch_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                text=True,
            )

            # Windows-specific stdout handling with synchronous time.sleep
            # as asyncio has limitations on Windows for subprocess operations
            output = ''
            while should_continue():
                if self.gateway_process.stdout is None:
                    time.sleep(1)  # type: ignore[ASYNC101] # noqa: ASYNC101
                    continue

                line = self.gateway_process.stdout.readline()
                if not line:
                    time.sleep(1)  # type: ignore[ASYNC101] # noqa: ASYNC101
                    continue

                output += line
                if 'at' in line:
                    break

                time.sleep(1)  # type: ignore[ASYNC101] # noqa: ASYNC101
                logger.debug('Waiting for jupyter kernel gateway to start...')

            logger.debug(
                f'Jupyter kernel gateway started at port {self.kernel_gateway_port}. Output: {output}'
            )
        else:
            # Unix systems (Linux/macOS)
            jupyter_launch_command = (
                "/bin/bash << 'EOF'\n"
                f"{poetry_prefix}"
                'jupyter server '
                '--ServerApp.ip=0.0.0.0 '
                f"--ServerApp.port={self.kernel_gateway_port} "
                '--ServerApp.token="" '
                '--ServerApp.password="" '
                '--ServerApp.disable_check_xsrf=True '
                '--ServerApp.allow_origin="*"\n'
                'EOF'
            )
            logger.debug(f'Jupyter launch command: {jupyter_launch_command}')
            logger.info(f'Jupyter server will start on port {self.kernel_gateway_port}')

            # Using asyncio.create_subprocess_shell instead of subprocess.Popen
            # to avoid ASYNC101 linting error
            self.gateway_process = await asyncio.create_subprocess_shell(
                jupyter_launch_command,
                stderr=asyncio.subprocess.STDOUT,
                stdout=asyncio.subprocess.PIPE,
            )
            # read stdout until the kernel gateway is ready
            output = ''
            while should_continue() and self.gateway_process.stdout is not None:
                line_bytes = await self.gateway_process.stdout.readline()
                line = line_bytes.decode('utf-8')
                output += line
                print(line)
                if 'http' in line or str(self.kernel_gateway_port) in line or 'Gateway' in line:
                    break
                await asyncio.sleep(1)
                logger.debug('Waiting for jupyter kernel gateway to start...')

            logger.debug(
                f'Jupyter kernel gateway started at port {self.kernel_gateway_port}. Output: {output}'
            )

        # 测试Jupyter服务器是否正常工作
        try:
            _obs = await self._run(
                IPythonRunCellAction(code='import sys; print(sys.executable)')
            )
            self.python_interpreter_path = _obs.content.strip()
            logger.info(f"Jupyter plugin initialized successfully. Python path: {self.python_interpreter_path}")
        except Exception as e:
            logger.error(f"Failed to test Jupyter plugin: {e}")
            raise

    async def _run(self, action: Action) -> IPythonRunCellObservation:
        """Internal method to run a code cell in the jupyter kernel."""
        if not isinstance(action, IPythonRunCellAction):
            raise ValueError(
                f'Jupyter plugin only supports IPythonRunCellAction, but got {action}'
            )

        if not hasattr(self, 'kernel'):
            self.kernel = JupyterKernel(
                f'localhost:{self.kernel_gateway_port}', self.kernel_id
            )

        if not self.kernel.initialized:
            await self.kernel.initialize()

        # Execute the code and get structured output
        output = await self.kernel.execute(action.code, timeout=action.timeout)

        # Extract text content and image URLs from the structured output
        text_content = output.get('text', '')
        image_urls = output.get('images', [])

        return IPythonRunCellObservation(
            content=text_content,
            code=action.code,
            image_urls=image_urls if image_urls else None,
        )

    async def run(self, action: Action) -> IPythonRunCellObservation:
        """Execute Python code in Jupyter kernel"""
        try:
            obs = await self._run(action)
            return obs
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            # 返回错误观察结果而不是抛出异常
            return IPythonRunCellObservation(
                content=f"Error executing code: {str(e)}",
                code=action.code if hasattr(action, 'code') else "unknown",
                image_urls=None,
            )
