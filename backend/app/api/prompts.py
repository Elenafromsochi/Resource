from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from app.api.dependencies import get_storage
from app.schemas import PromptCreate
from app.schemas import PromptList
from app.schemas import PromptRead
from app.schemas import PromptUpdate
from app.storage import Storage


router = APIRouter(prefix='/prompts', tags=['prompts'])


def normalize_value(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f'{label} is required',
        )
    return cleaned


@router.get('', response_model=PromptList)
async def list_prompts(storage: Storage = Depends(get_storage)):
    items = await storage.prompts.list()
    return PromptList(items=items)


@router.get('/{prompt_id}', response_model=PromptRead)
async def get_prompt(prompt_id: int, storage: Storage = Depends(get_storage)):
    prompt = await storage.prompts.get_by_id(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Prompt not found',
        )
    return prompt


@router.post('', response_model=PromptRead, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptCreate,
    storage: Storage = Depends(get_storage),
):
    name = normalize_value(payload.name, 'Prompt name')
    content = normalize_value(payload.content, 'Prompt content')
    prompt = await storage.prompts.create(name=name, content=content)
    return prompt


@router.put('/{prompt_id}', response_model=PromptRead)
async def update_prompt(
    prompt_id: int,
    payload: PromptUpdate,
    storage: Storage = Depends(get_storage),
):
    name = None
    content = None
    if payload.name is not None:
        name = normalize_value(payload.name, 'Prompt name')
    if payload.content is not None:
        content = normalize_value(payload.content, 'Prompt content')
    if name is None and content is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Prompt update payload is empty',
        )
    prompt = await storage.prompts.update(
        prompt_id,
        name=name,
        content=content,
    )
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Prompt not found',
        )
    return prompt


@router.delete('/{prompt_id}', status_code=status.HTTP_200_OK)
async def delete_prompt(prompt_id: int, storage: Storage = Depends(get_storage)):
    prompt = await storage.prompts.delete(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Prompt not found',
        )
    return {'status': 'deleted', 'id': prompt_id}
