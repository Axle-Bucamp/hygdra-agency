from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime
from dataclasses import dataclass
from Backend.app.DataModel.Task import Task, TaskStatus
from Backend.app.DataModel.Service import Service


# --- Models ---
@dataclass
class Project(BaseModel):
    id: str
    name: str
    description: str
    tasks: List[Task] = []
    status: str = "active"
    app : List[Service] = []