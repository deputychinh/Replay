"""Business flows B2 + B3: open → auto-assign → reply pauses SLA → customer reply resumes → solve."""

from httpx import AsyncClient

from tests.integration.conftest import API, Jobs, body


async def test_full_ticket_lifecycle(client: AsyncClient, agent: dict[str, str], customer: dict[str, str], jobs: Jobs) -> None:
    created = body(
        await client.post(
            f"{API}/tickets", headers=customer, json={"subject": "API returns 502", "body": "Since 9am.", "priority": "urgent"}
        )
    )
    assert created["status"] == "new" and created["sla_state"] == "active"
    assert created["first_response_due_at"] and created["resolution_due_at"]

    assert await jobs.run() >= 1  # auto-assign (+ assignment email)
    ticket = body(await client.get(f"{API}/tickets/{created['id']}", headers=agent))
    assert ticket["assignee"] is not None and ticket["status"] == "open"

    body(await client.post(f"{API}/tickets/{created['id']}/messages", headers=agent, json={"body": "Investigating."}))
    paused = body(await client.get(f"{API}/tickets/{created['id']}", headers=agent))
    assert paused["status"] == "pending_customer" and paused["sla_state"] == "paused"
    assert paused["first_responded_at"] and paused["resolution_due_at"] is None

    body(await client.post(f"{API}/tickets/{created['id']}/messages", headers=customer, json={"body": "Still broken."}))
    resumed = body(await client.get(f"{API}/tickets/{created['id']}", headers=agent))
    assert resumed["status"] == "open" and resumed["sla_state"] == "active" and resumed["resolution_due_at"]

    solved = body(await client.patch(f"{API}/tickets/{created['id']}", headers=agent, json={"status": "solved"}))
    assert solved["status"] == "solved" and solved["allowed_statuses"] == ["closed", "open"]

    events = [e["type"] for e in body(await client.get(f"{API}/tickets/{created['id']}/events", headers=agent))]
    assert events[0] == "created" and "assigned" in events and "replied" in events and events[-1] == "status_changed"
    await jobs.run()


async def test_invalid_transition_is_409(
    client: AsyncClient, agent: dict[str, str], customer: dict[str, str], jobs: Jobs
) -> None:
    created = body(await client.post(f"{API}/tickets", headers=customer, json={"subject": "Quick question", "body": "Hi"}))
    response = await client.patch(f"{API}/tickets/{created['id']}", headers=agent, json={"status": "closed"})
    assert response.status_code == 409 and response.json()["error"]["code"] == "INVALID_TRANSITION"


async def test_bulk_assign(client: AsyncClient, agent: dict[str, str], lead: dict[str, str], jobs: Jobs) -> None:
    unassigned = body(await client.get(f"{API}/tickets?view=unassigned&limit=3", headers=agent))["items"]
    staff = body(await client.get(f"{API}/users/staff", headers=agent))
    sam = next(u for u in staff if u["email"] == "sam@acme.demo")
    result = body(
        await client.post(
            f"{API}/tickets/bulk", headers=lead, json={"ids": [t["id"] for t in unassigned], "assignee_id": sam["id"]}
        )
    )
    assert result["updated"] == len(unassigned)
    for t in unassigned:
        assert body(await client.get(f"{API}/tickets/{t['id']}", headers=agent))["assignee"]["id"] == sam["id"]


async def test_priority_change_recomputes_due_dates(
    client: AsyncClient, agent: dict[str, str], customer: dict[str, str], jobs: Jobs
) -> None:
    created = body(
        await client.post(f"{API}/tickets", headers=customer, json={"subject": "Low prio thing", "body": "x", "priority": "low"})
    )
    raised = body(await client.patch(f"{API}/tickets/{created['id']}", headers=agent, json={"priority": "urgent"}))
    assert raised["resolution_due_at"] < created["resolution_due_at"]


async def test_presigned_upload_and_download(
    client: AsyncClient, customer: dict[str, str], agent: dict[str, str], jobs: Jobs
) -> None:
    upload = body(
        await client.post(
            f"{API}/attachments",
            headers=customer,
            json={"filename": "error log.txt", "content_type": "text/plain", "size_bytes": 11},
        )
    )
    async with AsyncClient() as s3:
        put = await s3.put(upload["upload_url"], content=b"hello world", headers=upload["headers"])
        assert put.status_code == 200
    ticket = body(
        await client.post(
            f"{API}/tickets",
            headers=customer,
            json={"subject": "See attached", "body": "Log attached", "attachment_ids": [upload["id"]]},
        )
    )
    messages = body(await client.get(f"{API}/tickets/{ticket['id']}/messages", headers=agent))
    assert messages[0]["attachments"][0]["filename"] == "error log.txt"
    link = body(await client.get(f"{API}/attachments/{upload['id']}", headers=agent))["url"]
    async with AsyncClient() as s3:
        assert (await s3.get(link)).content == b"hello world"

    bad = await client.post(
        f"{API}/attachments",
        headers=customer,
        json={"filename": "x.exe", "content_type": "application/x-msdownload", "size_bytes": 5},
    )
    assert bad.status_code == 422
