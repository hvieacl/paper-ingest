from __future__ import annotations
import os
import time
from typing import Any
import requests
from requests.exceptions import ConnectionError as RequestConnectionError, Timeout as RequestTimeout

BASE = "https://open.feishu.cn/open-apis"

class FeishuAPIError(RuntimeError):
    def __init__(self, action: str, status_code: int, detail):
        self.action = action
        self.status_code = status_code
        self.detail = detail
        super().__init__(
            f"{action}失败：HTTP {status_code}；飞书响应：{detail}"
        )

class FeishuBitableClient:
    def __init__(self):
        self.app_id = os.environ["FEISHU_APP_ID"]
        self.app_secret = os.environ["FEISHU_APP_SECRET"]
        self.app_token = self._clean_id(os.environ["FEISHU_APP_TOKEN"], "FEISHU_APP_TOKEN")
        self.table_id = self._clean_id(os.environ["FEISHU_TABLE_ID"], "FEISHU_TABLE_ID")
        self._token = None
        self._token_expire = 0.0
        self._fields = None
        self.session = requests.Session()
        self.session.trust_env = os.getenv("FEISHU_USE_PROXY", "0").strip() == "1"
        self.read_retries = max(0, int(os.getenv("FEISHU_READ_RETRIES", "2")))

    @staticmethod
    def _clean_id(value: str, name: str) -> str:
        """
        容错处理从飞书 URL 中复制出来的 token/id。
        例如误把 `tblxxxx&view=vewxxxx` 整段粘到 FEISHU_TABLE_ID，
        会自动截取为 `tblxxxx`。
        """
        value = value.strip()
        if not value:
            raise RuntimeError(f"缺少配置：{name}")

        for sep in ("?", "&", "#", "/"):
            if sep in value:
                value = value.split(sep, 1)[0].strip()

        if not value:
            raise RuntimeError(f"{name} 格式无效")
        return value

    def _read_request(self, method: str, url: str, **kwargs) -> requests.Response:
        for attempt in range(self.read_retries + 1):
            try:
                return self.session.request(method, url, **kwargs)
            except (RequestConnectionError, RequestTimeout) as exc:
                if attempt >= self.read_retries:
                    raise
                print(f"      [飞书网络] {method} 请求连接失败，将重试 ({attempt + 1}/{self.read_retries})：{exc}")
                time.sleep(min(2 ** attempt, 4))
        raise RuntimeError("飞书读取请求未完成")

    def _tenant_token(self) -> str:
        if self._token and time.time() < self._token_expire - 120:
            return self._token

        r = self._read_request("POST",
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

    @staticmethod
    def _raise_api_error(r: requests.Response, action: str) -> None:
        if r.ok:
            return
        try:
            detail = r.json()
        except Exception:
            detail = r.text[:1000]
        raise FeishuAPIError(action, r.status_code, detail)

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
            r = self._read_request("GET", url, headers=self._headers(), params=params, timeout=20)
            self._raise_api_error(r, "读取飞书字段")
            data = r.json()
            if data.get("code", 0) != 0:
                raise RuntimeError(f"读取飞书字段失败：{data}")
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
        # 100 足够用于文献库分页，也更保守地兼容飞书接口参数限制。
        params = {"page_size": 100}
        out = []
        page_token = None
        while True:
            if page_token:
                params["page_token"] = page_token
            r = self._read_request("GET", url, headers=self._headers(), params=params, timeout=30)
            self._raise_api_error(r, "读取飞书记录")
            data = r.json()
            if data.get("code", 0) != 0:
                raise RuntimeError(f"读取飞书记录失败：{data}")
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
        paper_hash = str(fields.get("PaperHash", "")).strip()

        # POST 非幂等：连接中断后先检查是否实际写入成功，避免重复记录。
        for attempt in range(2):
            try:
                r = self.session.post(
                    url,
                    headers=self._headers(),
                    json={"fields": fields},
                    timeout=30,
                )
            except (RequestConnectionError, RequestTimeout) as exc:
                print(f"      [飞书网络] 写入连接中断，正在核对 PaperHash：{exc}")
                if not paper_hash:
                    raise RuntimeError("飞书写入响应丢失，且缺少 PaperHash，无法安全重试。") from exc
                try:
                    existing = self.find_by_hash(paper_hash)
                except Exception as verify_exc:
                    raise RuntimeError(
                        "飞书写入响应丢失，且重新查询失败；无法确认是否已写入。"
                        "请稍后普通导入，不要强制重跑。"
                    ) from verify_exc
                if existing:
                    print("      ✓ 飞书已存在对应 PaperHash，确认写入成功（响应可能丢失）")
                    return {"data": {"record": existing}}
                if attempt == 0:
                    print("      ↻ 核对未发现记录，准备重试一次写入")
                    time.sleep(2)
                    continue
                raise RuntimeError(
                    "飞书写入连续连接中断；已核对未找到记录。请稍后普通导入。"
                ) from exc

            self._raise_api_error(r, "飞书写入")
            data = r.json()
            if data.get("code", 0) != 0:
                raise RuntimeError(f"飞书写入失败：{data}")
            return data

        raise RuntimeError("飞书写入未完成")

    def update_record(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        self.validate_field_names(fields)
        url = f"{BASE}/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{record_id}"
        r = self.session.put(
            url,
            headers=self._headers(),
            json={"fields": fields},
            timeout=30,
        )
        self._raise_api_error(r, "飞书更新")
        data = r.json()
        if data.get("code", 0) != 0:
            raise RuntimeError(f"飞书更新失败：{data}")
        return data
