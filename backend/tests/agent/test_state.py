import asyncio
import uuid

import pytest

from app.agent import state
from app.db import connect


@pytest.fixture
async def ready(seeded_db):
    async with await connect(seeded_db) as conn:
        await state.ensure_agent_tables(conn)
    return seeded_db


def _cid() -> str:
    return f"t-{uuid.uuid4().hex[:12]}"


async def _reserve(url: str, cid: str, order_id: int) -> bool:
    async with await connect(url) as conn:
        return (await state.reserve_attempt(conn, cid, order_id)).allowed


async def test_default_state_when_no_row(ready):
    async with await connect(ready) as conn:
        assert await state.get(conn, _cid()) == state.ConversationState()


async def test_ten_concurrent_attempts_allow_at_most_three(ready):
    cid = _cid()
    results = await asyncio.gather(*(_reserve(ready, cid, 910) for _ in range(10)))
    assert sum(results) <= 3
    await _clear_order(ready, 910)


async def _clear_order(url: str, order_id: int) -> None:
    async with await connect(url) as conn:
        await conn.execute(
            "DELETE FROM order_verification_failures WHERE order_id = %s", (order_id,)
        )
        await conn.commit()


async def test_a_new_conversation_cannot_bypass_an_order_lock(ready):
    order_id = 911
    for _ in range(state.ORDER_LOCK_AT):
        assert await _reserve(ready, _cid(), order_id)  # fresh chat id each time

    assert not await _reserve(ready, _cid(), order_id)
    await _clear_order(ready, order_id)


async def test_success_gives_the_attempt_back_and_records_the_order(ready):
    cid = _cid()
    async with await connect(ready) as conn:
        assert (await state.reserve_attempt(conn, cid, 912)).allowed
        await state.confirm_success(conn, cid, 912)
        await state.confirm_success(conn, cid, 912)  # no duplicates

        current = await state.get(conn, cid)
    assert current.failed_attempts == 0
    assert current.verified_order_ids == {912}
    await _clear_order(ready, 912)


async def test_conversation_locks_after_three_failures(ready):
    cid = _cid()
    async with await connect(ready) as conn:
        for _ in range(3):
            assert (await state.reserve_attempt(conn, cid, 913)).allowed
        assert not (await state.reserve_attempt(conn, cid, 913)).allowed
        assert (await state.get(conn, cid)).locked
    await _clear_order(ready, 913)


@pytest.mark.parametrize("bad", ["", "a b", "x" * 129, "../etc", "é"])
async def test_invalid_conversation_ids_are_rejected(ready, bad):
    async with await connect(ready) as conn:
        with pytest.raises(state.InvalidConversationId):
            await state.get(conn, bad)
        with pytest.raises(state.InvalidConversationId):
            await state.reserve_attempt(conn, bad, 1)
