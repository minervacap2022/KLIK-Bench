"""System mock backend — simulates a sandbox code execution environment.

Handles code_run, file_read, and file_write commands,
mapping to KK_exec's SystemProvider.
"""

import json
import traceback

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


class SystemMockBackend(BaseMockBackend):
    """Stateful mock for sandbox code execution (SystemProvider style).

    State schema:
        {
            "workspace_files": {
                "filename.csv": "file content...",
                "data.json": '{"key": "value"}'
            },
            "outputs": [],
            "files_created": {}
        }
    """

    def route_command(self, command: list[str]) -> MockResult:
        """Route a system CLI command to the appropriate handler."""
        if len(command) < 2 or command[0] != "system":
            return MockResult(
                stdout="",
                stderr=f"unknown command: {' '.join(command)}",
                exit_code=1,
            )

        action = command[1]
        remaining = command[2:]

        if action == "code_run":
            return self._code_run(remaining)
        if action == "file_read":
            return self._file_read(remaining)
        if action == "file_write":
            return self._file_write(remaining)

        return MockResult(
            stdout="",
            stderr=f"unknown subcommand: system {action}",
            exit_code=1,
        )

    def _code_run(self, args: list[str]) -> MockResult:
        """Execute Python code in a sandboxed context.

        Simple expressions are eval'd directly. Complex code with imports
        or statements is recorded and returns a mock success.
        """
        parsed = _parse_args(args)
        code = _get_flag(parsed, "--code")
        if not code:
            return MockResult(stdout="", stderr="--code is required", exit_code=1)

        # Build a local namespace with workspace files accessible
        workspace_files = self.state.get("workspace_files", {})
        local_ns: dict = {"workspace_files": workspace_files}

        # Try eval for simple expressions first
        output = self._try_eval(code, local_ns)

        # Record the execution
        self.state.setdefault("outputs", []).append(
            {"code": code, "result": output}
        )

        return MockResult(
            stdout=output,
            stderr="",
            exit_code=0,
        )

    def _try_eval(self, code: str, local_ns: dict) -> str:
        """Attempt to evaluate code, falling back to mock result for complex code."""
        # Try as a simple expression first (math, string ops)
        try:
            result = eval(code, {"__builtins__": {}}, local_ns)  # noqa: S307
            return str(result)
        except Exception:
            pass

        # Try exec for multi-statement code with a captured print
        captured: list[str] = []

        def mock_print(*args: object, **kwargs: object) -> None:
            captured.append(" ".join(str(a) for a in args))

        exec_ns: dict = {
            "__builtins__": {
                "print": mock_print,
                "len": len,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "dict": dict,
                "sum": sum,
                "min": min,
                "max": max,
                "round": round,
                "sorted": sorted,
                "enumerate": enumerate,
                "range": range,
                "zip": zip,
                "map": map,
                "filter": filter,
                "abs": abs,
                "pow": pow,
                "isinstance": isinstance,
                "type": type,
                "True": True,
                "False": False,
                "None": None,
            },
            **local_ns,
        }

        try:
            exec(code, exec_ns)  # noqa: S102
            if captured:
                return "\n".join(captured)
            return "Code executed successfully."
        except Exception:
            tb = traceback.format_exc()
            return f"Mock execution recorded. Code: {code[:200]}\n{tb}"

    def _file_read(self, args: list[str]) -> MockResult:
        """Read a file from the workspace."""
        parsed = _parse_args(args)
        path = _get_flag(parsed, "--path")
        if not path:
            return MockResult(stdout="", stderr="--path is required", exit_code=1)

        workspace_files = self.state.get("workspace_files", {})
        files_created = self.state.get("files_created", {})

        # Check both workspace_files and files_created
        if path in workspace_files:
            return MockResult(
                stdout=workspace_files[path],
                stderr="",
                exit_code=0,
            )
        if path in files_created:
            return MockResult(
                stdout=files_created[path],
                stderr="",
                exit_code=0,
            )

        return MockResult(
            stdout="",
            stderr=f"file not found: {path}",
            exit_code=1,
        )

    def _file_write(self, args: list[str]) -> MockResult:
        """Write a file to the workspace."""
        parsed = _parse_args(args)
        path = _get_flag(parsed, "--path")
        if not path:
            return MockResult(stdout="", stderr="--path is required", exit_code=1)

        content = _get_flag(parsed, "--content")
        if content is None:
            return MockResult(stdout="", stderr="--content is required", exit_code=1)

        self.state.setdefault("files_created", {})[path] = content

        return MockResult(
            stdout=json.dumps({"ok": True, "path": path, "bytes": len(content)}),
            stderr="",
            exit_code=0,
        )
