"""
Core schema definitions for simplerun events.
Simplified version of OpenHands schema.
"""

from enum import Enum


class ActionType(str, Enum):
    """Types of actions that can be performed."""
    RUN = 'run'
    READ = 'read'
    WRITE = 'write'
    EDIT = 'edit'
    RUN_IPYTHON = 'run_ipython'


class ObservationType(str, Enum):
    """Types of observations that can be returned."""
    RUN = 'run'
    READ = 'read'
    WRITE = 'write'
    EDIT = 'edit'
    RUN_IPYTHON = 'run_ipython'
    ERROR = 'error'
