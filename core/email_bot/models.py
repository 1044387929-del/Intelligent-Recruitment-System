from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.message import Message
from typing import Optional


@dataclass(frozen=True)
# frozen=True 表示这个 dataclass 实例创建之后不能再改字段（近似「只读对象」）
class EmailAddress:
    """A parsed email address with convenient fields."""
    # 邮件地址的名称
    name: str
    # 邮件地址
    address: str


@dataclass(frozen=True)
class ParsedEmail:
    """A parsed email with convenient fields."""

    # 邮件的唯一标识
    uid: str
    # 邮件的唯一标识
    message_id: str
    # 邮件主题
    subject: str
    # 邮件发件人
    from_: EmailAddress
    # 邮件收件人
    to: list[EmailAddress]
    # 邮件抄送人
    cc: list[EmailAddress]
    # 邮件发送时间
    date: Optional[datetime]

    text: str
    html: str

    raw: Message

