# services/uptime_service.py
import boto3
from datetime import datetime, timedelta

cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

def get_lambda_uptime(function_name):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=30)

    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/Lambda",
        MetricName="Invocations",
        Dimensions=[{"Name": "FunctionName", "Value": function_name}],
        StartTime=start_time,
        EndTime=end_time,
        Period=86400,
        Statistics=["Sum"]
    )

    error_response = cloudwatch.get_metric_statistics(
        Namespace="AWS/Lambda",
        MetricName="Errors",
        Dimensions=[{"Name": "FunctionName", "Value": function_name}],
        StartTime=start_time,
        EndTime=end_time,
        Period=86400,
        Statistics=["Sum"]
    )

    total_invocations = sum(dp["Sum"] for dp in response["Datapoints"])
    total_errors = sum(dp["Sum"] for dp in error_response["Datapoints"])

    if total_invocations == 0:
        return 100.0

    uptime = ((total_invocations - total_errors) / total_invocations) * 100
    return round(uptime, 2)

def get_rds_uptime(db_instance_identifier):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=30)

    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/RDS",
        MetricName="CPUUtilization",
        Dimensions=[
            {
                "Name": "DBInstanceIdentifier",
                "Value": db_instance_identifier
            }
        ],
        StartTime=start_time,
        EndTime=end_time,
        Period=86400,
        Statistics=["Average"]
    )

    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return 0.0

    # If DB had connections → considered UP
    uptime = (len(datapoints) / 30) * 100
    return round(min(uptime, 100), 2)