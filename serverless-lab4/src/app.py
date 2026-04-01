cat > src/app.py << 'EOF'
import json
import boto3
import os
import time
from datetime import datetime, timezone, timedelta

cloudwatch = boto3.client("cloudwatch")
s3 = boto3.client("s3")

NAMESPACE  = os.environ.get("CW_NAMESPACE", "Lab4/Analytics")
S3_BUCKET  = os.environ.get("S3_BUCKET")

def put_metric(latency_ms, status_code):
    cloudwatch.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[
            {"MetricName": "latency_ms", "Value": latency_ms, "Unit": "Milliseconds", "Timestamp": datetime.now(timezone.utc)},
            {"MetricName": "status_code", "Value": float(status_code), "Unit": "None", "Timestamp": datetime.now(timezone.utc)},
        ],
    )

def archive_to_s3(log_record):
    if not S3_BUCKET:
        return
    key = f"logs/{datetime.now(timezone.utc).strftime('%Y/%m/%d/%H%M%S%f')}.json"
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=json.dumps(log_record), ContentType="application/json")

def get_stats():
    end_time   = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=24)
    def fetch(metric_name, stat):
        resp = cloudwatch.get_metric_statistics(
            Namespace=NAMESPACE, MetricName=metric_name,
            StartTime=start_time, EndTime=end_time,
            Period=86400, Statistics=[stat],
        )
        points = resp.get("Datapoints", [])
        return points[0].get(stat, 0) if points else 0
    return {
        "period_hours": 24,
        "total_requests": int(fetch("latency_ms", "SampleCount")),
        "avg_latency_ms": round(fetch("latency_ms", "Average"), 2),
        "avg_status_code": round(fetch("status_code", "Average"), 2),
    }

def handler(event, context):
    start_ts = time.time()
    method = event.get("requestContext", {}).get("httpMethod") or event.get("httpMethod", "GET")
    path   = event.get("rawPath", event.get("path", "/"))
    try:
        if method == "GET" and path.rstrip("/").endswith("stats"):
            status_code = 200
            body = get_stats()
        else:
            status_code = 404
            body = {"message": "Not Found. Use GET /stats"}
    except Exception as exc:
        print(f"ERROR: {exc}")
        status_code = 500
        body = {"message": "Internal Server Error"}
    latency_ms = (time.time() - start_ts) * 1000
    try:
        put_metric(latency_ms, status_code)
    except Exception as exc:
        print(f"CloudWatch metric error: {exc}")
    try:
        archive_to_s3({"timestamp": datetime.now(timezone.utc).isoformat(), "method": method, "path": path, "status_code": status_code, "latency_ms": round(latency_ms, 2)})
    except Exception as exc:
        print(f"S3 archive error: {exc}")
    return {"statusCode": status_code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}
EOF