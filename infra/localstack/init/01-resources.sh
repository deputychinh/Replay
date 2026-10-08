#!/bin/sh
# Same names as the CDK DataStack, so code paths are identical locally and in AWS.
set -e
awslocal sqs create-queue --queue-name relay-jobs-dlq >/dev/null
DLQ_ARN=$(awslocal sqs get-queue-attributes --queue-url http://localhost:4566/000000000000/relay-jobs-dlq \
  --attribute-names QueueArn --query Attributes.QueueArn --output text)
awslocal sqs create-queue --queue-name relay-jobs \
  --attributes "{\"VisibilityTimeout\":\"60\",\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"5\\\"}\"}" >/dev/null
awslocal s3 mb s3://relay-files >/dev/null
awslocal s3api put-bucket-cors --bucket relay-files --cors-configuration \
  '{"CORSRules":[{"AllowedOrigins":["*"],"AllowedMethods":["PUT","GET"],"AllowedHeaders":["*"],"MaxAgeSeconds":3000}]}'
echo "relay resources ready"
