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


class FeedbackIn(BaseModel):
    # question may be empty (e.g. an assistant greeting with no preceding user
    # message); the service substitutes a placeholder so the gap is never lost.
    question: str = Field(default="", max_length=4000)
    answer: str = Field(default="", max_length=8000)
    route: str | None = Field(default=None, max_length=300)
