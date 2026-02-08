from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_iam as iam,
)
from constructs import Construct


class DataLakeIncidentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        rca_bucket = s3.Bucket(
            self,
            "RcaBucket",
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        lambda_env = {
            "RCA_BUCKET": rca_bucket.bucket_name,
        }

        tools_code = lambda_.Code.from_asset("infra/lambda")
        runtime = lambda_.Runtime.PYTHON_3_12

        get_s3_logs = lambda_.Function(
            self,
            "GetS3LogsFn",
            runtime=runtime,
            handler="get_s3_logs.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        get_emr_logs = lambda_.Function(
            self,
            "GetEmrLogsFn",
            runtime=runtime,
            handler="get_emr_logs.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        get_glue_logs = lambda_.Function(
            self,
            "GetGlueLogsFn",
            runtime=runtime,
            handler="get_glue_logs.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        get_mwaa_logs = lambda_.Function(
            self,
            "GetMwaaLogsFn",
            runtime=runtime,
            handler="get_mwaa_logs.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        get_kafka_status = lambda_.Function(
            self,
            "GetKafkaStatusFn",
            runtime=runtime,
            handler="get_kafka_status.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        get_cloudwatch_alarm = lambda_.Function(
            self,
            "GetCloudwatchAlarmFn",
            runtime=runtime,
            handler="get_cloudwatch_alarm.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        get_athena_query = lambda_.Function(
            self,
            "GetAthenaQueryFn",
            runtime=runtime,
            handler="get_athena_query.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        verify_source_data = lambda_.Function(
            self,
            "VerifySourceDataFn",
            runtime=runtime,
            handler="verify_source_data.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        retry_emr = lambda_.Function(
            self,
            "RetryEmrFn",
            runtime=runtime,
            handler="retry_emr.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        retry_glue_job = lambda_.Function(
            self,
            "RetryGlueJobFn",
            runtime=runtime,
            handler="retry_glue_job.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        retry_airflow_dag = lambda_.Function(
            self,
            "RetryAirflowDagFn",
            runtime=runtime,
            handler="retry_airflow_dag.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        retry_athena_query = lambda_.Function(
            self,
            "RetryAthenaQueryFn",
            runtime=runtime,
            handler="retry_athena_query.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        retry_kafka = lambda_.Function(
            self,
            "RetryKafkaFn",
            runtime=runtime,
            handler="retry_kafka.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        update_servicenow = lambda_.Function(
            self,
            "UpdateServiceNowFn",
            runtime=runtime,
            handler="update_servicenow_ticket.handler",
            code=tools_code,
            timeout=Duration.seconds(30),
            environment=lambda_env,
        )

        rca_bucket.grant_read_write(verify_source_data)
        rca_bucket.grant_read_write(get_s3_logs)

        log_read_policy = iam.PolicyStatement(
            actions=[
                "logs:FilterLogEvents",
                "logs:GetLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
            ],
            resources=["*"],
        )

        for fn in [get_emr_logs, get_glue_logs, get_mwaa_logs]:
            fn.add_to_role_policy(log_read_policy)

        emr_policy = iam.PolicyStatement(
            actions=[
                "elasticmapreduce:DescribeCluster",
                "elasticmapreduce:ListClusters",
                "elasticmapreduce:DescribeStep",
                "elasticmapreduce:ListSteps",
                "elasticmapreduce:AddJobFlowSteps",
            ],
            resources=["*"],
        )
        get_emr_logs.add_to_role_policy(emr_policy)
        retry_emr.add_to_role_policy(emr_policy)

        glue_policy = iam.PolicyStatement(
            actions=[
                "glue:GetJob",
                "glue:GetJobRun",
                "glue:GetJobRuns",
                "glue:StartJobRun",
            ],
            resources=["*"],
        )
        get_glue_logs.add_to_role_policy(glue_policy)
        retry_glue_job.add_to_role_policy(glue_policy)

        mwaa_policy = iam.PolicyStatement(
            actions=[
                "airflow:CreateCliToken",
                "airflow:CreateWebLoginToken",
            ],
            resources=["*"],
        )
        get_mwaa_logs.add_to_role_policy(mwaa_policy)
        retry_airflow_dag.add_to_role_policy(mwaa_policy)

        kafka_policy = iam.PolicyStatement(
            actions=[
                "kafka:DescribeCluster",
                "kafka:DescribeClusterV2",
                "kafka:GetBootstrapBrokers",
                "kafka:ListClusters",
                "kafka:ListClustersV2",
            ],
            resources=["*"],
        )
        get_kafka_status.add_to_role_policy(kafka_policy)
        retry_kafka.add_to_role_policy(kafka_policy)

        cw_policy = iam.PolicyStatement(
            actions=["cloudwatch:DescribeAlarms"],
            resources=["*"],
        )
        get_cloudwatch_alarm.add_to_role_policy(cw_policy)

        athena_policy = iam.PolicyStatement(
            actions=[
                "athena:StartQueryExecution",
                "athena:GetQueryExecution",
                "athena:GetQueryResults",
                "athena:StopQueryExecution",
            ],
            resources=["*"],
        )
        retry_athena_query.add_to_role_policy(athena_policy)
        get_athena_query.add_to_role_policy(athena_policy)
        retry_athena_query.add_to_role_policy(
            iam.PolicyStatement(actions=["s3:PutObject", "s3:GetBucketLocation"], resources=["*"])
        )

        CfnOutput(self, "RcaBucketName", value=rca_bucket.bucket_name)
        CfnOutput(self, "GetS3LogsArn", value=get_s3_logs.function_arn)
        CfnOutput(self, "GetEmrLogsArn", value=get_emr_logs.function_arn)
        CfnOutput(self, "GetGlueLogsArn", value=get_glue_logs.function_arn)
        CfnOutput(self, "GetMwaaLogsArn", value=get_mwaa_logs.function_arn)
        CfnOutput(self, "GetKafkaStatusArn", value=get_kafka_status.function_arn)
        CfnOutput(self, "GetCloudwatchAlarmArn", value=get_cloudwatch_alarm.function_arn)
        CfnOutput(self, "GetAthenaQueryArn", value=get_athena_query.function_arn)
        CfnOutput(self, "VerifySourceDataArn", value=verify_source_data.function_arn)
        CfnOutput(self, "RetryEmrArn", value=retry_emr.function_arn)
        CfnOutput(self, "RetryGlueJobArn", value=retry_glue_job.function_arn)
        CfnOutput(self, "RetryAirflowDagArn", value=retry_airflow_dag.function_arn)
        CfnOutput(self, "RetryAthenaQueryArn", value=retry_athena_query.function_arn)
        CfnOutput(self, "RetryKafkaArn", value=retry_kafka.function_arn)
        CfnOutput(self, "UpdateServiceNowArn", value=update_servicenow.function_arn)
