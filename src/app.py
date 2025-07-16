# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from celery.app import Celery

from opentelemetry import trace

from opentelemetry.exporter.otlp.proto.grpc import trace_exporter as grpc_exporter
from opentelemetry.exporter.otlp.proto.http import trace_exporter as http_exporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.celery import CeleryInstrumentor

def setup_telemetry(service_name: str):
    """Configures the OpenTelemetry trace exporter.

    Args:
        service_name (str): the service name used to identify generated traces.
    """

    resource = Resource(attributes={
        "service.name": service_name
    })

    # --- Tracing Setup ---
    trace.set_tracer_provider(TracerProvider(resource=resource))

    otel_mode = os.environ.get("OTEL_MODE", "otlp-grpc")
    otlp_grpc_endpoint = os.environ.get("OTLP_GRPC_ENDPOINT", "jaeger:4317")
    otlp_http_endpoint = os.environ.get("OTLP_HTTP_ENDPOINT", "http://jaeger-collector:4318/v1/traces")

    trace_exporter = None
    if otel_mode == "otlp-grpc":
        trace_exporter = grpc_exporter.OTLPSpanExporter(
                endpoint=otlp_grpc_endpoint, insecure=True)
    elif otel_mode == "otlp-http":
        trace_exporter = http_exporter.OTLPSpanExporter(
                endpoint=otlp_http_endpoint)
    else:
        raise Exception("Unsupported OTEL tracing mode %s", otel_mode)

    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(trace_exporter))

setup_telemetry('worker-strings')
REDIS_URL = os.getenv("REDIS_URL")
celery_app = Celery(broker=REDIS_URL, backend=REDIS_URL, include=["src.tasks"])
CeleryInstrumentor().instrument(celery_app=celery_app)
