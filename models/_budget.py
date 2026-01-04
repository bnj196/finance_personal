from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Fund: # Quỹ cá nhân
    id: int
    name: str
    type: str # 'goal', 'monthly', 'pool'
    target: float
    current: float
    icon: str
    history: List[Dict] = field(default_factory=list)

    def to_dict(self):
        return self.__dict__

@dataclass
class Goal: # Quỹ nhóm
    id: int
    name: str
    target: float
    members: List[Dict] = field(default_factory=list) # [{"name": "A", "contribution": 100...}]

    def to_dict(self):
        return self.__dict__