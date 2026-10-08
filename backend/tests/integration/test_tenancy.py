"""FR-02: one organisation never sees another's data; customers see only their own tickets."""

from httpx import AsyncClient

from tests.integration.conftest import API, body


async def test_cross_tenant_ids_are_not_found(client: AsyncClient, agent: dict[str, str], other_org: dict[str, str]) -> None:
    ticket = body(await client.get(f"{API}/tickets?limit=1", headers=agent))["items"][0]
    for method, path in [
        ("GET", f"/tickets/{ticket['id']}"),
        ("GET", f"/tickets/{ticket['id']}/messages"),
        ("GET", f"/tickets/{ticket['id']}/events"),
        ("PATCH", f"/tickets/{ticket['id']}"),
    ]:
        response = await client.request(method, f"{API}{path}", headers=other_org, json={} if method == "PATCH" else None)
        assert response.status_code == 404, (method, path, response.text)

    their_list = body(await client.get(f"{API}/tickets?limit=100", headers=other_org))["items"]
    assert ticket["id"] not in {t["id"] for t in their_list}
    assert len(their_list) == 3


async def test_customer_sees_only_own_tickets_and_no_internal_notes(
    client: AsyncClient, agent: dict[str, str], customer: dict[str, str], jobs: object
) -> None:
    mine = body(await client.post(f"{API}/tickets", headers=customer, json={"subject": "Where is my invoice?", "body": "Hello"}))
    body(
        await client.post(
            f"{API}/tickets/{mine['id']}/messages",
            headers=agent,
            json={"body": "VIP customer, be quick", "kind": "internal_note"},
        )
    )

    listed = body(await client.get(f"{API}/tickets?limit=100", headers=customer))["items"]
    me = body(await client.get(f"{API}/auth/me", headers=customer))["user"]["id"]
    assert listed and all(t["requester"]["id"] == me for t in listed)

    messages = body(await client.get(f"{API}/tickets/{mine['id']}/messages", headers=customer))
    assert [m["kind"] for m in messages] == ["public_reply"]

    someone_else = body(await client.get(f"{API}/tickets?limit=100", headers=agent))["items"]
    other = next(t for t in someone_else if t["requester"]["id"] != me)
    assert (await client.get(f"{API}/tickets/{other['id']}", headers=customer)).status_code == 404


async def test_customers_cannot_use_staff_endpoints(client: AsyncClient, customer: dict[str, str]) -> None:
    ticket = body(await client.get(f"{API}/tickets?limit=1", headers=customer))["items"][0]
    assert (await client.patch(f"{API}/tickets/{ticket['id']}", headers=customer, json={"status": "solved"})).status_code == 403
    assert (await client.get(f"{API}/reports/dashboard", headers=customer)).status_code == 403
    note = await client.post(
        f"{API}/tickets/{ticket['id']}/messages", headers=customer, json={"body": "x", "kind": "internal_note"}
    )
    assert note.status_code == 403
