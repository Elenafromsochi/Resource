"""Pydantic-схемы запросов/ответов."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


# --- Авторизация ---
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Профиль / личный кабинет ---
class ProfileData(BaseModel):
    full_name: str = ""
    occupation: str = ""
    city: str = ""
    about: str = ""
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    goals: str = ""
    contacts: str = ""


class ProfileOut(ProfileData):
    email: str
    completeness: float = 0.0


# --- ИИ-помощник кабинета ---
class AssistIn(BaseModel):
    text: str  # свободный рассказ о себе (или ответ на вопрос помощника)


class AssistQuestion(BaseModel):
    field: str
    question: str
    examples: list[str] = Field(default_factory=list)


class AssistOut(BaseModel):
    draft: ProfileData  # предложенные ИИ значения полей (черновик, редактируемый)
    questions: list[AssistQuestion] = Field(default_factory=list)
    provider: str  # "claude" | "local"
