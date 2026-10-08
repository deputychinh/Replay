"""Generate every Relay diagram as draw.io files (and PNGs with --png).

Run:  python3 docs/architecture/gen_diagrams.py [--png]      (or: npm run diagrams)
Out:  docs/architecture/*.drawio and *.png — see docs/plan.md §11.

Same conventions as real-estate/docs/architecture:
- data at the top of each function, layout by explicit coordinates, no hand edits of the output;
- numbered arrows match the flow tables in README.md;
- sequence diagrams: one lifeline per participant, steps 1 → n, solid = call, dashed = reply,
  loop = internal step, `opt [condition]` frames for branches.
Colours come from the Relay palette (frontend/packages/design-tokens/tokens.css).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

OUT_DIR = Path(__file__).resolve().parent

# Relay palette (tokens.css). Names kept short: TEAL = primary (indigo), OCHRE = accent (signal orange).
INK, TEAL, TEAL_SOFT, OCHRE, OCHRE_SOFT = "#111827", "#3730A3", "#E0E7FF", "#C2410C", "#FFEDD5"
PAPER, STONE, MUTED, WHITE = "#F7F8FA", "#E5E7EB", "#4B5563", "#FFFFFF"
GREEN, RED, AMBER, BLUE = "#15803D", "#B91C1C", "#A16207", "#0369A1"
SLATE = "#0F172A"

FONT = "fontFamily=Helvetica;"
F = 20          # body text
SMALL = 15      # technical line under a title
TITLE = 24      # column titles

BOX = ("rounded=1;whiteSpace=wrap;html=1;arcSize=6;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;"
       f"fontColor={INK};fontSize={F};spacing=8;verticalAlign=middle;" + FONT)
COLUMN = ("swimlane;horizontal=1;startSize=56;html=1;whiteSpace=wrap;collapsible=0;rounded=1;arcSize=2;"
          f"fillColor={{fill}};swimlaneFillColor={{fill}};strokeColor={STONE};fontSize={TITLE};fontStyle=1;"
          f"fontColor={INK};" + FONT)
EDGE = ("edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;html=1;endArrow=block;endFill=1;"
        f"strokeColor={INK};strokeWidth=1.5;fontSize={SMALL + 1};fontColor={INK};labelBackgroundColor={WHITE};" + FONT)
DASHED = EDGE + f"dashed=1;strokeColor={MUTED};"
NOTE = (f"text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize={SMALL};fontColor={MUTED};" + FONT)


def label(title: str, sub: str = "") -> str:
    text = f"<b>{escape(title)}</b>"
    if sub:
        text += f'<br><font style="font-size:{SMALL}px;color:{MUTED}">{sub}</font>'
    return text


class Diagram:
    def __init__(self, name: str, width: int, height: int):
        self.name, self.width, self.height = name, width, height
        self.cells: list[str] = []

    def vertex(self, cid: str, value: str, style: str, x: float, y: float, w: float, h: float) -> str:
        geo = f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
        self.cells.append(f'<mxCell id="{cid}" value={quoteattr(value)} style={quoteattr(style)} vertex="1" parent="1">{geo}</mxCell>')
        return cid

    def box(self, cid: str, title: str, sub: str, x: float, y: float, w: float, h: float,
            fill: str = WHITE, stroke: str = TEAL) -> str:
        return self.vertex(cid, label(title, sub), BOX.format(fill=fill, stroke=stroke), x, y, w, h)

    def edge(self, cid: str, source: str, target: str, text: str = "", style: str = EDGE,
             points: list[tuple[float, float]] | None = None, ports: str = "") -> None:
        pts = ""
        if points:
            pts = '<Array as="points">' + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points) + "</Array>"
        geo = f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry>'
        self.cells.append(f'<mxCell id="{cid}" value={quoteattr(escape(text))} style={quoteattr(style + ports)} edge="1" '
                          f'parent="1" source="{source}" target="{target}">{geo}</mxCell>')

    def free_edge(self, cid: str, x1: float, y1: float, x2: float, y2: float, text: str, style: str,
                  points: list[tuple[float, float]] | None = None) -> None:
        pts = ""
        if points:
            pts = '<Array as="points">' + "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points) + "</Array>"
        geo = (f'<mxGeometry relative="1" as="geometry"><mxPoint x="{x1}" y="{y1}" as="sourcePoint"/>'
               f'<mxPoint x="{x2}" y="{y2}" as="targetPoint"/>{pts}</mxGeometry>')
        self.cells.append(f'<mxCell id="{cid}" value={quoteattr(text)} style={quoteattr(style)} edge="1" parent="1">{geo}</mxCell>')

    def page(self) -> str:
        return (f'<diagram id={quoteattr(self.name)} name={quoteattr(self.name)}>'
                '<mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
                f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.width}" pageHeight="{self.height}" '
                f'background="{WHITE}" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
                + "".join(self.cells) + "</root></mxGraphModel></diagram>")


def mxfile(pages: list[Diagram]) -> str:
    return '<mxfile host="gen_diagrams.py" type="device">' + "".join(p.page() for p in pages) + "</mxfile>\n"


TABLE = ("swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;startSize=34;horizontalStack=0;resizeParent=1;"
         f"collapsible=0;html=1;rounded=1;arcSize=4;fillColor={TEAL};fontColor={WHITE};strokeColor={TEAL};"
         f"swimlaneFillColor={WHITE};fontSize=17;" + FONT)


def table(d: Diagram, cid: str, name: str, columns: list[str], x: float, y: float, w: float = 330) -> str:
    body = "<br>".join(escape(c) for c in columns)
    h = 34 + 21 * len(columns) + 16
    d.vertex(cid, name, TABLE, x, y, w, h)
    d.vertex(f"{cid}-cols", body, f"text;html=1;align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;fontSize=14;fontColor={INK};"
             "fontFamily=Courier New;", x, y + 34, w, h - 34)
    return cid


PX, TECH_PX, COL_W, LIFE_W, HEAD, GAP, FRAME_PAD = 19, 15, 290, 230, 90, 62, 26
LIFELINE = ("shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=1;dropTarget=0;collapsible=0;"
            f"recursiveResize=0;outlineConnect=0;portConstraint=eastwest;size={HEAD};fillColor={WHITE};strokeColor={TEAL};"
            f"fontColor={INK};fontSize={PX};" + FONT)
CALL = (f"html=1;verticalAlign=bottom;endArrow=block;endFill=1;strokeColor={INK};strokeWidth=1.5;fontSize={PX - 3};"
        f"fontColor={INK};labelBackgroundColor={WHITE};" + FONT)
REPLY = CALL.replace("endArrow=block;endFill=1;", "endArrow=open;endFill=0;") + f"dashed=1;strokeColor={MUTED};"
SELF = CALL + "edgeStyle=orthogonalEdgeStyle;align=left;labelPosition=right;spacingLeft=40;entryX=0;"
FRAME = (f"shape=umlFrame;whiteSpace=wrap;html=1;width={{w}};height=28;fontSize={PX - 4};fontStyle=1;strokeColor={OCHRE};"
         f"fontColor={OCHRE};" + FONT)


def sequence(name: str, participants: list[tuple[str, str, str]], steps: list[tuple[str, str, str, str]],
             frames: tuple[tuple[str, int, int, str, str], ...] = ()) -> Diagram:
    left, top = 20, 20
    starts = {f[1] for f in frames}
    after = {f[2] + 1 for f in frames}
    ys, y = [], top + HEAD + 50
    for n in range(1, len(steps) + 1):
        if n > 1:
            y += GAP + (FRAME_PAD if n in starts or n in after else 0)
        ys.append(y)
    height = ys[-1] + 50
    width = left * 2 + COL_W * (len(participants) - 1) + LIFE_W + 220
    d = Diagram(name, width, height + 20)
    xs: dict[str, float] = {}
    for i, (pid, title, tech) in enumerate(participants):
        x = left + i * COL_W
        xs[pid] = x + LIFE_W / 2
        d.vertex(f"ll-{pid}", f'<b>{escape(title)}</b><br><font style="font-size:{TECH_PX}px;color:{MUTED}">{escape(tech)}</font>',
                 LIFELINE, x, top, LIFE_W, height - top)
    for n, (kind, src, dst, text) in enumerate(steps, 1):
        text_label = f"{n}. {escape(text)}"
        yy = ys[n - 1]
        if kind == "self":
            d.free_edge(f"m{n}", xs[src], yy, xs[src] + 1, yy + 16, text_label, SELF,
                        points=[(xs[src] + 36, yy), (xs[src] + 36, yy + 16)])
        else:
            d.free_edge(f"m{n}", xs[src], yy, xs[dst], yy, text_label, REPLY if kind == "reply" else CALL)
    for i, (title, first, last, lp, rp) in enumerate(frames):
        fy = ys[first - 1] - 56
        fh = ys[last - 1] - ys[first - 1] + 76
        fx = min(xs[lp], xs[rp]) - LIFE_W / 2 + 4
        fr = max(xs[lp], xs[rp]) + LIFE_W / 2 - 4
        d.vertex(f"frame{i}", escape(title), FRAME.format(w=min(int(fr - fx) - 10, 11 * len(title) + 30)), fx, fy, fr - fx, fh)
    return d



AWS = {"compute": "#ED7100", "database": "#C925D1", "networking": "#8C4FFF", "storage": "#7AA116",
       "integration": "#E7157B", "security": "#DD344C", "management": "#E7157B"}


def aws_icon(d: Diagram, cid: str, res: str, category: str, title: str, sub: str, x: float, y: float, size: int = 64) -> str:
    style = ("sketch=0;outlineConnect=0;fontColor=#232F3E;strokeColor=#ffffff;dashed=0;verticalLabelPosition=bottom;"
             f"verticalAlign=top;align=center;html=1;fontSize={SMALL + 1};aspect=fixed;shape=mxgraph.aws4.resourceIcon;"
             f"resIcon=mxgraph.aws4.{res};fillColor={AWS[category]};" + FONT)
    return d.vertex(cid, label(title, sub), style, x, y, size, size)


GROUP = ("rounded=1;whiteSpace=wrap;html=1;arcSize=2;fillColor={fill};strokeColor={stroke};dashed={dashed};"
         f"verticalAlign=top;align=left;spacingLeft=12;spacingTop=6;fontSize={SMALL + 2};fontStyle=1;fontColor={INK};" + FONT)


def group(d: Diagram, cid: str, title: str, x: float, y: float, w: float, h: float, fill: str = "none", stroke: str = MUTED,
          dashed: int = 1) -> None:
    d.vertex(cid, title, GROUP.format(fill=fill, stroke=stroke, dashed=dashed), x, y, w, h)


# ───────────────────────── 1. AWS deployment ─────────────────────────

def aws_deployment() -> Diagram:
    d = Diagram("Relay — AWS deployment (us-east-1)", 2140, 1230)
    group(d, "cloud", "AWS Cloud · us-east-1", 300, 20, 1820, 1080, stroke="#232F3E", dashed=0)
    group(d, "vpc", "VPC · 2 Availability Zones", 640, 90, 1060, 990, stroke="#8C4FFF")
    group(d, "public", "Public subnets", 670, 140, 300, 300, fill="#E9F3E6", stroke="#7AA116")
    group(d, "app", "Private app subnets", 1000, 140, 670, 420, fill="#E6F2F8", stroke="#147EBA")
    group(d, "data", "Isolated data subnets (no internet route)", 1000, 600, 670, 450, fill="#F3E6F7", stroke="#C925D1")

    d.box("users", "Customers and agents", "browsers (React app)", 30, 200, 230, 100, stroke=INK)
    aws_icon(d, "cf", "cloudfront", "networking", "CloudFront", "one domain · TLS · CSP", 380, 210)
    aws_icon(d, "site", "s3", "storage", "S3 · web app", "static build, private (OAC)", 380, 470)
    aws_icon(d, "alb", "elastic_load_balancing", "networking", "Application LB", "403 unless X-Origin-Verify", 790, 230)
    aws_icon(d, "nat", "nat_gateway", "networking", "NAT gateway", "1 staging · 2 prod", 790, 350)
    aws_icon(d, "api", "fargate", "compute", "ECS Fargate · api", "migrate init → uvicorn · 2–6 tasks", 1080, 200)
    aws_icon(d, "worker", "fargate", "compute", "ECS Fargate · worker", "SQS consumer · scales on depth", 1430, 400)
    aws_icon(d, "rds", "rds", "database", "RDS PostgreSQL 16", "Multi-AZ (prod) · encrypted", 1080, 700)
    aws_icon(d, "redis", "elasticache", "database", "ElastiCache Redis", "cache · rate limits · pub/sub", 1430, 700)
    aws_icon(d, "sqs", "sqs", "integration", "SQS jobs + DLQ", "5 tries → dead letters", 1850, 200)
    aws_icon(d, "eb", "eventbridge", "integration", "EventBridge", "SLA scan 1 min · auto-close 1 h", 1850, 420)
    aws_icon(d, "files", "s3", "storage", "S3 · files", "presigned up/download · exports 7 d", 1850, 640)
    aws_icon(d, "ses", "simple_email_service", "integration", "SES", "notifications", 1850, 860)
    aws_icon(d, "secrets", "secrets_manager", "security", "Secrets Manager", "DB password · JWT key", 380, 720)
    aws_icon(d, "ecr", "ecr", "compute", "ECR", "backend image (one for both)", 380, 920)
    aws_icon(d, "cw", "cloudwatch_2", "management", "CloudWatch", "logs · dashboard · 6 alarms → SNS", 1080, 960)
    d.box("gh", "GitHub Actions", "OIDC role · build → ECR → cdk deploy", 30, 900, 230, 110, stroke=INK)

    def wire(cid: str, src: str, dst: str, text: str, style: str = EDGE, ports: str = "",
             points: list[tuple[float, float]] | None = None) -> None:
        d.edge(cid, src, dst, text, style=style, ports=ports, points=points)

    wire("e1", "users", "cf", "1", ports="exitX=1;exitY=0.4;entryX=0;entryY=0.5;")
    wire("e2", "cf", "site", "2", ports="exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    wire("e3", "cf", "alb", "3  /api/* + WebSocket", ports="exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
    wire("e4", "alb", "api", "4", ports="exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
    wire("e5", "api", "rds", "5", ports="exitX=0.25;exitY=1;entryX=0.25;entryY=0;")
    wire("e6", "api", "redis", "6", ports="exitX=0.75;exitY=1;entryX=0.5;entryY=0;", points=[(1128, 640), (1462, 640)])
    wire("e7", "api", "sqs", "7  jobs", ports="exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
    wire("e8", "eb", "sqs", "8", ports="exitX=0.5;exitY=0;entryX=0.5;entryY=1;")
    wire("e9", "sqs", "worker", "9", ports="exitX=0;exitY=0.8;entryX=1;entryY=0.3;", points=[(1700, 251), (1700, 419)])
    wire("e10", "worker", "files", "10", DASHED, ports="exitX=1;exitY=0.6;entryX=0;entryY=0.5;", points=[(1760, 438), (1760, 672)])
    wire("e11", "worker", "ses", "11", DASHED, ports="exitX=1;exitY=0.9;entryX=0;entryY=0.5;", points=[(1800, 458), (1800, 892)])
    wire("e12", "worker", "rds", "", DASHED, ports="exitX=0;exitY=0.5;entryX=1;entryY=0.5;", points=[(1250, 432), (1250, 732)])
    wire("e13", "users", "files", "12  presigned PUT / GET", DASHED, ports="exitX=0.5;exitY=1;entryX=1;entryY=0.5;",
         points=[(145, 1070), (2090, 1070), (2090, 672)])
    wire("e14", "gh", "ecr", "13", DASHED, ports="exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
    wire("e15", "secrets", "api", "secrets", DASHED, ports="exitX=1;exitY=0.5;entryX=0;entryY=1;", points=[(590, 752), (590, 540), (1080, 540)])
    d.vertex("legend", "<b>1</b> one HTTPS domain · <b>2</b> static app · <b>3</b> /api/* and the WebSocket go to the ALB with a secret header · "
             "<b>4</b> API tasks · <b>5</b> SQL as the tenant-scoped app · <b>6</b> cache, rate limits, pub/sub between tasks · <b>7</b> slow work queued · "
             "<b>8</b> schedules · <b>9</b> worker · <b>10</b> CSV exports · <b>11</b> email · <b>12</b> files never pass through the API · "
             "<b>13</b> deploy with short-lived credentials", NOTE.replace(f"fontColor={MUTED}", f"fontColor={INK}") + "fontSize=16;",
             30, 1120, 2080, 70)
    return d


# ───────────────────────── 2. Logical architecture ─────────────────────────

def architecture() -> Diagram:
    d = Diagram("Relay — logical architecture", 1900, 910)
    for cid, text, x, w, fill in [("c1", "Browser", 20, 360, PAPER), ("c2", "API (FastAPI, stateless)", 420, 620, TEAL_SOFT),
                                  ("c3", "Background (worker)", 1080, 380, OCHRE_SOFT), ("c4", "State", 1500, 380, PAPER)]:
        d.vertex(cid, text, COLUMN.format(fill=fill), x, 20, w, 830)
    d.box("console", "React console (/console)", "agents & leads · virtualised inbox<br>TanStack Query cache · WebSocket", 50, 110, 300, 120)
    d.box("portal", "React portal (/portal/:org)", "customers · own tickets only", 50, 290, 300, 100)
    d.box("client", "@relay/api-client", "types + enums generated from OpenAPI", 50, 450, 300, 90, fill=PAPER, stroke=STONE)
    d.box("tokens", "@relay/design-tokens", "one palette · BEM blocks", 50, 580, 300, 90, fill=PAPER, stroke=STONE)
    d.box("routers", "Routers /api/v1", "auth · tickets · messages · attachments<br>sla-policies · reports · notifications", 450, 110, 560, 110)
    d.box("services", "Services (rules)", "TicketService · MessageService · AuthService<br>SLA engine (pure functions) · Notifier", 450, 270, 560, 110, stroke=OCHRE)
    d.box("repos", "Repositories (TenantRepository)", "every query filtered by org_id · keyset pages", 450, 430, 560, 100)
    d.box("uow", "Unit of Work", "commit, then publish events and queue jobs", 450, 580, 260, 100, fill=PAPER, stroke=STONE)
    d.box("ws", "WebSocket hub", "Redis pub/sub → sockets of the org", 750, 580, 260, 100, fill=PAPER, stroke=STONE)
    d.box("worker", "Worker", "claim idempotency key → handler<br>→ commit → delete message", 1110, 110, 320, 120)
    d.box("jobs", "Jobs", "auto_assign · sla_scan · auto_close<br>export_csv · send_email", 1110, 290, 320, 110)
    d.box("pg", "PostgreSQL", "tickets · messages · SLA dates · audit", 1530, 110, 320, 100, stroke=OCHRE)
    d.box("redis", "Redis", "cache · rate limit · pub/sub", 1530, 270, 320, 90, stroke=OCHRE)
    d.box("sqs", "SQS + DLQ", "LocalStack locally", 1530, 420, 320, 90, stroke=OCHRE)
    d.box("s3", "S3", "attachments · exports", 1530, 570, 320, 90, stroke=OCHRE)
    d.box("mail", "Email", "SES · Mailpit locally", 1530, 720, 320, 90, stroke=OCHRE)
    def wire(cid: str, src: str, dst: str, text: str, ports: str, points: list[tuple[float, float]] | None = None,
             style: str = EDGE) -> None:
        d.edge(cid, src, dst, text, style=style, ports=ports, points=points)

    wire("a1", "console", "routers", "REST + Bearer", "exitX=1;exitY=0.4;entryX=0;entryY=0.4;")
    wire("a2", "portal", "routers", "", "exitX=1;exitY=0.5;entryX=0;entryY=0.8;", [(400, 340), (400, 198)])
    wire("a3", "routers", "services", "", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    wire("a4", "services", "repos", "", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    wire("a5", "repos", "pg", "SQL", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", [(1475, 480), (1475, 160)])
    wire("a6", "services", "uow", "", "exitX=0;exitY=0.8;entryX=0;entryY=0.5;", [(432, 358), (432, 630)])
    wire("a7", "uow", "sqs", "after commit: queue jobs", "exitX=0.5;exitY=1;entryX=0;entryY=0.5;", [(580, 770), (1495, 770), (1495, 465)])
    wire("a8", "ws", "redis", "pub/sub", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", [(1485, 630), (1485, 315)])
    wire("a9", "ws", "console", "live events", "exitX=0.5;exitY=1;entryX=0;entryY=0.5;", [(880, 830), (30, 830), (30, 170)], DASHED)
    wire("a10", "worker", "jobs", "", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    wire("a11", "sqs", "jobs", "receive", "exitX=0;exitY=0.8;entryX=0.5;entryY=1;", [(1270, 492)])
    wire("a12", "jobs", "s3", "exports", "exitX=0.8;exitY=1;entryX=0;entryY=0.5;", [(1366, 615)])
    wire("a13", "jobs", "mail", "email", "exitX=0.95;exitY=1;entryX=0;entryY=0.5;", [(1414, 765)])
    d.vertex("arch-note", "Files go browser ↔ S3 with presigned URLs (never through the API). Redis also holds the dashboard cache and rate limits.",
             NOTE, 30, 860, 1800, 30)
    return d


# ───────────────────────── 3. ERD ─────────────────────────

def erd() -> Diagram:
    d = Diagram("Relay — data model", 1880, 1060)
    table(d, "orgs", "organizations", ["PK id", "name · slug UNIQUE", "ticket_seq", "brand_color"], 40, 40)
    table(d, "users", "users", ["PK id · FK org_id", "email (UNIQUE per org)", "full_name · company", "role  role", "password_hash (bcrypt)", "is_active"], 480, 40)
    table(d, "tokens", "refresh_tokens", ["PK id · FK user_id", "family_id", "token_hash UNIQUE", "expires_at · revoked_at"], 920, 40)
    table(d, "teams", "teams / team_members", ["PK id · FK org_id", "name · is_default", "last_assigned_user_id (round robin)", "members: (team_id, user_id)"], 1360, 40, 380)
    table(d, "cal", "business_calendars / holidays", ["PK org_id", "timezone", "weekly_hours jsonb", "holidays: (org_id, day) UNIQUE"], 40, 330)
    table(d, "sla", "sla_policies", ["PK id · FK org_id", "priority (UNIQUE per org)", "first_response_minutes", "resolution_minutes"], 40, 560)
    table(d, "tickets", "tickets", ["PK id · FK org_id", "number (UNIQUE per org)", "subject · status · priority · channel", "FK requester_id · FK assignee_id · FK team_id",
                                    "tags text[]", "sla_state", "first_response_due_at · resolution_due_at", "first_responded_at · solved_at",
                                    "resolution_remaining_minutes (paused)", "sla_due_at  GENERATED", "search tsvector GENERATED (GIN)"], 480, 330, 440)
    table(d, "messages", "messages", ["PK id · FK org_id · FK ticket_id", "FK author_id", "kind  public_reply | internal_note", "body"], 1000, 330, 380)
    table(d, "files", "attachments", ["PK id · FK org_id", "FK ticket_id · FK message_id", "s3_key UNIQUE", "filename · content_type · size"], 1000, 560, 380)
    table(d, "events", "ticket_events (audit)", ["PK id · FK org_id · FK ticket_id", "FK actor_id NULL = system", "type · data jsonb"], 480, 800, 440)
    table(d, "notes", "notifications", ["PK id · FK org_id · FK user_id", "kind · message · read_at"], 1000, 800, 380)
    table(d, "exports", "exports", ["PK id · FK org_id", "from_date · to_date · status", "s3_key · row_count"], 1460, 330, 380)
    table(d, "jobs", "processed_jobs", ["PK key (idempotency)", "processed_at"], 1460, 560, 380)
    rel = EDGE + "endArrow=ERmany;startArrow=ERone;endFill=0;startFill=0;"
    for cid, s, t, ports in [("r1", "orgs", "users", "exitX=1;exitY=0.4;entryX=0;entryY=0.4;"), ("r2", "users", "tokens", "exitX=1;exitY=0.4;entryX=0;entryY=0.4;"),
                             ("r3", "users", "tickets", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"), ("r4", "tickets", "messages", "exitX=1;exitY=0.2;entryX=0;entryY=0.3;"),
                             ("r5", "messages", "files", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"), ("r6", "tickets", "events", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"),
                             ("r7", "orgs", "cal", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;"), ("r8", "cal", "sla", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")]:
        d.edge(cid, s, t, "", style=rel, ports=ports)
    d.vertex("note", "Every table except organizations, refresh_tokens and processed_jobs has org_id and is read only through TenantRepository.scoped(). "
             "Indexes per list order: (org, updated_at desc, id), (org, priority desc, updated_at desc, id), (org, sla_due_at, id) partial, "
             "unassigned-open partial, (org, assignee, status), GIN on search.", NOTE, 40, 990, 1800, 60)
    return d


# ───────────────────────── 4. Ticket lifecycle + SLA clock ─────────────────────────

def lifecycle() -> Diagram:
    d = Diagram("Relay — ticket status and SLA clock", 1700, 760)
    state = ("ellipse;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};strokeWidth=2;fontSize=18;fontStyle=1;"
             f"fontColor={INK};" + FONT)
    for cid, name, x, y, fill, stroke in [
        ("new", "NEW<br><font style='font-size:13px'>clock running</font>", 40, 240, "#E0F2FE", BLUE),
        ("open", "OPEN", 340, 240, TEAL_SOFT, TEAL),
        ("pending", "PENDING<br>CUSTOMER<br><font style='font-size:13px'>clock paused</font>", 680, 60, "#FEF3C7", AMBER),
        ("hold", "ON HOLD<br><font style='font-size:13px'>clock running</font>", 680, 420, "#FEF3C7", AMBER),
        ("solved", "SOLVED<br><font style='font-size:13px'>met / breached</font>", 1040, 240, "#DCFCE7", GREEN),
        ("closed", "CLOSED<br><font style='font-size:13px'>final</font>", 1380, 240, PAPER, MUTED),
    ]:
        d.vertex(cid, name, state.format(fill=fill, stroke=stroke), x, y, 220, 120)
    for cid, s, t, text in [("t1", "new", "open", "assigned / agent replies"), ("t2", "open", "pending", "agent replies (default)"),
                            ("t3", "pending", "open", "customer replies (resume clock)"), ("t4", "open", "hold", "waiting on a third party"),
                            ("t5", "hold", "open", ""), ("t6", "open", "solved", "solved"), ("t7", "pending", "solved", ""),
                            ("t8", "solved", "open", "customer replies (reopen)"), ("t9", "solved", "closed", "4 days later (auto-close job)")]:
        d.edge(cid, s, t, text)
    d.vertex("note", "SLA targets per priority are business minutes (team calendar, time zone, holidays). Pausing stores the minutes left; resuming "
             "computes a new due time from them. Every minute the scan warns once 30 min before a deadline and flags a breach once. "
             "The rules live in backend/app/modules/tickets/rules.py (TICKET_TRANSITIONS) and app/sla/.", NOTE, 40, 620, 1620, 70)
    return d


# ───────────────────────── 5. Business flows ─────────────────────────

CUSTOMER = ("cust", "Customer", "React portal")
AGENT = ("agent", "Agent", "React console")
API = ("api", "API", "FastAPI task")
PG = ("pg", "Postgres", "RDS")
REDIS = ("redis", "Redis", "ElastiCache")
SQS = ("sqs", "SQS", "jobs + DLQ")
WORKER = ("worker", "Worker", "ECS task")
S3 = ("s3", "S3", "files")
EB = ("eb", "EventBridge", "schedules")


def flows() -> list[Diagram]:
    return [
        sequence("B1 Sign in and refresh (FR-01, NFR-04)", [AGENT, API, REDIS, PG], [
            ("call", "agent", "api", "POST /auth/login"),
            ("call", "api", "redis", "rate limit: 10 / min per IP + email"),
            ("reply", "api", "agent", "429 + Retry-After"),
            ("call", "api", "pg", "user by (org, email) · bcrypt check"),
            ("call", "api", "pg", "store refresh token hash (new family)"),
            ("reply", "api", "agent", "access JWT (15 min) + httpOnly refresh cookie"),
            ("call", "agent", "api", "POST /auth/refresh (cookie)"),
            ("call", "api", "pg", "revoke old token · issue next in family"),
            ("reply", "pg", "api", "token already revoked = stolen"),
            ("call", "api", "pg", "revoke the whole family"),
            ("reply", "api", "agent", "401 → sign in again"),
        ], frames=(("opt [too many attempts]", 3, 3, "agent", "api"), ("opt [refresh token reused]", 9, 11, "agent", "pg"))),
        sequence("B2 Customer opens a ticket (FR-03, FR-08, FR-10)", [CUSTOMER, API, S3, PG, SQS, WORKER], [
            ("call", "cust", "api", "POST /attachments (name, type, size)"),
            ("reply", "api", "cust", "presigned PUT URL"),
            ("call", "cust", "s3", "PUT file (never through the API)"),
            ("call", "cust", "api", "POST /tickets {subject, body, priority, attachment_ids}"),
            ("call", "api", "pg", "number · SLA due dates (business hours) · message · audit — one transaction"),
            ("call", "api", "sqs", "after commit: auto_assign job"),
            ("reply", "api", "cust", "201 ticket"),
            ("call", "sqs", "worker", "auto_assign"),
            ("call", "worker", "pg", "lock team row · round robin · assign · notify"),
        ]),
        sequence("B3 Agent replies (FR-04, FR-07, FR-11)", [AGENT, API, PG, REDIS, SQS], [
            ("call", "agent", "api", "POST /tickets/{id}/messages {body, status_after}"),
            ("self", "api", "api", "first response time recorded"),
            ("self", "api", "api", "pending_customer → pause clock, store minutes left"),
            ("call", "api", "pg", "message · status · audit — one transaction"),
            ("call", "api", "redis", "after commit: publish ticket.reply_added"),
            ("call", "api", "sqs", "after commit: send_email to the customer"),
            ("reply", "api", "agent", "201 message"),
        ]),
        sequence("B4 Real-time fan-out across API tasks (FR-07, NFR-02)", [AGENT, ("api1", "API task A", "has the request"), REDIS,
                                                                             ("api2", "API task B", "holds other sockets"), ("agent2", "Other agent", "console")], [
            ("call", "agent2", "api2", "WS /api/v1/ws · first message = token"),
            ("reply", "api2", "agent2", "ready"),
            ("call", "agent", "api1", "PATCH /tickets/{id}"),
            ("call", "api1", "redis", "PUBLISH relay:events {org, event}"),
            ("call", "redis", "api2", "message on the channel"),
            ("self", "api2", "api2", "only sockets of that org (and user, if targeted)"),
            ("reply", "api2", "agent2", "ticket.updated → refetch"),
        ]),
        sequence("B5 SLA scan and breach (FR-08, FR-09)", [EB, SQS, WORKER, PG, REDIS], [
            ("call", "eb", "sqs", "every minute: {type: sla_scan, key: sla_scan:<time>}"),
            ("call", "sqs", "worker", "receive"),
            ("call", "worker", "pg", "INSERT processed_jobs(key) ON CONFLICT DO NOTHING"),
            ("reply", "pg", "worker", "already done → skip, delete message"),
            ("call", "worker", "pg", "due soon, not warned (FOR UPDATE SKIP LOCKED) → warn once"),
            ("call", "worker", "pg", "overdue and active → BREACHED · audit · notify assignee + leads"),
            ("call", "worker", "redis", "after commit: ticket.sla_breached"),
        ], frames=(("opt [duplicate delivery]", 4, 4, "worker", "pg"),)),
        sequence("B6 CSV export (FR-13)", [AGENT, API, SQS, WORKER, PG, S3], [
            ("call", "agent", "api", "POST /reports/exports {from, to}"),
            ("call", "api", "pg", "export row (pending)"),
            ("call", "api", "sqs", "after commit: export_csv"),
            ("reply", "api", "agent", "202 Accepted + id"),
            ("call", "sqs", "worker", "export_csv"),
            ("call", "worker", "pg", "stream rows (1,000 at a time)"),
            ("call", "worker", "s3", "PUT exports/<org>/<id>.csv (deleted after 7 days)"),
            ("call", "worker", "pg", "ready · notification"),
            ("call", "agent", "api", "GET /reports/exports/{id}"),
            ("reply", "api", "agent", "presigned download URL"),
        ]),
        sequence("B7 Tenant isolation (FR-02)", [("other", "Agent of org B", "console"), API, PG], [
            ("call", "other", "api", "GET /tickets/{id of org A}"),
            ("self", "api", "api", "org_id comes from the JWT, never from the request"),
            ("call", "api", "pg", "SELECT … WHERE org_id = :B AND id = :id"),
            ("reply", "pg", "api", "no row"),
            ("reply", "api", "other", "404 NOT_FOUND (not 403: nothing leaks)"),
        ]),
    ]


FILES: list[tuple[str, list[Diagram], list[str]]] = []


def build() -> None:
    FILES.extend([
        ("aws_deployment.drawio", [aws_deployment()], ["aws_deployment.png"]),
        ("architecture.drawio", [architecture()], ["architecture.png"]),
        ("erd.drawio", [erd()], ["erd.png"]),
        ("ticket_lifecycle.drawio", [lifecycle()], ["ticket_lifecycle.png"]),
        ("business_flows.drawio", flows(), ["flow_b1_sign_in.png", "flow_b2_open_ticket.png", "flow_b3_agent_reply.png",
                                            "flow_b4_realtime.png", "flow_b5_sla_scan.png", "flow_b6_csv_export.png", "flow_b7_tenant_isolation.png"]),
    ])
    for name, pages, pngs in FILES:
        assert len(pages) == len(pngs), name
        (OUT_DIR / name).write_text(mxfile(pages), encoding="utf-8")
        print("wrote", name)


def export_png() -> None:
    """Export every page with draw.io desktop (brew install --cask drawio)."""
    for name, _, pngs in FILES:
        for index, png in enumerate(pngs, 1):
            subprocess.run(["drawio", "--export", "--format", "png", "--scale", "2", "--border", "20", "--page-index", str(index),
                            "-o", str(OUT_DIR / png), str(OUT_DIR / name)], check=True, capture_output=True)
            print("exported", png)


if __name__ == "__main__":
    build()
    if "--png" in sys.argv:
        export_png()
