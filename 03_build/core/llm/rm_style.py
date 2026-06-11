"""
Analyze an RM's Gmail episodes and save a style prompt to pulse.rm_style_profiles.
Called after Gmail sync completes. Uses ANTHROPIC_HAIKU for cost efficiency.
"""
from __future__ import annotations

import asyncio
import logging
import os

from psycopg.rows import dict_row

from core.db import get_pool
from core.llm.config import ANTHROPIC_HAIKU, load_env

log = logging.getLogger(__name__)

_MAX_EMAILS = 50
_STYLE_PROMPT_TEMPLATE = (
    "Analyze the following email snippets written by a Relationship Manager at a healthcare "
    "staffing company. Extract their communication style. Return a 100-150 word paragraph "
    "describing: greeting and sign-off patterns, sentence length, formality level, tone, and "
    "any recurring phrases or habits. Write it as instructions for someone impersonating this "
    "RM's writing style.\n\nEmails:\n{samples}"
)
_DEFAULT_STYLE = (
    "Write professionally and warmly. Use a friendly but concise tone. "
    "Keep responses focused and helpful. Be supportive and solution-oriented."
)


def _call_claude(email_samples: str) -> str:
    load_env()
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    response = client.messages.create(
        model=ANTHROPIC_HAIKU,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": _STYLE_PROMPT_TEMPLATE.format(samples=email_samples),
        }],
    )
    return response.content[0].text.strip()


async def analyze_rm_style(user_id: str) -> None:
    """Fetch RM's Gmail episodes, call Claude for style, upsert to DB."""
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        rows = await (await conn.execute(
            """
            SELECT subject, description
            FROM pulse.episodes
            WHERE source = 'gmail'
              AND %s = ANY(tags)
              AND description IS NOT NULL
            ORDER BY source_timestamp DESC
            LIMIT %s
            """,
            [user_id, _MAX_EMAILS],
        )).fetchall()

    if not rows:
        log.info("rm_style: no Gmail episodes for %s — skipping", user_id)
        return

    email_samples = "\n---\n".join(
        f"Subject: {r['subject'] or 'No subject'}\n{r['description']}"
        for r in rows
    )

    try:
        style_prompt = await asyncio.to_thread(_call_claude, email_samples)
    except Exception as exc:
        log.error("rm_style: Claude call failed for %s: %s", user_id, exc)
        return

    pool2 = await get_pool()
    async with pool2.connection() as conn:
        await conn.execute(
            """
            INSERT INTO pulse.rm_style_profiles (rm_pulse_user_id, style_prompt, email_count, analyzed_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (rm_pulse_user_id) DO UPDATE SET
                style_prompt = EXCLUDED.style_prompt,
                email_count  = EXCLUDED.email_count,
                analyzed_at  = EXCLUDED.analyzed_at
            """,
            [user_id, style_prompt, len(rows)],
        )
        await conn.commit()

    log.info("rm_style: profile saved for %s (%d emails analyzed)", user_id, len(rows))
