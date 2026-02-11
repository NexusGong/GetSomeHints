# -*- coding: utf-8 -*-
"""抖音 URL 解析模型。"""
from pydantic import BaseModel, Field


class VideoUrlInfo(BaseModel):
    aweme_id: str = Field(title="视频 id")
    url_type: str = Field(default="normal", title="normal | short | modal")


class CreatorUrlInfo(BaseModel):
    sec_user_id: str = Field(title="创作者 sec_user_id")
