# Requirements
from .agent_skills import (
    AgentSkillsPlugin,
    AgentSkillsRequirement,
)
from .jupyter import JupyterPlugin, JupyterRequirement
from .requirement import Plugin, PluginRequirement
from .vscode import VSCodePlugin, VSCodeRequirement

__all__ = [
    'Plugin',
    'PluginRequirement',
    'AgentSkillsRequirement',
    'AgentSkillsPlugin',
    'JupyterRequirement',
    'JupyterPlugin',
    'VSCodeRequirement',
    'VSCodePlugin',
]

ALL_PLUGINS = {
    'jupyter': JupyterPlugin,
    'agent_skills': AgentSkillsPlugin,
    'vscode': VSCodePlugin,
}