import json
import requests
import uuid
import time
from typing import Iterable, Callable, Optional
import re

JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImQwMzZkNjJlLWZiN2UtNDE4Ny04ODg5LTNjNDMxZmE1ZGY2ZCIsImxhc3RfcGFzc3dvcmRfY2hhbmdlIjoxNzUwNjYwODczLCJleHAiOjE3Njc4ODY2MzZ9.-MU-_JUD5lRnjBtVgWL5j3cyMu0ATOdqroLqWFe_Cvw"
CHAT_ID = "dc08efcb-1f65-4cb8-ab35-bab46b8437fd"
PARENT_ID = None        
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
BX_UA = ("231!VC435+mUHOA+jmD4KZ7qZk8FEl2ZWfPwIPF92lBLek2KxVW/XJ2EwruCiDOX5b/I+qgdg3A9CJgFRZ609xp4Cz7aEFu9gONUGhnsWJmtufN6zUvsZgwuRnqYzl6AktUrW74DGvtj2X/T53eT9WFpldN0t85hUOHyNTgeY8Nc6WMD9B5+df/e3km30Q3oyE+jauHhUBWqS6JGHkE+++3+qCS4+ItNN46Q48uCo+r+0N6L5qMnzf5ScgBDAbXlIFsdkuEuz+cbmhjb4zZ4yEc/IWgalkMkTYqma1UWqGDIFR5g8/CFxpNpKRU37CfzS3CK8nCh3fhgMXOUXAvFHvVzXVifNkns/aVvjttShZajWBvSoZ7BRpEeO/s6Af7zAwWxG+k5nINT3cn07IuBVmK2LsjmZ8KLW2qsq5ArbcSyzkU6uEFNV2pUfrnSjvYeB1lgXb8SsvmzFceZPIBHVpHSwumYIz0n0bj5ixazWmxYZxhSl7Zg6sUjOs8DocXWg2CKxVwpMX3c7x7elhSJUjUcuOMpLbSZyPp6Yy10nq8j73Et3LUcOmn0rbk4po9AEPPf9JvKnBj9wo0xM3/MCjZdUoSvhdxtTEn6SRSDP6gq8lhNDHxowAbe25BVBkEEZUEZEZ1jENstYasRt9rowI/mYEP/w14ljXYfcZb6NuLTMHvm9Bni6XCLI/ByPmonSGynAn1kw3lc3y2bCMjE1/4V7gKATZJO2XrGaDuduOo0hQ7ew77tXHv1+CiQcZgReOXgR1c1ihh7eNUMrMPKd0qg/JI7aoLBhj9Gemi37RvZTWkOfGh5aSZnwMq1GthOQswepmOikhVQBwih9drcKcB33o4e9JRJk/hPsZwxjR8EU0pQ45i/D9Kclo5hTdXZnNt5fYWWZiqHN481MCQb7pECxFqZEme1OF9t8OHlwJXohSmNbheUBh9aD8+CWoFohtqH2Zpivm+/5B9+XYhRZD+Ez3EnFUDcpp+HmNiYayA706RPDILNbxzxq3bI4hnzbRUF0oGHrCmszugizr/stK/pLQFuZb11gzZWzZww+ccNInCnkitrSJnMnET39DiEpqXWHGbAJ6d6ltMfdaeQ1gS3YRCEZx43FTSQhu60U+f4faWIdx2Xb4NNjbm2XfqZaFkgo6Qsqr4tU5GgjWbnS84cLqrilkBK6hqswMl2VD3AFC8hwcIXWsO8hgJkVrDPPl+7R0eQAHucGUGJ+1ug9CLax4yUhctqkNYCM7dlHoEXjD7HTZln6tM0IViwMXUgquL3URyt/JB7i69yiT5B7rL/viy2lOvetuIbJReALXHmUwQB/ez39ZkPzQgJod3yJbQcz3KoqPHnSw0x3dWlNUy5KCCqsz0g3PxNShtDikoCDQpOI7BSuKd20M4qy+TCBEgPyNSWqahXwTa6C76Ttil7GMttKqOLfBFw8YRZGoROXlm6aHNSzEWZrv/OUjNfuuN5UXMN3qegh1/69iUziJmLThKeMvmqAY+ATIDFQa3WR2Y8opLVfbj4gUT1vzEjwBKzYEMTdN0B847ll1sSptz1RU/2Lr/=")
BX_UMIDTOKEN = "T2gAqPT0q3WtNHgAitTKchPNmoRkVh9KyTe_X-Z3oNI4cOyVoTurTrOxqJF6S3VDdds="

COOKIE_RAW = (
    "cna=POJTIFfG02ICASp2GKAtmQuZ; "
    "cnaui=d036d62e-fb7e-4187-8889-3c431fa5df6d; "
    "aui=d036d62e-fb7e-4187-8889-3c431fa5df6d; "
    "_bl_uid=hzmn1ikyahI2tRgvCyjktFb3qpp4; "
    "_gcl_au=1.1.1796703808.1765286084; "
    "acw_tc=0a03e59817672814628834933e1462883321de062d0e1b58308f799f1264ee; "
    "x-ap=ap-southeast-1; "
    "sca=8493bc14; "
    "xlly_s=1; "
    f"token={JWT}; "
    "atpsida=28d6e35004ade4b9d6367e80_1767281837_9; "
    "tfstk=gzYr-k1AN43P51HM_CbEuW6hk3QRlwksre6CtBAhNTXoee_FttRUF3OBtwuFnpBkRYQ3iyJwpXIlqXE0ot1MPXUHZwSFt1So90ndiovFZy4urXCUwEJaRzM-2B4FRwDsCVg6wQ_d-A993Nwbe6fa-213--bRO53Kil36wQFDDBxewVgUcchct9vhqi2c_t43KTvhoZfhnzf3r62mg6Bc-yjh-ofcs1X3q_vHij5On9bhqpbmg6BcKwbnaW6hCr5NqjQC4ZQEG3SPIQX47dLPZQqJatkEKEJP4O013y4Hu_RbEqj37D6MXTs1BK0bzwRcTKS64AzyLBA9xi8UEb9MtLLVyNoIwG-Dchsy0Y4FhU1Fjwj4tyAVutpwlN0g3sKDNHYJUWzhwUT1YOIqtyICoFsMjLPK6IbltpI9RAUREBA9Wh_ZzRCymC7V4w2dio3eJ3y3YgfAgOGqgCNS2l6qRAcbvkIJDsWswbELvgfAgOGqgkEd2ZCVCbhR.; "
    "isg=BPX1raxl8OJ3ahrEE_dWLsfOBHGvcqmE1j8OMXca0Gy7ThRAO8PbVqyImAr4OsE8; "
    "ssxmod_itna=1-QqGx9DBDR7D=itG7zG0IbmxQKAK4iQDRDl4BtGR/DIde7=GFWDCOit_wQ4BKq1PmYYKALxXrq5PxDsyK14GkXDWPGEKZfh44oMrGu6prWATbbtqQAQTqISYAT1mpeWbV9Def=0hggnDTwU6Q7eDU4Gnz8DPB8eD44DvDBYD74G_DDeDixGmz4DStxD9DGPQZQWrceDEDYpTxiUqahcHxDLT0Wb7EDDBDD6qcip=oDDlYYO480D5=BaDYSi7NrwN5D8g0eDMWxGXB0k40jyXqvDThKkg8aooxB6yxBQrucT=mOTW56crWG6V=_6lwr0vYQGGlGKiDnnGmiG5QDtnDeAw4BNzlDolqYIeNKxxt4DDPKZyYn2Y8ieYelIHZtcT0yYiibzi1UEGt_NQGHbDOtbbBhND44BG4W0q7e5nAqlhrqobPD; "
    "ssxmod_itna2=1-QqGx9DBDR7D=itG7zG0IbmxQKAK4iQDRDl4BtGR/DIde7=GFWDCOit_wQ4BKq1PmYYKALxXrq5xDfrKWlD2AKODj__E=s4GXHxgQ6Bnxq9Sk8mYhkjpTwEz50O6ULhwV_ulxEyzk3hSkOcdScG4OZ5HshiFTB5GKeKGA=E42cBkfZGz2GKCQz0WCh0wkKhaqAKfhzfxOEik6h8Fql0fVgmhq_F_nbGhqWEO0Zph3iGzvZvjPKIRFKEjvbQstI2_X700ntv4Af0YrnD5Nl1etyF4uP/BKzF1Aw0CY02Ye7SxwPhq5FO9598eRHetWeKhtf545DBBhNDRlWDUiYxD5PoGDD"
)

# ------------- BUILD HEADERS -------------
HEADERS = {
    "accept": "application/json",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9,vi;q=0.8",
    "authorization": f"Bearer {JWT}",
    "bx-ua": BX_UA,
    "bx-umidtoken": BX_UMIDTOKEN,
    "bx-v": "2.5.31",
    "cache-control": "no-cache",
    "connection": "keep-alive",
    "content-type": "application/json",
    "cookie": COOKIE_RAW,
    "host": "chat.qwen.ai",
    "origin": "https://chat.qwen.ai",
    "pragma": "no-cache",
    "referer": f"https://chat.qwen.ai/c/{CHAT_ID}",
    "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "source": "web",
    "timezone": "Thu Jan 01 2026 22:37:32 GMT+0700",
    "user-agent": USER_AGENT,
    "version": "0.1.30",
    "x-accel-buffering": "no",
    "x-request-id": "45cab222-35fa-4767-bb8b-c4cb9d2a86dc"
}

class BotChatAgentAPI:
    """
    Agent tương tác với chat.qwen.ai – giữ nguyên mọi const ở trên
    """
    def __init__(self,
                 jwt: str = JWT,
                 chat_id: str = CHAT_ID,
                 parent_id: str = PARENT_ID) -> None:
        self.jwt = jwt
        self.chat_id = chat_id
        self.parent_id = parent_id
        self.url = f"https://chat.qwen.ai/api/v2/chat/completions?chat_id={self.chat_id}"


        self.headers = HEADERS.copy()
        self.headers["authorization"] = f"Bearer {self.jwt}"

    # --------------- CORE ---------------
    def send(self, content: str, stream: bool = True) -> requests.Response:
        """Gửi tin nhắn và trả về object Response đã stream=True"""
        fid = str(uuid.uuid4())
        payload = {
            "stream": stream,
            "incremental_output": True,
            "chat_id": self.chat_id,
            "chat_mode": "normal",
            "model": "qwen3-max-2025-10-30",
            "parent_id": self.parent_id,
            "messages": [
                {
                    "fid": fid,
                    "parentId": self.parent_id,
                    # "childrenIds": [str(uuid.uuid4())],  # placeholder
                    "role": "user",
                    "content": content,
                    "user_action": "chat",
                    "files": [],
                    "timestamp": int(time.time()),
                    "models": ["qwen3-max"],
                    "chat_type": "t2t",
                    "feature_config": {
                        "thinking_enabled": False,
                        "output_schema": "phase"
                    },
                    "extra": {"meta": {"subChatType": "t2t"}},
                    "sub_chat_type": "t2t"
                }
            ],
            "timestamp": int(time.time())
        }

        return requests.post(self.url, headers=self.headers, json=payload, stream=stream)

    def stream_tokens(self, prompt: str) -> Iterable[str]:

        resp = self.send(prompt, stream=True)
        with resp:
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw.startswith("data: "):
                    continue
                chunk = raw[6:].strip()
                if chunk in ("[DONE]", ""):
                    break
                try:
                    data = json.loads(chunk)
                    delta = data["choices"][0]["delta"]
                    token = delta.get("content", "")
                except Exception:
                    continue
                if token:
                    yield token


