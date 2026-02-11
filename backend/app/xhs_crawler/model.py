# -*- coding: utf-8 -*-
"""小红书 URL 解析模型。"""
from pydantic import BaseModel, Field


class NoteUrlInfo(BaseModel):
    note_id: str = Field(title="note id")
    xsec_token: str = Field(default="", title="xsec token")
    xsec_source: str = Field(default="", title="xsec source")


class CreatorUrlInfo(BaseModel):
    user_id: str = Field(title="user id")
    xsec_token: str = Field(default="", title="xsec token")
    xsec_source: str = Field(default="", title="xsec source")
