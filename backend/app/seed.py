"""Demo data.

  python -m app.seed            # 2 organisations, 5,000 tickets with threads
  python -m app.seed --large    # + 1,000,000 extra tickets for the performance check (NFR-01)

Accounts (password Demo@1234), organisation "acme":
  lead@acme.demo (owner) · agent@acme.demo, sam@acme.demo, rio@acme.demo (agents) · customer@globex.demo (customer)
A second organisation "initech" exists only to prove tenant isolation.
"""

import asyncio
import random
import sys
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import insert, text

from app.common.enums import MessageKind, Role, SlaState, TicketEventType, TicketPriority, TicketStatus
from app.core.security import hash_password
from app.db.session import SessionFactory, engine
from app.modules.canned_replies.models import CannedReply
from app.modules.messages.models import Message
from app.modules.organizations.models import BusinessCalendar, Holiday, Organization
from app.modules.sla_policies.models import SlaPolicy
from app.modules.sla_policies.repository import FALLBACK_TARGETS
from app.modules.teams.models import Team, TeamMember
from app.modules.tickets.models import Ticket, TicketEvent
from app.modules.users.models import User
from app.sla.calendar import DEFAULT_WEEKLY_HOURS
from app.sla.calendar import BusinessCalendar as Calendar
from app.sla.clock import due_at

PASSWORD = "Demo@1234"
TICKETS = 5000
LARGE_TICKETS = 1_000_000
rng = random.Random(42)

SUBJECTS = [
    "Cannot sign in after password reset",
    "Invoice shows the wrong VAT number",
    "API returns 502 on /v2/orders",
    "Export to CSV is missing columns",
    "Webhook deliveries are delayed",
    "How do I add a teammate?",
    "Dashboard charts load slowly",
    "SSO login loops back to the start page",
    "Refund request for duplicate charge",
    "Mobile app crashes on Android 15",
    "Rate limit too low for our integration",
    "Data import stuck at 80 %",
    "Two-factor codes not arriving by SMS",
    "Feature request: dark mode",
    "Billing address change",
    "Search does not find archived projects",
    "Email notifications go to spam",
    "Upgrade from Starter to Pro",
]
BODIES = [
    "Hi team, this started this morning and blocks our work. Could you take a look?",
    "Steps: 1) open the page 2) click export 3) nothing happens. Screenshot attached later.",
    "We need this fixed before our board meeting on Friday. Thanks!",
    "Not urgent, but it would help us a lot. Happy to jump on a call.",
]
REPLIES = [
    "Thanks for the details. I can reproduce it and I've escalated it to engineering.",
    "Could you send the request id from the error message? That helps us trace it.",
    "Good news: a fix is deployed. Can you confirm it works on your side?",
    "I've updated your account. Let me know if anything else looks off.",
]
COMPANIES = ["Globex", "Initrode", "Umbrella", "Hooli", "Soylent", "Stark Industries", "Wayne Enterprises", "Wonka"]
FIRST = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Quinn", "Drew", "Parker", "Reese"]
LAST = ["Smith", "Johnson", "Lee", "Garcia", "Brown", "Davis", "Martinez", "Clark", "Lewis", "Walker", "Young", "King"]


async def reset() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE organizations, processed_jobs RESTART IDENTITY CASCADE"))


def calendar() -> Calendar:
    return Calendar.from_settings("America/New_York", DEFAULT_WEEKLY_HOURS, {date(2026, 11, 26), date(2026, 12, 25)})


async def seed_org(name: str, slug: str, staff: list[tuple[str, str, Role]], customers: int, tickets: int) -> None:
    password_hash = hash_password(PASSWORD)
    async with SessionFactory() as s:
        org = Organization(name=name, slug=slug, brand_color="#3730A3")
        s.add(org)
        await s.flush()
        s.add(BusinessCalendar(org_id=org.id, timezone="America/New_York", weekly_hours=DEFAULT_WEEKLY_HOURS))
        for day, holiday in [(date(2026, 11, 26), "Thanksgiving"), (date(2026, 12, 25), "Christmas Day")]:
            s.add(Holiday(org_id=org.id, day=day, name=holiday))
        for priority, targets in FALLBACK_TARGETS.items():
            s.add(
                SlaPolicy(
                    org_id=org.id,
                    priority=priority,
                    first_response_minutes=targets.first_response_minutes,
                    resolution_minutes=targets.resolution_minutes,
                )
            )
        support = Team(org_id=org.id, name="Support", is_default=True)
        billing = Team(org_id=org.id, name="Billing")
        s.add_all([support, billing])

        agents = [
            User(org_id=org.id, email=email, full_name=full, role=role, password_hash=password_hash)
            for email, full, role in staff
        ]
        people = [
            User(
                org_id=org.id,
                email=f"customer@{COMPANIES[0].lower()}.demo"
                if i == 0
                else f"{FIRST[i % len(FIRST)].lower()}.{LAST[i % len(LAST)].lower()}{i}@{COMPANIES[i % len(COMPANIES)].lower()}.demo",
                full_name="Dana Whitfield" if i == 0 else f"{FIRST[i % len(FIRST)]} {LAST[(i * 7) % len(LAST)]}",
                company=COMPANIES[i % len(COMPANIES)],
                role=Role.CUSTOMER,
                password_hash=password_hash,
            )
            for i in range(customers)
        ]
        s.add_all(agents + people)
        await s.flush()
        for agent in agents:
            s.add(TeamMember(org_id=org.id, team_id=support.id, user_id=agent.id))
        s.add_all(
            [
                CannedReply(
                    org_id=org.id,
                    title="Ask for request id",
                    body="Hi {{customer.name}}, could you share the request id shown in the error? — {{agent.name}}",
                ),
                CannedReply(
                    org_id=org.id,
                    title="Fix deployed",
                    body="Good news {{customer.name}}: the fix for #{{ticket.number}} is live. Can you confirm?",
                ),
                CannedReply(
                    org_id=org.id, title="Closing note", body="I'll mark this as solved. Just reply if anything comes up again."
                ),
            ]
        )
        await s.flush()
        await _seed_tickets(s, org, agents, people, support.id, tickets)
        org.ticket_seq = tickets
        await s.commit()


async def _seed_tickets(s, org: Organization, agents: list[User], people: list[User], team_id: uuid.UUID, count: int) -> None:  # type: ignore[no-untyped-def]
    cal, now = calendar(), datetime.now(UTC)
    tickets, messages, events = [], [], []
    statuses = (
        [TicketStatus.NEW] * 4
        + [TicketStatus.OPEN] * 10
        + [TicketStatus.PENDING_CUSTOMER] * 6
        + [TicketStatus.ON_HOLD] * 2
        + [TicketStatus.SOLVED] * 18
        + [TicketStatus.CLOSED] * 60
    )
    priorities = [TicketPriority.LOW] * 2 + [TicketPriority.NORMAL] * 5 + [TicketPriority.HIGH] * 2 + [TicketPriority.URGENT]
    for n in range(1, count + 1):
        # Older tickets are mostly closed; the last few days hold the open queue.
        age_minutes = int((count - n) / count * 60 * 24 * 60) + rng.randint(0, 300)
        created = now - timedelta(minutes=age_minutes)
        # The open queue is the last three days; everything older has been answered and solved.
        status = rng.choice(statuses[22:]) if age_minutes > 60 * 24 * 3 else rng.choice(statuses[:40])
        priority = rng.choice(priorities)
        targets = FALLBACK_TARGETS[priority]
        fr_due, res_due = due_at(created, targets.first_response_minutes, cal), due_at(created, targets.resolution_minutes, cal)
        requester = people[0] if n % 40 == 0 else rng.choice(people)
        assignee = None if status == TicketStatus.NEW else rng.choice(agents)
        responded = (
            None
            if status == TicketStatus.NEW
            else created + timedelta(minutes=rng.randint(5, int(targets.first_response_minutes * 1.6)))
        )
        solved = (
            responded + timedelta(hours=rng.randint(1, 40))
            if responded and status in {TicketStatus.SOLVED, TicketStatus.CLOSED}
            else None
        )
        # Nothing in the demo happens in the future.
        if responded:
            responded = min(responded, now - timedelta(minutes=rng.randint(1, 30)))
        if solved:
            solved = min(solved, now - timedelta(minutes=rng.randint(1, 20)))
            if responded and solved < responded:
                solved = responded + timedelta(minutes=1)
        late = (responded and responded > fr_due) or (solved and solved > res_due) or (not solved and now > res_due)
        sla_state = SlaState.BREACHED if late else SlaState.MET if solved else SlaState.ACTIVE
        if status == TicketStatus.PENDING_CUSTOMER and not late:
            sla_state = SlaState.PAUSED
        tid = uuid.uuid4()
        updated = max(x for x in (created, responded, solved) if x)
        tickets.append(
            {
                "id": tid,
                "org_id": org.id,
                "number": n,
                "subject": rng.choice(SUBJECTS),
                "status": status,
                "priority": priority,
                "requester_id": requester.id,
                "assignee_id": assignee.id if assignee else None,
                "team_id": team_id,
                "tags": rng.sample(["billing", "api", "login", "bug", "question", "vip"], k=rng.randint(0, 2)),
                "sla_state": sla_state,
                "first_response_due_at": fr_due,
                "resolution_due_at": None if sla_state == SlaState.PAUSED else res_due,
                "resolution_remaining_minutes": 600 if sla_state == SlaState.PAUSED else None,
                "first_responded_at": responded,
                "solved_at": solved,
                "created_at": created,
                "updated_at": updated,
            }
        )
        messages.append(
            {
                "id": uuid.uuid4(),
                "org_id": org.id,
                "ticket_id": tid,
                "author_id": requester.id,
                "kind": MessageKind.PUBLIC_REPLY,
                "body": rng.choice(BODIES),
                "created_at": created,
            }
        )
        events.append(
            {
                "id": uuid.uuid4(),
                "org_id": org.id,
                "ticket_id": tid,
                "actor_id": requester.id,
                "type": TicketEventType.CREATED,
                "data": {},
                "created_at": created,
            }
        )
        if responded and assignee:
            messages.append(
                {
                    "id": uuid.uuid4(),
                    "org_id": org.id,
                    "ticket_id": tid,
                    "author_id": assignee.id,
                    "kind": MessageKind.PUBLIC_REPLY,
                    "body": rng.choice(REPLIES),
                    "created_at": responded,
                }
            )
            if n % 5 == 0:
                messages.append(
                    {
                        "id": uuid.uuid4(),
                        "org_id": org.id,
                        "ticket_id": tid,
                        "author_id": assignee.id,
                        "kind": MessageKind.INTERNAL_NOTE,
                        "body": "Checked the logs, looks like the edge cache. Watching.",
                        "created_at": responded + timedelta(minutes=3),
                    }
                )
            events.append(
                {
                    "id": uuid.uuid4(),
                    "org_id": org.id,
                    "ticket_id": tid,
                    "actor_id": assignee.id,
                    "type": TicketEventType.REPLIED,
                    "data": {},
                    "created_at": responded,
                }
            )
    for table, rows in ((Ticket, tickets), (Message, messages), (TicketEvent, events)):
        for i in range(0, len(rows), 2000):
            await s.execute(insert(table), rows[i : i + 2000])


async def seed_large(slug: str = "acme") -> None:
    """One million extra tickets, generated inside Postgres (seconds, not minutes)."""
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            INSERT INTO tickets (id, org_id, number, subject, status, priority, channel, requester_id, team_id, tags,
                                 sla_state, created_at, updated_at)
            SELECT gen_random_uuid(), o.id, o.ticket_seq + g,
                   'Load test ticket ' || g,
                   (ARRAY['closed','closed','closed','solved','open','pending_customer'])[1 + g % 6]::ticket_status,
                   (ARRAY['low','normal','normal','high','urgent'])[1 + g % 5]::ticket_priority,
                   'portal', u.id, NULL, '{}', 'met',
                   now() - (g || ' minutes')::interval, now() - (g || ' minutes')::interval
            FROM organizations o
            JOIN LATERAL (SELECT id FROM users WHERE org_id = o.id AND role = 'customer' LIMIT 1) u ON true
            CROSS JOIN generate_series(1, :n) g
            WHERE o.slug = :slug
        """),
            {"n": LARGE_TICKETS, "slug": slug},
        )
        await conn.execute(
            text("UPDATE organizations SET ticket_seq = ticket_seq + :n WHERE slug = :slug"), {"n": LARGE_TICKETS, "slug": slug}
        )
        await conn.execute(text("ANALYZE tickets"))


async def main() -> None:
    await reset()
    await seed_org(
        "Acme Cloud",
        "acme",
        [
            ("lead@acme.demo", "Morgan Reyes", Role.OWNER),
            ("agent@acme.demo", "Priya Natarajan", Role.AGENT),
            ("sam@acme.demo", "Sam Okafor", Role.AGENT),
            ("rio@acme.demo", "Rio Tanaka", Role.AGENT),
        ],
        customers=120,
        tickets=TICKETS,
    )
    await seed_org("Initech", "initech", [("lead@initech.demo", "Bill Lumbergh", Role.OWNER)], customers=5, tickets=20)
    if "--large" in sys.argv:
        await seed_large()
    await engine.dispose()
    print(f"seeded: acme ({TICKETS} tickets{' + 1M' if '--large' in sys.argv else ''}), initech (20 tickets)")


if __name__ == "__main__":
    asyncio.run(main())
