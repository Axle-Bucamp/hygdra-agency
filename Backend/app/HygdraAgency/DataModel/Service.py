from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime


class Service(BaseModel):
    id: str
    name: str
    doc: str
    status: str = "todo"
    type: str
