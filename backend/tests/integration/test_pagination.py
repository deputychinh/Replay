"""Keyset pagination: no duplicates, no gaps, stable order for every sort."""

import pytest
from httpx import AsyncClient

from app.common.enums import TicketSort
from tests.integration.conftest import API, body


@pytest.mark.parametrize("sort", list(TicketSort))
async def test_pages_cover_every_ticket_once(client: AsyncClient, agent: dict[str, str], sort: TicketSort) -> None:
    everything = body(await client.get(f"{API}/tickets?sort={sort}&limit=100", headers=agent))["items"]
    seen: list[str] = []
    cursor = None
    while True:
        query = f"{API}/tickets?sort={sort}&limit=7" + (f"&cursor={cursor}" if cursor else "")
        page = body(await client.get(query, headers=agent))
        seen += [t["id"] for t in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == [t["id"] for t in everything]
    assert len(seen) == len(set(seen))


async def test_search_and_filters(client: AsyncClient, agent: dict[str, str]) -> None:
    hits = body(await client.get(f"{API}/tickets?q=invoice&limit=50", headers=agent))["items"]
    assert hits and all("invoice" in t["subject"].lower() for t in hits)
    urgent = body(await client.get(f"{API}/tickets?priority=urgent&limit=50", headers=agent))["items"]
    assert all(t["priority"] == "urgent" for t in urgent)
    assert (await client.get(f"{API}/tickets?cursor=garbage", headers=agent)).status_code == 422
