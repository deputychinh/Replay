Architecture diagrams

Every diagram comes from `gen_diagrams.py`; edit that script, not the .drawio files. To regenerate the files and their PNGs, run `make diagrams`, which needs draw.io desktop.

- `aws_deployment.drawio`: the AWS deployment with official icons (CloudFront, ALB, ECS Fargate, RDS, ElastiCache, SQS, EventBridge, S3, SES, Secrets Manager, ECR, CloudWatch). The numbered arrows are explained under the drawing.
- `architecture.drawio`: the logical view of the browser, the API layers, the worker and the data stores.
- `erd.drawio`: tables, keys and the list indexes.
- `ticket_lifecycle.drawio`: ticket statuses and what each one does to the SLA clock.
- `business_flows.drawio`: seven sequence diagrams (B1 sign-in and refresh, B2 opening a ticket, B3 an agent reply, B4 real-time fan-out, B5 the SLA scan, B6 a CSV export, B7 tenant isolation).
