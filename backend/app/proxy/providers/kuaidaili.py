# -*- coding: utf-8 -*-
"""KuaiDaili DPS (getdps) proxy provider. Docs: https://www.kuaidaili.com/doc/api/getdps/"""
import os
import re
import time
from typing import Any, Dict, List

import httpx

from app.proxy.base_proxy import IpCache, ProxyProvider
from app.proxy.types import IpInfoModel, ProviderNameEnum

DELTA_EXPIRED_SECOND = 5  # Consider IP expired 5s early to avoid mid-request expiry


def _parse_kuaidaili_proxy(proxy_info: str) -> tuple[str, int, int]:
    """Parse one entry: 'ip:port,expire_seconds' -> (ip, port, expire_seconds)."""
    pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5}),(\d+)"
    match = re.search(pattern, proxy_info)
    if not match:
        raise ValueError(f"invalid kuaidaili proxy info: {proxy_info!r}")
    return match.group(1), int(match.group(2)), int(match.group(3))


class KuaiDaiLiProxy(ProxyProvider):
    """KuaiDaili getdps API provider."""

    def __init__(
        self,
        kdl_user_name: str,
        kdl_user_pwd: str,
        kdl_secret_id: str,
        kdl_signature: str,
    ) -> None:
        self.kdl_user_name = kdl_user_name
        self.kdl_user_pwd = kdl_user_pwd
        self.api_base = "https://dps.kdlapi.com/"
        self.secret_id = kdl_secret_id
        self.signature = kdl_signature
        self.ip_cache = IpCache()
        self.proxy_brand_name = ProviderNameEnum.KUAI_DAILI.value
        self.params: Dict[str, Any] = {
            "secret_id": self.secret_id,
            "signature": self.signature,
            "pt": 1,
            "format": "json",
            "sep": 1,
            "f_et": 1,
        }

    async def get_proxy(self, num: int) -> List[IpInfoModel]:
        """Fetch num IPs; use cache first, then getdps to supplement."""
        cached = self.ip_cache.load_all_ip(proxy_brand_name=self.proxy_brand_name)
        if len(cached) >= num:
            return cached[:num]

        need = num - len(cached)
        params = {**self.params, "num": need}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(self.api_base + "api/getdps/", params=params)

        if resp.status_code != 200:
            raise Exception(f"getdps status {resp.status_code}: {resp.text}")

        data = resp.json()
        if data.get("code") != 0:
            msg = data.get("msg", data)
            # 额度用尽(1/2)等时返回已有缓存，避免直接报错
            if len(cached) > 0 and data.get("code") in (1, 2):
                return cached[:num]
            raise Exception(f"getdps error: {msg}")

        proxy_list = data.get("data", {}).get("proxy_list") or []
        now = int(time.time())
        result: List[IpInfoModel] = list(cached)
        for raw in proxy_list:
            try:
                ip, port, expire_sec = _parse_kuaidaili_proxy(raw)
            except ValueError:
                continue
            # expire_sec from API is relative (seconds until expiry); convert to absolute and subtract buffer
            expired_time_ts = now + expire_sec - DELTA_EXPIRED_SECOND
            model = IpInfoModel(
                ip=ip,
                port=port,
                user=self.kdl_user_name,
                password=self.kdl_user_pwd,
                expired_time_ts=expired_time_ts,
            )
            key = f"{self.proxy_brand_name}_{ip}_{port}"
            self.ip_cache.set_ip(key, model.model_dump_json(), ex=expire_sec - DELTA_EXPIRED_SECOND)
            result.append(model)
            if len(result) >= num:
                break
        return result[:num]


def new_kuai_daili_proxy() -> KuaiDaiLiProxy:
    """Build KuaiDaili provider from env (KDL_* or kdl_*)."""
    secret_id = os.getenv("KDL_SECRET_ID") or os.getenv("KDL_SECERT_ID") or os.getenv("kdl_secret_id", "")
    signature = os.getenv("KDL_SIGNATURE") or os.getenv("kdl_signature", "")
    user = os.getenv("KDL_USER_NAME") or os.getenv("kdl_user_name", "")
    pwd = os.getenv("KDL_USER_PWD") or os.getenv("kdl_user_pwd", "")
    return KuaiDaiLiProxy(
        kdl_user_name=user,
        kdl_user_pwd=pwd,
        kdl_secret_id=secret_id,
        kdl_signature=signature,
    )
