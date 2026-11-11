"""Aísla las pruebas unitarias de exportadores de observabilidad externos."""

import os


os.environ.setdefault("OTEL_SDK_DISABLED", "true")
