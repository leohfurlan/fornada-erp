"""Estado operacional sem despejar variáveis, tokens ou dados de clientes."""

import json
import re
import subprocess


def main() -> None:
    for name in ("api", "postgres", "redis"):
        container = f"fornada-evolution-{name}-1"
        result = subprocess.check_output(
            ["sudo", "docker", "inspect", container, "--format", "{{json .State}}"],
            text=True,
        )
        state = json.loads(result)
        print(
            name,
            state["Status"],
            "OOM",
            state["OOMKilled"],
            "health",
            state.get("Health", {}).get("Status"),
        )
    result = subprocess.run(
        ["sudo", "docker", "logs", "--tail", "35", "fornada-evolution-api-1"],
        capture_output=True,
        text=True,
        check=False,
    )
    logs = result.stdout + result.stderr
    logs = re.sub(r"(?:postgresql|redis)://\S+", "[connection redacted]", logs)
    logs = re.sub(r"[a-fA-F0-9]{32,}", "[token redacted]", logs)
    logs = re.sub(
        r"(?im)^.*(?:api.?key|token|password|secret).*$",
        "[sensitive line redacted]",
        logs,
    )
    print(logs[-5000:])


if __name__ == "__main__":
    main()
