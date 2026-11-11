"""Bounded HTTPS throughput samples with validated dashboard contracts."""
from datetime import datetime, timezone
import http.client
import os
import statistics
import time
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, model_validator

class SpeedSample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checked: datetime
    test_state: Literal["complete", "partial", "unavailable"] = "unavailable"
    download_mbps: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    upload_mbps: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    response_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    download_bytes: int = Field(ge=0, le=4194304)
    upload_bytes: int = Field(ge=0, le=1048576)
    verified_tor: bool | None = None

class SpeedReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    updated: datetime
    interval_seconds: Literal[900] = 900
    internet: SpeedSample
    tor: SpeedSample

    @model_validator(mode="after")
    def verified_paths(self):
        if self.internet.verified_tor is not None:
            raise ValueError("Home Internet is a separately measured direct path")
        if self.tor.verified_tor is not True and any(value is not None for value in (self.tor.download_mbps, self.tor.upload_mbps, self.tor.response_ms)):
            raise ValueError("Unverified Tor results must not contain speed values")
        return self

class TorProbeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checked: datetime
    verified_tor: bool
    exit_ip: IPvAnyAddress | None
    sample_mbps: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    upload_mbps: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    response_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    sample_bytes: Literal[262144]
    upload_bytes: Literal[65536] = 65536
    test_state: Literal["complete", "partial", "unavailable"]

class InternetProbe:
    host = "speed.cloudflare.com"
    download_bytes = 4194304
    upload_bytes = 1048576

    def request(self, method, path, limit, body=None):
        # Fixed vendor host, verified TLS, no redirects, bounded body and timeout.
        connection = http.client.HTTPSConnection(self.host, timeout=15)
        start = time.monotonic()
        try:
            connection.request(method, path, body=body, headers={"User-Agent": "Kurukshetra-speed/1", "Accept-Encoding": "identity", "Cache-Control": "no-cache", "Content-Type": "application/octet-stream"})
            response = connection.getresponse()
            if response.status != 200:
                raise OSError("measurement endpoint unavailable")
            chunks = []
            count = 0
            while True:
                if time.monotonic() - start > 45:
                    raise OSError("measurement deadline exceeded")
                chunk = response.read1(min(65536, limit + 1 - count))
                if not chunk:
                    break
                chunks.append(chunk)
                count += len(chunk)
                if count > limit:
                    raise OSError("measurement exceeded cap")
            return b"".join(chunks), time.monotonic() - start
        finally:
            connection.close()

    def run(self):
        result = SpeedSample(checked=datetime.now(timezone.utc), download_bytes=self.download_bytes, upload_bytes=self.upload_bytes)
        try:
            timings = [self.request("GET", "/__down?bytes=0", 0)[1] * 1000 for _ in range(3)]
            result.response_ms = round(statistics.median(timings), 1)
            data, elapsed = self.request("GET", "/__down?bytes=" + str(self.download_bytes), self.download_bytes)
            if len(data) != self.download_bytes:
                raise OSError("incomplete download")
            result.download_mbps = round(len(data) * 8 / elapsed / 1000000, 3)
            _, elapsed = self.request("POST", "/__up", 8192, os.urandom(self.upload_bytes))
            result.upload_mbps = round(self.upload_bytes * 8 / elapsed / 1000000, 3)
            result.test_state = "complete"
        except (OSError, http.client.HTTPException):
            result.test_state = "partial" if result.download_mbps is not None or result.response_ms is not None else "unavailable"
        return result
