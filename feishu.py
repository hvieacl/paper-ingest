from __future__ import annotations
import os
import time
from typing import Any
import requests

BASE = "https://open.feishu.cn/open-apis"

class FeishuBitableClient:
    def __init__(self):
        self.app_id = os.environ["FEISHU_APP_ID"]
        self.app_secret = os.environ["FEISHU_APP_SECRET"]
        self.app_token = os.environ["FEISHU_APP_TOKEN"]
        self.table_id = os.environ["FEISHU_TABLE_ID"]
        self._token = None
        self._token_expire = 0.0
        self._fields = None

    def _tenant_token(self) -> str:
        if self._token and time.time() < self._token_expire - 120:
            return self._token

        r = requests.post(
            f"{BASE}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code", 0) != 0:
            raise RuntimeError(f"飞书获取 tenant token 失败: {data}")
        self._token = data["tenant_access_token"]
        self._token_expire = time.time() + int(data.get("expire", 7200))
        return self._token

    def _headers(self):
        return {
            "Authorization": f"Bearer {self._tenant_token()}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def get_fields(self) -> dict[str, dict[str, Any]]:
        if self._fields is not None:
            return self._fields

        url = f"{BASE}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields"
        params = {"page_size": 100}
        fields = {}
        page_token = None
        while True:
            if page_token:
                params["page_token"] = page_token
            r = requests.get(url, headers=self._headers(), params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            if data.get("code", 0) != 0:
                raise RuntimeError(f"读取飞书字段失败: {data}")
            for item in data.get("data", {}).get("items", []):
                fields[item["field_name"]] = item
            if not data.get("data", {}).get("has_more"):
                break
            page_token = data["data"]["page_token"]

        self._fields = fields
        return fields

    def validate_field_names(self, payload: dict[str, Any]) -> None:
        fields = self.get_fields()
        missing = [name for name in payload if name not in fields]
        if missing:
            raise ValueError(
                "飞书表缺少这些字段："
                + "、".join(missing)
                + "。请先按 README 创建/重命名字段，或修改 schema.FEISHU_FIELD_MAP。"
            )

    def list_records(self) -> list[dict[str, Any]]:
        url = f"{BASE}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
        params = {"page_size": 500}
        out = []
        page_token = None
        while True:
            if page_token:
                params["page_token"] = page_token
            r = requests.get(url, headers=self._headers(), params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            if data.get("code", 0) != 0:
                raise RuntimeError(f"读取飞书记录失败: {data}")
            out.extend(data.get("data", {}).get("items", []))
            if not data.get("data", {}).get("has_more"):
                break
            page_token = data["data"]["page_token"]
        return out

    def find_by_hash(self, paper_hash: str, hash_field: str = "PaperHash"):
        # 文献库规模通常只有几百条，V1 直接分页拉取并本地匹配：
        # 实现简单、稳定，不依赖复杂 filter DSL。
        for rec in self.list_records():
            if str(rec.get("fields", {}).get(hash_field, "")).strip() == paper_hash:
                return rec
        return None

    def create_record(self, fields: dict[str, Any]) -> dict[str, Any]:
        self.validate_field_names(fields)
        url = f"{BASE}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
        r = requests.post(
            url,
            headers=self._headers(),
            json={"fields": fields},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code", 0) != 0:
            raise RuntimeError(f"飞书写入失败: {data}")
        return data

    def update_record(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        self.validate_field_names(fields)
        url = f"{BASE}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{record_id}"
        r = requests.put(
            url,
            headers=self._headers(),
            json={"fields": fields},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code", 0) != 0:
            raise RuntimeError(f"飞书更新失败: {data}")
        return data
