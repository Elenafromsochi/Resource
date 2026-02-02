from __future__ import annotations

import logging
from typing import Iterable

import tiktoken
from openai import AsyncOpenAI
from openai import OpenAIError

from app.config import DEEPSEEK_API_KEY
from app.config import DEEPSEEK_BASE_URL
from app.config import DEEPSEEK_MAX_INPUT_TOKENS
from app.config import DEEPSEEK_MAX_OUTPUT_TOKENS
from app.config import DEEPSEEK_MAX_TOTAL_TOKENS
from app.config import DEEPSEEK_MODEL
from app.config import DEEPSEEK_TIMEOUT_SECONDS
from app.exceptions import ExternalServiceError


logger = logging.getLogger(__name__)

TOKEN_OVERHEAD_PER_MESSAGE = 4
TOKEN_OVERHEAD_REQUEST = 2
TOKEN_SAFETY_MARGIN = 128


class _PromptBuilder:
    def __init__(self) -> None:
        self._sections: list[str] = []

    def add_lines(self, title: str, lines: Iterable[str] | None, *, separator: str = '\n') -> None:
        if not lines:
            return
        cleaned = [line for line in lines if line]
        if not cleaned:
            return
        body = separator.join(cleaned)
        self._sections.append(f'{title}:\n{body}')

    def add_heading(self, title: str) -> None:
        self._sections.append(f'{title}:')

    def render(self) -> str:
        return '\n\n'.join(self._sections).strip()


class DeepSeek:
    def __init__(self, api_key: str = DEEPSEEK_API_KEY) -> None:
        self.api_key = api_key
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=DEEPSEEK_BASE_URL,
            timeout=DEEPSEEK_TIMEOUT_SECONDS,
        )
        self._tokenizer = self._build_tokenizer(DEEPSEEK_MODEL)

    async def close(self) -> None:
        await self.client.close()

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float,
        model: str = DEEPSEEK_MODEL,
    ) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except OpenAIError as exc:
            logger.warning('DeepSeek request failed: %s', exc)
            raise ExternalServiceError('DeepSeek request failed') from exc
        if not response.choices:
            raise ExternalServiceError('DeepSeek response parsing failed')
        content = response.choices[0].message.content
        if not content:
            raise ExternalServiceError('DeepSeek response parsing failed')
        return content

    async def chat_in_chunks(
        self,
        *,
        system_prompt: str,
        hashtags: list[str],
        message_blocks: list[str],
        max_tokens: int = DEEPSEEK_MAX_OUTPUT_TOKENS,
        temperature: float,
        model: str = DEEPSEEK_MODEL,
    ) -> list[str]:
        if not message_blocks:
            return []
        chunks = self._build_chunked_user_messages(
            system_prompt=system_prompt,
            hashtags=hashtags,
            message_blocks=message_blocks,
            max_output_tokens=max_tokens,
        )
        results: list[str] = []
        for user_content in chunks:
            results.append(
                await self.chat(
                    [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_content},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model=model,
                ),
            )
        return results

    def _build_tokenizer(self, model: str):
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            return tiktoken.get_encoding('cl100k_base')

    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self._tokenizer.encode(text))

    def _user_token_budget(self, system_prompt: str, max_output_tokens: int) -> int:
        input_budget = min(
            DEEPSEEK_MAX_INPUT_TOKENS,
            DEEPSEEK_MAX_TOTAL_TOKENS - max_output_tokens,
        )
        input_budget = max(0, input_budget - TOKEN_SAFETY_MARGIN)
        system_tokens = self._count_tokens(system_prompt) + TOKEN_OVERHEAD_PER_MESSAGE
        overhead = TOKEN_OVERHEAD_PER_MESSAGE + TOKEN_OVERHEAD_REQUEST
        available = input_budget - system_tokens - overhead
        if available <= 0:
            raise ExternalServiceError('DeepSeek request is too large')
        return available

    def _build_user_prefix(self, hashtags: list[str]) -> str:
        builder = _PromptBuilder()
        builder.add_lines('EXISTING_HASHTAGS', hashtags)
        builder.add_heading('MESSAGES')
        return builder.render()

    def _build_user_content(self, prefix: str, blocks: list[str]) -> str:
        if not blocks:
            return prefix
        if not prefix:
            return '\n\n'.join(blocks)
        return f'{prefix}\n' + '\n\n'.join(blocks)

    def _split_long_block(self, block: str, max_tokens: int) -> list[str]:
        if max_tokens <= 0:
            raise ExternalServiceError('DeepSeek request is too large')
        tokens = self._tokenizer.encode(block)
        if len(tokens) <= max_tokens:
            return [block]
        parts: list[str] = []
        for index in range(0, len(tokens), max_tokens):
            parts.append(self._tokenizer.decode(tokens[index : index + max_tokens]))
        return parts

    def _build_chunked_user_messages(
        self,
        *,
        system_prompt: str,
        hashtags: list[str],
        message_blocks: list[str],
        max_output_tokens: int,
    ) -> list[str]:
        user_budget = self._user_token_budget(system_prompt, max_output_tokens)
        prefix = self._build_user_prefix(hashtags)
        prefix_tokens = self._count_tokens(f'{prefix}\n') if prefix else 0
        if prefix_tokens >= user_budget:
            raise ExternalServiceError('DeepSeek request is too large')

        separator_tokens = self._count_tokens('\n\n')
        chunks: list[list[str]] = []
        current_blocks: list[str] = []
        current_tokens = prefix_tokens
        max_block_tokens = max(1, user_budget - prefix_tokens)

        for block in message_blocks:
            parts = self._split_long_block(block, max_block_tokens)
            for part in parts:
                part_tokens = self._count_tokens(part)
                extra = separator_tokens if current_blocks else 0
                if current_blocks and current_tokens + extra + part_tokens > user_budget:
                    chunks.append(current_blocks)
                    current_blocks = []
                    current_tokens = prefix_tokens
                    extra = 0
                if current_tokens + extra + part_tokens > user_budget:
                    raise ExternalServiceError('DeepSeek request is too large')
                if extra:
                    current_tokens += separator_tokens
                current_blocks.append(part)
                current_tokens += part_tokens

        if current_blocks:
            chunks.append(current_blocks)
        return [self._build_user_content(prefix, blocks) for blocks in chunks]
