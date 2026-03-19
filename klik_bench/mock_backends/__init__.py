"""Mock service backends for benchmark evaluation."""

from klik_bench.mock_backends.system import SystemMockBackend
from klik_bench.mock_backends.web_search import WebSearchMockBackend

__all__ = ["SystemMockBackend", "WebSearchMockBackend"]
