from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re

class EmailInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message_id: str = Field(min_length=1,max_length=200)
    thread_id: str = Field(default='',max_length=200)
    sender: str = Field(min_length=1,max_length=150)
    sender_email: str = Field(min_length=3,max_length=254)
    subject: str = Field(min_length=1,max_length=500)
    body: str = Field(min_length=1,max_length=24000)
    received_at: str = Field(default='',max_length=80)
    @field_validator('sender_email')
    @classmethod
    def address(cls,v):
        if not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+',v) or '\r' in v or '\n' in v:
            raise ValueError('Invalid sender address')
        return v

class Analysis(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True)
    category: Literal['Sales','Support','Billing','Internal','Other']
    priority: Literal['High','Medium','Low']
    sentiment: Literal['Positive','Neutral','Negative']
    summary: str = Field(min_length=10,max_length=700)
    action_required: bool
    suggested_reply: str = Field(max_length=5000)
    @field_validator('summary')
    @classmethod
    def nonempty(cls,v):
        if not v.strip():raise ValueError('Summary is empty')
        return v.strip()

class Review(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision: int = Field(ge=0)
    draft: str = Field(max_length=5000)
    action: Literal['save','approve','complete']

class DraftReceipt(BaseModel):
    model_config=ConfigDict(extra='forbid')
    gmail_draft_id: str = Field(min_length=1,max_length=200)
