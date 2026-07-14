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
    avatar: str = ""
    occupation: str = ""
    city: str = ""
    about: str = ""
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    goals: str = ""
    contacts: str = ""
    answers: dict = Field(default_factory=dict)
    resources: list = Field(default_factory=list)  # карточки «Даю/Прошу»


class ProfileOut(ProfileData):
    email: str
    completeness: float = 0.0


# --- ИИ-помощник кабинета ---
class AssistIn(BaseModel):
    text: str  # свободный рассказ о себе (или ответ на вопрос помощника)


class ExtractIn(BaseModel):
    text: str  # свободный рассказ про ресурс/потребность
    kind: str = "give"  # give | ask


class AssistQuestion(BaseModel):
    field: str
    question: str
    examples: list[str] = Field(default_factory=list)


class AssistOut(BaseModel):
    draft: ProfileData  # предложенные ИИ значения полей (черновик, редактируемый)
    questions: list[AssistQuestion] = Field(default_factory=list)
    provider: str  # "claude" | "local"


# --- Карточка ресурса/потребности ---
class CardDraft(BaseModel):
    category: str = ""
    title: str = ""
    description: str = ""
    fields: dict = Field(default_factory=dict)
    amount_money: str = ""
    amount_points: str = ""
    ideal: str = ""
    impact: str = ""
    questions: list[str] = Field(default_factory=list)
    provider: str = ""


class ClarificationsIn(BaseModel):
    draft: CardDraft  # черновик карточки
    clarifications: dict  # ответы на уточняющие вопросы: {field_name: answer}
