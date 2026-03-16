"""CLI adapter for AI-CORE.

Usage:
    py -m adapters.cli <tool> [--key value ...]
    py -m adapters.cli healthcheck
    py -m adapters.cli echo --message "hello"
    py -m adapters.cli fetch_url --url https://example.com
    py -m adapters.cli query_runs --failed_only true --limit 10
    py -m adapters.cli --host http://localhost:8000 system_info

Environment:
    AI_CORE_URL   Base URL of the AI-CORE server (default: http://localhost:8000)
"""
import argparse
import json
import os
import sys

import httpx


def _parse_arguments(tokens: list[str]) -> dict:
    """Convert ['--key', 'value', '--flag'] into {'key': 'value', 'flag': True}."""
    args: dict = {}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("--"):
            key = tok[2:].replace("-", "_")
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                val = tokens[i + 1]
                # Coerce JSON-parseable values (true/false/numbers/arrays/objects)
                try:
                    val = json.loads(val)
                except (json.JSONDecodeError, ValueError):
                    pass
                args[key] = val
                i += 2
            else:
                args[key] = True
                i += 1
        else:
            i += 1
    return args


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI-CORE CLI adapter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("command", help="Tool name to execute")
    parser.add_argument(
        "--host",
        default=os.getenv("AI_CORE_URL", "http://localhost:8000"),
        help="AI-CORE base URL",
    )
    parser.add_argument("--request-id", default=None, help="Optional request ID for correlation")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")

    args, remaining = parser.parse_known_args()
    arguments = _parse_arguments(remaining)

    payload: dict = {"command": args.command, "arguments": arguments}
    if args.request_id:
        payload["request_id"] = args.request_id

    try:
        resp = httpx.post(
            f"{args.host.rstrip('/')}/command",
            json=payload,
            timeout=args.timeout,
        )
        result = resp.json()
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0 if result.get("success") else 1)
    except httpx.ConnectError:
        print(json.dumps({"success": False, "error": f"Cannot connect to {args.host}"}), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
