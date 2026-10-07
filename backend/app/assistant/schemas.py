"""Request schemas for the assistant API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NewConversationIn(BaseModel):
    title: str | None = Field(default=None, max_length=300)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    route: str | None = Field(default=None, max_length=300)


class AnswerGapIn(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)
