#!/usr/bin/env python3
"""
BotChatAgentAPI – phiên bản thay thế chính xác từ script gốc đang chạy được
"""

import json
import uuid
import requests
from typing import Iterable

# ---------- CẤU HÌNH GIỐNG HỆT SCRIPT GỐC ----------
CHAT_ID   = "a8b2e64a-2dc8-4b2d-b290-49debc5fd2df"
PARENT_ID = "5dc0fc73-f467-4885-9e82-02528a9470b9"
TOKEN     = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQyMjI4MGU2LTRkNzctNDI2NC05ZmI4LTg1NWYzYTJi"
             "MmJmMyIsImxhc3RfcGFzc3dvcmRfY2hhbmdlIjoxNzUwNjYwODczLCJleHAiOjE3NjgxOTY0Mjd9."
             "CpsK965pZNKQ9jXvGMuSVL9AZAh6YkPecHr9uKu7-Sk")

# ✅ Sửa: BỎ KHOẢNG TRẮNG THỪA TRONG URL
URL = f"https://chat.qwen.ai/api/v2/chat/completions?chat_id={CHAT_ID}"
# ------------------------------------------------------------

class BotChatAgentAPI:
    def __init__(self):
        self.session = requests.Session()
        # --- Headers y hệt script gốc (đã sửa khoảng trắng) ---
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/json",
            # ✅ Sửa: bỏ khoảng trắng ở Origin & Referer
            "Origin": "https://chat.qwen.ai",
            "Referer": f"https://chat.qwen.ai/c/{CHAT_ID}",
            "Sec-Ch-Ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Version": "0.1.31",
            "X-Accel-Buffering": "no",
        })
        # --- Cookie y hệt script gốc ---
        self.session.headers["Cookie"] = f"token={TOKEN}; x-ap=ap-southeast-1; xlly_s=1"

    def _build_payload(self, message: str) -> dict:
        """Tạo payload giống hệt script gốc"""
        return {
            "stream": True,
            "version": "2.1",
            "incremental_output": True,
            "chat_id": CHAT_ID,
            "chat_mode": "normal",
            "model": "qwen3-max-2025-10-30",
            "parent_id": PARENT_ID,
            "messages": [{
                "fid": str(uuid.uuid4()),
                "parentId": PARENT_ID,
                "childrenIds": [],
                "role": "user",
                "content": message,
                "user_action": "chat",
                "files": [],
                "timestamp": int(uuid.uuid1().time // 10**7),
                "models": ["qwen3-max-2025-10-30"],
                "chat_type": "t2t",
                "feature_config": {
                    "thinking_enabled": False,
                    "output_schema": "phase",
                    "research_mode": "normal",
                },
                "extra": {"meta": {"subChatType": "t2t"}},
                "sub_chat_type": "t2t",
            }],
            "timestamp": int(uuid.uuid1().time // 10**7),
        }

    def stream_tokens(self, prompt: str) -> Iterable[str]:
        # ✅ Mỗi request nên có X-Request-Id mới (như script gốc sinh 1 lần, nhưng tốt hơn nên sinh lại)
        self.session.headers["X-Request-Id"] = str(uuid.uuid4())

        payload = self._build_payload(prompt)
        resp = self.session.post(URL, json=payload, stream=True)
        resp.raise_for_status()

        for raw in resp.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data:"):
                continue
            try:
                chunk = json.loads(raw[5:].strip())
                if chunk.get("choices"):
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
            except Exception:
                continue

# ---------------- DEMO ----------------
if __name__ == "__main__":
    agent = BotChatAgentAPI()
    try:
        while True:
            prompt = input("\nBạn: ").strip()
            if not prompt:
                break
            print("Qwen: ", end="", flush=True)
            for token in agent.stream_tokens(prompt):
                print(token, end="", flush=True)
            print()
    except KeyboardInterrupt:
        print("\nBye!")