from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime
from HygdraAgency.DataModel.Task import Task, TaskStatus
from HygdraAgency.DataModel.Service import Service


# --- Models ---
class Project(BaseModel):
    id: str
    name: str
    description: str
    tasks: List[Task] = []
    status: str = "active"
    app : List[Service] = []