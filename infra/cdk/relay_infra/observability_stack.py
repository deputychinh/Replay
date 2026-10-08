from aws_cdk import Duration, Stack
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_sns as sns
from constructs import Construct

from relay_infra.config import StageConfig
from relay_infra.data_stack import DataStack
from relay_infra.services_stack import ServicesStack


class ObservabilityStack(Stack):
    """Dashboard, alarms (to an SNS topic) and a monthly budget."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        config: StageConfig,
        data: DataStack,
        services: ServicesStack,
        alert_email: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        topic = sns.Topic(self, "Alerts", display_name=f"Relay {config.name} alerts")
        if alert_email:
            sns.Subscription(
                self, "AlertEmail", topic=topic, protocol=sns.SubscriptionProtocol.EMAIL, endpoint=alert_email
            )

        alb = services.alb.metrics
        tg = services.target_group.metrics
        five_minutes = Duration.minutes(5)
        alarms = {
            "Api5xx": (
                alb.http_code_target(code=elbv2.HttpCodeTarget.TARGET_5XX_COUNT, period=five_minutes),
                10,
                "More than 10 API 5xx in 5 minutes",
            ),
            "ApiLatencyP95": (
                tg.target_response_time(period=five_minutes, statistic="p95"),
                0.5,
                "API p95 above 500 ms",
            ),
            "DeadLetters": (
                data.dead_letters.metric_approximate_number_of_messages_visible(period=five_minutes),
                0,
                "A job failed 5 times and is in the dead-letter queue",
            ),
            "QueueAge": (
                data.queue.metric_approximate_age_of_oldest_message(period=five_minutes),
                300,
                "Jobs wait more than 5 minutes: the worker is down or too slow",
            ),
            "DbCpu": (data.database.metric_cpu_utilization(period=five_minutes), 80, "Postgres CPU above 80 %"),
            "ApiCpu": (
                services.api_service.metric_cpu_utilization(period=five_minutes),
                85,
                "API tasks CPU above 85 %",
            ),
        }
        for alarm_id, (metric, threshold, description) in alarms.items():
            alarm = cw.Alarm(
                self,
                alarm_id,
                metric=metric,
                threshold=threshold,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
                alarm_description=description,
            )
            alarm.add_alarm_action(cw_actions.SnsAction(topic))

        dashboard = cw.Dashboard(self, "Dashboard", dashboard_name=f"relay-{config.name}")
        dashboard.add_widgets(
            cw.GraphWidget(
                title="API requests and 5xx",
                left=[alb.request_count(), alb.http_code_target(code=elbv2.HttpCodeTarget.TARGET_5XX_COUNT)],
            ),
            cw.GraphWidget(
                title="API latency p50 / p95",
                left=[tg.target_response_time(statistic="p50"), tg.target_response_time(statistic="p95")],
            ),
            cw.GraphWidget(
                title="Job queue",
                left=[
                    data.queue.metric_approximate_number_of_messages_visible(),
                    data.dead_letters.metric_approximate_number_of_messages_visible(),
                ],
            ),
            cw.GraphWidget(
                title="CPU",
                left=[
                    services.api_service.metric_cpu_utilization(),
                    services.worker_service.metric_cpu_utilization(),
                    data.database.metric_cpu_utilization(),
                ],
            ),
        )

        budgets.CfnBudget(
            self,
            "Budget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_type="COST",
                time_unit="MONTHLY",
                budget_name=f"relay-{config.name}",
                budget_limit=budgets.CfnBudget.SpendProperty(amount=config.monthly_budget_usd, unit="USD"),
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        notification_type="FORECASTED",
                        threshold=100,
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(subscription_type="SNS", address=topic.topic_arn)
                    ],
                )
            ],
        )
