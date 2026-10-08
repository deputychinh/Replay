# ADR-0006: ECS Fargate behind one CloudFront domain, defined with CDK in Python

**Status:** accepted · 2026-10-08 (designed and synthesized; not deployed, by decision)

## Context
The API keeps WebSocket connections and database pools open, and needs the same image locally and in AWS. The team writes Python.

## Decision
- ECS Fargate runs the API (2–6 tasks) and the worker (scaled on queue depth) from one image, with different commands.
- A single CloudFront domain serves the React app from S3 and sends `/api/*` (including the WebSocket) to the ALB. The browser sees one origin, so the httpOnly refresh cookie and the WebSocket need no CORS.
- The ALB answers 403 unless CloudFront's secret header is present.
- Migrations run in a non-essential init container before the API container (`dependsOn: SUCCESS`). An advisory lock in `alembic/env.py` makes parallel tasks wait for each other.
- Data stores (RDS, ElastiCache) sit in isolated subnets with no internet route. Secrets come from Secrets Manager. Deploys use GitHub OIDC, with no stored keys.
- CDK in Python, six stacks, with assertion tests for the security rules. Locally, LocalStack (SQS, S3) and Mailpit (SES) stand in for AWS.

## Alternatives
- Lambda + API Gateway: WebSockets and connection pools are harder, and cold starts are worse.
- EKS: too much to operate for this size.
- Terraform: equally valid. CDK keeps infrastructure in the backend's language and allows unit tests.

## Consequences
- Staging costs about USD 110–120 a month (the NAT gateway is the biggest item). A budget alarm is part of the stack.
- CloudFront to ALB is plain HTTP inside AWS until a custom domain and ACM certificate are added; the code comments say where.
