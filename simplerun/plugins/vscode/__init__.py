import asyncio
import os
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from simplerun.core import logger
from simplerun.events.action import Action
from simplerun.events.observation import Observation
from ..requirement import Plugin, PluginRequirement
from simplerun.utils.system import check_port_available

def should_continue() -> bool:
    """Simple helper function to check if execution should continue."""
    return True


@dataclass
class VSCodeRequirement(PluginRequirement):
    name: str = 'vscode'


class VSCodePlugin(Plugin):
    name: str = 'vscode'
    vscode_port: Optional[int] = None
    vscode_connection_token: Optional[str] = None
    gateway_process: asyncio.subprocess.Process

    async def initialize(self, username: str) -> None:
        # Windows 容器内不支持 VSCode 插件
        if os.name == 'nt' or sys.platform == 'win32':
            self.vscode_port = None
            self.vscode_connection_token = None
            logger.warning('VSCode plugin is not supported on Windows. Plugin will be disabled.')
            return

        # Set up VSCode settings.json
        self._setup_vscode_settings()

        # 端口：使用环境变量或默认值
        try:
            self.vscode_port = int(os.environ.get('VSCODE_PORT', '3000'))
        except ValueError:
            logger.warning('VSCODE_PORT environment variable invalid. VSCode plugin will be disabled.')
            return

        self.vscode_connection_token = str(uuid.uuid4())
        
        # 添加调试信息：记录端口检查过程
        logger.debug(f'Checking if port {self.vscode_port} is available...')
        port_available = check_port_available(self.vscode_port)
        logger.debug(f'Port {self.vscode_port} available: {port_available}')
        
        if not port_available:
            logger.warning(
                f'Port {self.vscode_port} is not available. VSCode plugin will be disabled.'
            )
            return
        # 工作目录：使用 WORKSPACE_BASE 或 WORK_DIR，默认 /simplerun/workspace
        workspace_base = os.getenv('WORKSPACE_BASE') or os.getenv('WORK_DIR') or '/simplerun/workspace'

        # 直接以当前用户启动，不再强制 su/sudo，兼容 appuser
        cmd = (
            f"cd {workspace_base} && "
            f"exec /simplerun/.openvscode-server/bin/openvscode-server "
            f"--host 0.0.0.0 --connection-token {self.vscode_connection_token} "
            f"--port {self.vscode_port} --disable-workspace-trust"
        )

        # Using asyncio.create_subprocess_shell instead of subprocess.Popen
        # to avoid ASYNC101 linting error
        self.gateway_process = await asyncio.create_subprocess_shell(
            cmd,
            stderr=asyncio.subprocess.STDOUT,
            stdout=asyncio.subprocess.PIPE,
        )
        # read stdout until the kernel gateway is ready
        output = ''
        while should_continue() and self.gateway_process.stdout is not None:
            line_bytes = await self.gateway_process.stdout.readline()
            line = line_bytes.decode('utf-8')
            print(line)
            output += line
            if 'at' in line:
                break
            await asyncio.sleep(1)
            logger.debug('Waiting for VSCode server to start...')

        logger.info(f'VSCode server will start on port {self.vscode_port}')
        logger.debug(
            f'VSCode server started at port {self.vscode_port}. Output: {output}'
        )

    def _setup_vscode_settings(self) -> None:
        """
        Set up VSCode settings by creating the .vscode directory in the workspace
        and copying the settings.json file there.
        """
        # Get the path to the settings.json file in the plugin directory
        current_dir = Path(__file__).parent
        settings_path = current_dir / 'settings.json'

        # Create the .vscode directory in the workspace if it doesn't exist
        workspace_dir = Path(os.getenv('WORKSPACE_BASE', '/workspace'))
        vscode_dir = workspace_dir / '.vscode'
        
        # 检查是否已经存在 .vscode 目录和 settings.json
        target_path = vscode_dir / 'settings.json'
        
        # 如果 .vscode 目录不存在，或者 settings.json 不存在，才创建
        if not vscode_dir.exists() or not target_path.exists():
            vscode_dir.mkdir(parents=True, exist_ok=True)
            # Copy the settings.json file to the .vscode directory
            shutil.copy(settings_path, target_path)
            # Make sure the settings file is readable and writable by all users
            os.chmod(target_path, 0o666)
            logger.debug(f'VSCode settings copied to {target_path}')
        else:
            logger.debug(f'VSCode settings already exist at {target_path}, skipping creation')

    async def run(self, action: Action) -> Observation:
        """Run the plugin for a given action."""
        raise NotImplementedError('VSCodePlugin does not support run method')
