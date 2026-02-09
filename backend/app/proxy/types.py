# -*- coding: utf-8 -*-
"""Proxy types: IpInfoModel, provider enum."""
import time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProviderNameEnum(str, Enum):
    KUAI_DAILI = "kuaidaili"


class IpInfoModel(BaseModel):
    """Unified IP proxy model."""

    ip: str = Field(description="Proxy IP")
    port: int = Field(description="Proxy port")
    user: str = Field(default="", description="Username for proxy auth")
    password: str = Field(default="", description="Password for proxy auth")
    protocol: str = Field(default="http", description="Protocol")
    expired_time_ts: Optional[int] = Field(default=None, description="Expiration unix timestamp")

    def is_expired(self, buffer_seconds: int = 30) -> bool:
        """True if expired or within buffer_seconds of expiry."""
        if self.expired_time_ts is None:
            return False
        return int(time.time()) >= (self.expired_time_ts - buffer_seconds)
