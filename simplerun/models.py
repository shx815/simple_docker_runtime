from pydantic import BaseModel
from typing import Optional, Dict, Any

class ServerInfo(BaseModel):
    status: str
    version: str
    cwd: str
    username: Optional[str] = None
    resources: Optional[Dict[str, Any]] = None