"""Validated anonymous bot-summary contracts; no user identity fields."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class RoleCount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: int = Field(ge=0, le=100000)
    count: int = Field(ge=0)

class RegistrySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_identities: int = Field(ge=0)
    chat_identities: int = Field(ge=0)
    managed_chats: int | None = Field(default=None, ge=0)
    role_definitions: int | None = Field(default=None, ge=0)
    role_counts: list[RoleCount] = Field(max_length=64)
    unknown_entries: int = Field(ge=0)
    chat_types: dict[Literal["private", "group", "supergroup", "channel", "unknown"], int]
    users_state: Literal["available"] = "available"
    chats_state: Literal["available", "unavailable"]
    rules_state: Literal["available", "unavailable"]
