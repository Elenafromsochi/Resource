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
    questions_map: dict = Field(default_factory=dict)  # field_name -> question_text
    provider: str = ""


class ClarificationsIn(BaseModel):
    draft: CardDraft  # черновик карточки
    clarifications: dict  # ответы на уточняющие вопросы: {field_name: answer}


# --- Новая система Intake (две независимые модели) ---
class IntakeExtractIn(BaseModel):
    text: str  # свободный текст про ресурс/потребность
    current_state: dict | None = None  # опционально, текущее состояние для обновления


class IntakeExtractOut(BaseModel):
    mode: str | None  # "resource" | "need"
    category: str | None  # "skill" | "thing" | "space" | "knowledge"
    object_text: str | None  # описание объекта
    object_level: int | None  # уровень (зависит от категории)
    transfer_form: str | None  # "permanent" | "temporary" (для thing/space)
    when_type: str | None  # "once" | "period" | "regular"
    when_window: str | None  # "по выходным, 3 раза в неделю"
    urgency: str | None  # "urgent" | "week" | "relaxed"
    where_mode: str | None  # "online" | "offline"
    where_geo: str | None  # "м.Студенческая, Москва"
    where_side: str | None  # "mine" | "yours" | "neutral"
    counter_value: list[str] | None  # ["gift", "money", "barter", "unit"]
    priority_fields: list[str] | None  # критичные поля для этого типа
    evidence: dict = Field(default_factory=dict)  # field -> дословный фрагмент


class IntakeQuestion(BaseModel):
    field: str  # название поля
    text: str  # текст вопроса
    explanation: str  # зачем спрашиваю
    variants: list[str]  # предложенные варианты (2-5)


class IntakeClarifyIn(BaseModel):
    state: IntakeExtractOut  # результат extract_intake


class IntakeClarifyOut(BaseModel):
    questions: list[IntakeQuestion]  # max 3 вопроса по приоритету
    stop_reason: str | None  # "ready_to_search" | "need_more_info" | None
