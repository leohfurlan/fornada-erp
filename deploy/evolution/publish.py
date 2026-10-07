"""Publica somente a Evolution no Caddy existente, preservando a rota da Fornada."""

import argparse
import fcntl
import json
import re
import shutil
import socket
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from configure import load_env, write_env


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=capture)
    return result.stdout if capture else ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("domain")
    args = parser.parse_args()
    domain = args.domain.lower()
    if (
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", domain)
        or "." not in domain
    ):
        raise SystemExit("Hostname inválido")
    if socket.gethostbyname(domain) != "163.176.96.250":
        raise SystemExit("DNS não corresponde à VPS confirmada")
    # Mesmo lock do deploy Fornada: nunca disputar proxy/configuração com outro deploy.
    with open("/opt/fornada/.deploy.lock", "a") as deploy_lock:
        try:
            fcntl.flock(deploy_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(
                "Outro deploy Fornada está em andamento; aguarde sua conclusão"
            ) from None
        publish(domain)


def publish(domain: str) -> None:
    root = Path(__file__).resolve().parent
    env = load_env(root / ".env")
    env.update(SERVER_URL=f"https://{domain}", CORS_ORIGIN="*")
    write_env(root / ".env", env)
    run(
        "sudo",
        "docker",
        "compose",
        "-f",
        str(root / "compose.yml"),
        "-f",
        str(root / "public-network.yml"),
        "config",
        "--quiet",
    )
    run(
        "sudo",
        "docker",
        "compose",
        "-f",
        str(root / "compose.yml"),
        "-f",
        str(root / "public-network.yml"),
        "up",
        "-d",
        "--wait",
        "--wait-timeout",
        "720",
    )
    proxy = "fornada-prod-proxy-1"
    mounts = json.loads(
        run(
            "sudo",
            "docker",
            "inspect",
            proxy,
            "--format",
            "{{json .Mounts}}",
            capture=True,
        )
    )
    source = next(
        mount["Source"]
        for mount in mounts
        if mount["Destination"] == "/etc/caddy/Caddyfile"
    )
    path = Path(source)
    if path.resolve() != Path("/opt/fornada/deploy/Caddyfile"):
        raise SystemExit("Mount do Caddy mudou; inspecione antes de publicar")
    original = path.read_text()
    marker = f"# BEGIN EVOLUTION FORNADA {domain}"
    if marker in original:
        print("Bloco Evolution já configurado; aplicação preservada.")
        return
    if domain in original:
        raise SystemExit(
            "Hostname já aparece no Caddyfile; não sobrescrevo configuração existente"
        )
    addition = (
        f"\n{marker}\n{domain} {{\n"
        "    encode zstd gzip\n"
        "    request_body {\n        max_size 16MB\n    }\n"
        "    reverse_proxy evolution-api:8080\n"
        f"}}\n# END EVOLUTION FORNADA {domain}\n"
    )
    candidate = root / "Caddyfile.candidate"
    candidate.write_text(original + addition)
    candidate.chmod(0o600)
    run("sudo", "docker", "cp", str(candidate), f"{proxy}:/tmp/evolution.Caddyfile")
    run(
        "sudo",
        "docker",
        "exec",
        proxy,
        "caddy",
        "validate",
        "--config",
        "/tmp/evolution.Caddyfile",
        "--adapter",
        "caddyfile",
    )
    if path.read_text() != original:
        raise SystemExit(
            "Caddyfile alterado por outro processo; publicação interrompida"
        )
    backup = root / f"Caddyfile.before-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    shutil.copy2(path, backup)
    backup.chmod(0o600)
    path.write_text(original + addition)
    try:
        run(
            "sudo",
            "docker",
            "exec",
            proxy,
            "caddy",
            "reload",
            "--config",
            "/etc/caddy/Caddyfile",
            "--adapter",
            "caddyfile",
        )
    except subprocess.CalledProcessError:
        if path.read_text() == original + addition:
            path.write_text(original)
            run(
                "sudo",
                "docker",
                "exec",
                proxy,
                "caddy",
                "reload",
                "--config",
                "/etc/caddy/Caddyfile",
                "--adapter",
                "caddyfile",
            )
        raise
    print(f"Proxy recarregado para https://{domain}; containers Fornada preservados.")


if __name__ == "__main__":
    main()
