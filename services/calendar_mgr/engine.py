# File: services/calendar_mgr/engine.py
import json
import pathlib
import os

from core._const import DATA_TODOS, DATA_NOTES, BASE_DIR

class CalendarEngine:
    def __init__(self):

        self.data_dir = BASE_DIR
        self.todo_file = DATA_TODOS
        self.note_file = DATA_NOTES
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.todos_cache = {}
        self.notes_cache = {}
        self.load_data()

    def load_data(self):
        """Load dữ liệu từ ổ cứng lên RAM"""
        self.todos_cache = self._read_json(self.todo_file)
        self.notes_cache = self._read_json(self.note_file)

    def _read_json(self, path):
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_json(self, data, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # --- TODO METHODS ---
    def get_todos(self, date_str):
        return self.todos_cache.get(date_str, [])

    def add_todo(self, date_str, name, price):
        if date_str not in self.todos_cache:
            self.todos_cache[date_str] = []
        
        self.todos_cache[date_str].append({
            "name": name,
            "price": price,
            "done": False
        })
        self._save_json(self.todos_cache, self.todo_file)

    def update_todo_status(self, date_str, index, is_done):
        if date_str in self.todos_cache and 0 <= index < len(self.todos_cache[date_str]):
            self.todos_cache[date_str][index]['done'] = is_done
            self._save_json(self.todos_cache, self.todo_file)

    def delete_todo(self, date_str, index):
        if date_str in self.todos_cache and 0 <= index < len(self.todos_cache[date_str]):
            self.todos_cache[date_str].pop(index)
            # Dọn dẹp key rỗng nếu muốn
            if not self.todos_cache[date_str]:
                del self.todos_cache[date_str]
            self._save_json(self.todos_cache, self.todo_file)

    # --- NOTE METHODS ---
    def get_notes(self, date_str):
        return self.notes_cache.get(date_str, [])

    def add_note(self, date_str, content):
        if date_str not in self.notes_cache:
            self.notes_cache[date_str] = []
        self.notes_cache[date_str].append(content)
        self._save_json(self.notes_cache, self.note_file)

    def delete_note(self, date_str, index):
        if date_str in self.notes_cache and 0 <= index < len(self.notes_cache[date_str]):
            self.notes_cache[date_str].pop(index)
            if not self.notes_cache[date_str]:
                del self.notes_cache[date_str]
            self._save_json(self.notes_cache, self.note_file)