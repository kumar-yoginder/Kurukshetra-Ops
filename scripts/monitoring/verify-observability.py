#!/usr/bin/env python3
"""Local readiness/metrics checks; --probe adds a synthetic OTLP privacy regression test."""
import argparse
from datetime import datetime, timezone
import http.client
import json
import subprocess
import time
from urllib.parse import urlencode

class LocalStack:
    def __init__(self):
        self.addresses = {}
        for service in ("alloy", "prometheus", "grafana"):
            raw = subprocess.check_output(["docker", "inspect", "--format", "{{json .NetworkSettings.Networks}}", "kurukshetra-ops-" + service + "-1"], text=True)
            networks = json.loads(raw)
            self.addresses[service] = next(value["IPAddress"] for name, value in networks.items() if name.endswith("_observability-data"))
    def request(self, service, port, path, body=None, headers=None):
        connection = http.client.HTTPConnection(self.addresses[service], port, timeout=10)
        try:
            connection.request("POST" if body is not None else "GET", path, body=body, headers=headers or {})
            response = connection.getresponse()
            payload = response.read(1024 * 1024 + 1)
            if len(payload) > 1024 * 1024:
                raise ValueError("bounded verification response exceeded")
            return response.status, payload
        finally:
            connection.close()
    def query(self, expression):
        status, body = self.request("prometheus", 9090, "/api/v1/query?" + urlencode({"query": expression}))
        assert status == 200
        data = json.loads(body)
        assert data["status"] == "success"
        return data["data"]["result"], body

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    stack = LocalStack()
    for service, port, path in (("prometheus", 9090, "/-/ready"), ("alloy", 12345, "/-/ready"), ("grafana", 3000, "/grafana/api/health")):
        status, _ = stack.request(service, port, path)
        assert status == 200, (service, status)
        print("PASS readiness", service)
    for expression in ("kurukshetra_host_memory_bytes", "kurukshetra_container_memory_bytes", "chitragupt_registry_entries", "kurukshetra_host_cpu_usage_percent"):
        result, _ = stack.query(expression)
        assert result, ("No samples yet", expression)
        print("PASS stored metrics", expression)
    status, _ = stack.request("grafana", 3000, "/grafana/api/user", headers={"X-WEBAUTH-USER": "untrusted-direct-client"})
    assert status in (401, 403), ("Untrusted proxy identity accepted", status)
    print("PASS untrusted direct Grafana identity rejected")
    if args.probe:
        sentinel = "PRIVACY_SENTINEL_DO_NOT_EXPORT"
        now = str(time.time_ns())
        point = {"asDouble": 7, "timeUnixNano": now, "attributes": [{"key": "chat.id", "value": {"stringValue": sentinel}}], "exemplars": [{"asDouble": 7, "timeUnixNano": now, "traceId": "11" * 16, "spanId": "22" * 8, "filteredAttributes": [{"key": "private", "value": {"stringValue": sentinel}}]}]}
        metric = {"name": "kurukshetra_otel_pipeline_probe", "description": sentinel, "unit": sentinel, "gauge": {"dataPoints": [point]}}
        rejected = {"name": "private_unapproved_metric", "gauge": {"dataPoints": [point]}}
        payload = {"resourceMetrics": [{"resource": {"attributes": [{"key": "user.id", "value": {"stringValue": sentinel}}]}, "scopeMetrics": [{"scope": {"name": sentinel, "version": sentinel}, "metrics": [metric, rejected]}]}]}
        status, _ = stack.request("alloy", 4318, "/v1/metrics", json.dumps(payload), {"Content-Type": "application/json"})
        assert status == 200
        for attempt in range(15):
            result, body = stack.query("kurukshetra_otel_pipeline_probe")
            if any(float(series["value"][1]) == 7 for series in result):
                break
            time.sleep(2)
        else:
            raise AssertionError("OTLP sample not exported within the verification window")
        assert sentinel.encode() not in body
        for query in ("private_unapproved_metric", '{__name__=~".*PRIVACY.*"}'):
            result, _ = stack.query(query)
            assert not result, "Unapproved metric name or unit escaped the filter"
        status, body = stack.request("prometheus", 9090, "/api/v1/query_exemplars?" + urlencode({"query": "kurukshetra_otel_pipeline_probe", "start": time.time() - 120, "end": time.time()}))
        assert status == 200 and not json.loads(body).get("data")
        print("PASS synthetic OTLP admitted; identities, metadata, unit and exemplars excluded; unapproved metric rejected")
