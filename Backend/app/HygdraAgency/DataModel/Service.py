from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime


# --- use later ---
class AppStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "tested"
    DONE = "done"

class CodeFile(BaseModel):
    id: str
    name: str
    description: str 
    filename: str
    status: str = "todo"
    langage: str

class Service(BaseModel):
    id: str
    name: str
    doc: str
    status: str = "todo"
    description: str 
    code: List[CodeFile] = []

