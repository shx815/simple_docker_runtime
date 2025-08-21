"""
Event serialization utilities for simplerun.
Simplified version of OpenHands event serialization.
"""

import json
from typing import Any, Dict

from simplerun.events.action import (
    Action,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    IPythonRunCellAction,
)
from simplerun.events.observation import (
    CmdOutputObservation,
    ErrorObservation,
    FileEditObservation,
    FileReadObservation,
    FileWriteObservation,
    IPythonRunCellObservation,
    Observation,
)
from simplerun.events.event import Event


# Map action types to classes
ACTION_TYPE_TO_CLASS = {
    'run': CmdRunAction,
    'read': FileReadAction,
    'write': FileWriteAction,
    'edit': FileEditAction,
    'run_ipython': IPythonRunCellAction,
}

# Map observation types to classes
OBSERVATION_TYPE_TO_CLASS = {
    'run': CmdOutputObservation,
    'read': FileReadObservation,
    'write': FileWriteObservation,
    'edit': FileEditObservation,
    'run_ipython': IPythonRunCellObservation,
    'error': ErrorObservation,
}


def event_to_dict(event: Event) -> Dict[str, Any]:
    """Convert an event to a dictionary following OpenHands format."""
    if hasattr(event, '__dict__'):
        props = {}
        for key, value in event.__dict__.items():
            if not key.startswith('_'):
                props[key] = value
        
        # 按照 OpenHands 格式组织输出
        if 'action' in props:
            # Action 格式：{"action": "run", "args": {...}}
            action_type = props.pop('action')
            result = {'action': action_type}
            if props:
                result['args'] = props
            return result
        elif 'observation' in props:
            # Observation 格式：{"observation": "run", "content": "...", "extras": {...}}
            obs_type = props.pop('observation')
            result = {'observation': obs_type}
            if 'content' in props:
                result['content'] = props.pop('content')
            if props:
                result['extras'] = props
            return result
        
        # 如果没有核心字段，返回所有字段
        return props
    
    return {}


def event_from_dict(data: Dict[str, Any]) -> Event:
    """Create an event from a dictionary."""
    # 只支持 OpenHands 标准格式：
    # {"action": "run", "args": {"command": "..."}}
    
    if 'action' in data:
        action_type = data.get('action')
        if action_type in ACTION_TYPE_TO_CLASS:
            cls = ACTION_TYPE_TO_CLASS[action_type]
            
            # OpenHands 标准格式：参数在 args 字段中
            args = data.get('args', {})
            # 不传递 action 参数，依赖类的默认值（与 OpenHands 一致）
            return cls(**args)
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    elif 'observation' in data:
        # This is an observation
        obs_type = data.get('observation')
        if obs_type in OBSERVATION_TYPE_TO_CLASS:
            cls = OBSERVATION_TYPE_TO_CLASS[obs_type]
            obs_data = data.copy()
            obs_data.pop('observation', None)
            return cls(observation=obs_type, **obs_data)
        else:
            raise ValueError(f"Unknown observation type: {obs_type}")
    
    else:
        raise ValueError("Data must contain either 'action' or 'observation' field")