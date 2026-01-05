import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Fund:
    # 1. Các trường bắt buộc (Không có giá trị mặc định) - PHẢI ĐỂ ĐẦU TIÊN
    name: str
    target: float
    
    # 2. Các trường có giá trị mặc định - ĐỂ PHÍA SAU
    # --- FIX LỖI Ở ĐÂY: Thêm trường type ---
    type: str = "goal"  # Mặc định là 'goal' nếu dữ liệu cũ không có
    
    current: float = 0.0
    
    # Tự động sinh UUID
    id: str = field(default_factory=lambda: str(uuid.uuid4())) 
    
    icon: str = "💰"
    color: str = "#ffffff"
    
    # History lưu list dict
    history: List[Dict] = field(default_factory=list)

    # Hàm xử lý flexible arguments để tránh lỗi nếu JSON có trường lạ
    @classmethod
    def from_dict(cls, data: dict):
        # Lọc chỉ lấy những key có trong dataclass để tránh lỗi "unexpected keyword"
        valid_keys = cls.__annotations__.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)

    def to_dict(self):
        return self.__dict__

@dataclass
class Goal:
    name: str
    target: float
    
    # Sửa id thành str/uuid cho đồng bộ
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    members: List[Dict] = field(default_factory=list)
    deadline: str = ""
    status: str = "active"

    def to_dict(self):
        return self.__dict__