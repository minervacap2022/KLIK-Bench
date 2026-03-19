"""Web search mock backend — simulates web search and page reading.

Handles search and read commands,
mapping to KK_exec's JinaProvider/DuckDuckGoProvider.
"""

import json

from klik_bench.mock_backends.base import BaseMockBackend, MockResult


def _parse_args(args: list[str]) -> dict[str, list[str]]:
    """Parse CLI args into a dict mapping --flag to list of values.

    Supports repeated flags (e.g. --label bug --label urgent).
    Positional args are stored under the empty-string key.
    """
    parsed: dict[str, list[str]] = {"": []}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            key = arg
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                parsed.setdefault(key, []).append(args[i + 1])
                i += 2
            else:
                parsed.setdefault(key, []).append("")
                i += 1
        else:
            parsed[""].append(arg)
            i += 1
    return parsed


def _get_flag(parsed: dict[str, list[str]], flag: str) -> str | None:
    """Get the first value for a flag, or None if absent."""
    values = parsed.get(flag)
    if values:
        return values[0]
    return None


class WebSearchMockBackend(BaseMockBackend):
    """Stateful mock for web search tools (Jina/DuckDuckGo style).

    State schema:
        {
            "search_results": {
                "keyword1": [
                    {"title": "Result 1", "url": "https://...", "snippet": "..."},
                    {"title": "Result 2", "url": "https://...", "snippet": "..."}
                ]
            },
            "pages": {
                "https://example.com": "Page content..."
            },
            "searches_performed": [],
            "pages_visited": []
        }
    """

    def route_command(self, command: list[str]) -> MockResult:
        """Route a web_search CLI command to the appropriate handler."""
        if len(command) < 2 or command[0] != "web_search":
            return MockResult(
                stdout="",
                stderr=f"unknown command: {' '.join(command)}",
                exit_code=1,
            )

        action = command[1]
        remaining = command[2:]

        if action == "search":
            return self._search(remaining)
        if action == "read":
            return self._read(remaining)

        return MockResult(
            stdout="",
            stderr=f"unknown subcommand: web_search {action}",
            exit_code=1,
        )

    def _search(self, args: list[str]) -> MockResult:
        """Search the web by query, matching against pre-loaded search_results."""
        parsed = _parse_args(args)
        query = _get_flag(parsed, "--query")
        if not query:
            return MockResult(stdout="", stderr="--query is required", exit_code=1)

        max_results_str = _get_flag(parsed, "--max_results")
        max_results = int(max_results_str) if max_results_str else 5

        # Log the search
        self.state.setdefault("searches_performed", []).append(query)

        # Match query against search_results keys (case-insensitive, partial match)
        search_results = self.state.get("search_results", {})
        matches: list[dict] = []
        query_lower = query.lower()

        for keyword, results in search_results.items():
            if query_lower in keyword.lower() or keyword.lower() in query_lower:
                matches.extend(results)

        # Deduplicate by URL, preserving order
        seen_urls: set[str] = set()
        unique_matches: list[dict] = []
        for result in matches:
            url = result.get("url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_matches.append(result)

        # Apply max_results limit
        unique_matches = unique_matches[:max_results]

        return MockResult(
            stdout=json.dumps(unique_matches),
            stderr="",
            exit_code=0,
        )

    def _read(self, args: list[str]) -> MockResult:
        """Read a web page by URL."""
        parsed = _parse_args(args)
        url = _get_flag(parsed, "--url")
        if not url:
            return MockResult(stdout="", stderr="--url is required", exit_code=1)

        # Log the page visit
        self.state.setdefault("pages_visited", []).append(url)

        pages = self.state.get("pages", {})
        if url not in pages:
            return MockResult(
                stdout="",
                stderr=f"404 Not Found: {url}",
                exit_code=1,
            )

        return MockResult(
            stdout=pages[url],
            stderr="",
            exit_code=0,
        )
