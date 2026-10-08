from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from relay_infra.config import StageConfig, ssm_name
from relay_infra.services_stack import ORIGIN_HEADER

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self' wss: https://*.amazonaws.com; frame-ancestors 'none'; base-uri 'self'"
)


class FrontendStack(Stack):
    """One CloudFront domain: the React app from S3, and /api/* (incl. WebSocket) to the ALB.
    Same origin for both, so the refresh cookie and the WebSocket need no CORS."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        config: StageConfig,
        alb: elbv2.IApplicationLoadBalancer,
        origin_secret: str,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        site = s3.Bucket(
            self,
            "Site",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.RETAIN if config.removal_protection else RemovalPolicy.DESTROY,
            auto_delete_objects=not config.removal_protection,
        )

        headers = cloudfront.ResponseHeadersPolicy(
            self,
            "SecurityHeaders",
            security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
                content_security_policy=cloudfront.ResponseHeadersContentSecurityPolicy(
                    content_security_policy=CSP, override=True
                ),
                strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=Duration.days(730), include_subdomains=True, override=True
                ),
                content_type_options=cloudfront.ResponseHeadersContentTypeOptions(override=True),
                frame_options=cloudfront.ResponseHeadersFrameOptions(
                    frame_option=cloudfront.HeadersFrameOption.DENY, override=True
                ),
                referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                    referrer_policy=cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN, override=True
                ),
            ),
        )

        api_origin = origins.LoadBalancerV2Origin(
            alb,
            protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
            read_timeout=Duration.seconds(60),
            custom_headers={ORIGIN_HEADER: origin_secret},
        )
        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                response_headers_policy=headers,
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=api_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                    response_headers_policy=headers,
                ),
            },
            # Client-side routes (/console/…, /portal/…) all serve index.html.
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403, response_http_status=200, response_page_path="/index.html", ttl=Duration.seconds(0)
                ),
                cloudfront.ErrorResponse(
                    http_status=404, response_http_status=200, response_page_path="/index.html", ttl=Duration.seconds(0)
                ),
            ],
            # With a custom domain, add `certificate=` and `minimum_protocol_version=TLS_V1_2_2021` here.
        )
        url = f"https://{self.distribution.distribution_domain_name}"
        for key, value in [
            ("web-bucket", site.bucket_name),
            ("web-distribution", self.distribution.distribution_id),
            ("url", url),
        ]:
            ssm.StringParameter(self, f"Param-{key}", parameter_name=ssm_name(config.name, key), string_value=value)
        CfnOutput(self, "Url", value=url)
