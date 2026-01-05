#!/usr/bin/env python3
"""
qwen_chat_api.py
Gọi https://chat.qwen.ai/api/v2/chat/completions
với payload & headers đúng như browser đã thực hiện.
"""

import json
import uuid
import requests

# ---------- CONFIG ----------
CHAT_ID   = "a8b2e64a-2dc8-4b2d-b290-49debc5fd2df"
PARENT_ID = "5dc0fc73-f467-4885-9e82-02528a9470b9"
TOKEN     = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjQyMjI4MGU2LTRkNzctNDI2NC05ZmI4LTg1NWYzYTJi"
             "MmJmMyIsImxhc3RfcGFzc3dvcmRfY2hhbmdlIjoxNzUwNjYwODczLCJleHAiOjE3NjgxOTY0Mjd9."
             "CpsK965pZNKQ9jXvGMuSVL9AZAh6YkPecHr9uKu7-Sk")

URL = f"https://chat.qwen.ai/api/v2/chat/completions?chat_id={CHAT_ID}"
# ----------------------------

session = requests.Session()
session.headers.update({
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"),
    "Accept": "application/json",
    "Accept-Language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Content-Type": "application/json",
    "Origin": "https://chat.qwen.ai",
    "Referer": f"https://chat.qwen.ai/c/{CHAT_ID}",
    "Sec-Ch-Ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Version": "0.1.31",
    "X-Request-Id": str(uuid.uuid4()),
    "X-Accel-Buffering": "no",
})

# Cookie lấy từ browser (bỏ bớt để gọn, bạn paste đầy đủ nếu cần)
session.headers["Cookie"] = f"token={TOKEN}; x-ap=ap-southeast-1; xlly_s=1"

def ask_qwen(message: str):
    payload = {
        "stream": True,
        "version": "2.1",
        "incremental_output": True,
        "chat_id": CHAT_ID,
        "chat_mode": "normal",
        "model": "qwen3-max-2025-10-30",
        "parent_id": PARENT_ID,
        "messages": [
            {
                "fid": str(uuid.uuid4()),
                "parentId": PARENT_ID,
                "childrenIds": [],
                "role": "user",
                "content": message,
                "user_action": "chat",
                "files": [],
                "timestamp": int(uuid.uuid1().time // 10**7),  # ~ now
                "models": ["qwen3-max-2025-10-30"],
                "chat_type": "t2t",
                "feature_config": {
                    "thinking_enabled": False,
                    "output_schema": "phase",
                    "research_mode": "normal",
                },
                "extra": {"meta": {"subChatType": "t2t"}},
                "sub_chat_type": "t2t",
            }
        ],
        "timestamp": int(uuid.uuid1().time // 10**7),
    }

    with session.post(URL, json=payload, stream=True) as resp:
        resp.raise_for_status()
        
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            # Server gửi dạng "data: {...}" (SSE)
            if raw.startswith("data:"):
                chunk = json.loads(raw[5:].strip())
                # chunk có thể chứa "choices"[0]["delta"]["content"]
                if chunk.get("choices"):
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        print(delta["content"], end="", flush=True)

if __name__ == "__main__":
    try:
        while True:
            prompt = input("\nBạn: ")
            if not prompt.strip():
                break
            print("Qwen: ", end="")
            ask_qwen(prompt)
    except KeyboardInterrupt:
        print("\nBye!")