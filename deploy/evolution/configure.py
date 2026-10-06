"""Executar apenas na VPS: gera segredos sem imprimi-los; prepara instância privada."""

import argparse
import json
import os
import secrets
import subprocess
import urllib.request
from urllib.parse import urlparse
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in path.read_text().splitlines()
        if line and not line.startswith("#") and "=" in line
    )


def write_env(path: Path, values: dict[str, str]) -> None:
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
    os.chmod(path, 0o600)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["env", "cors", "pin", "instance", "status"])
    parser.add_argument("--url", default="http://localhost:8081")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    path = root / ".env"
    if args.action == "env":
        if path.exists():
            print("Configuração existente preservada.")
            return
        write_env(
            path,
            {
                "EVOLUTION_IMAGE": "evoapicloud/evolution-api:v2.3.7",
                "EVOLUTION_DB_PASSWORD": secrets.token_hex(32),
                "AUTHENTICATION_API_KEY": secrets.token_hex(32),
                "SERVER_URL": args.url,
                "EVOLUTION_DOMAIN": urlparse(args.url).hostname or "localhost",
                "CORS_ORIGIN": "*",
                "FORNADA_INSTANCE": "fornada",
                "FORNADA_INSTANCE_TOKEN": secrets.token_hex(32),
                "FORNADA_WEBHOOK_SECRET": secrets.token_hex(32),
            },
        )
        print("Configuração criada com permissões 600; segredos não exibidos.")
        return
    env = load_env(path)
    if args.action == "cors":
        # APIs server-to-server não enviam Origin; autenticação é por apikey.
        env["CORS_ORIGIN"] = "*"
        write_env(path, env)
        print("CORS ajustado; segredos preservados.")
        return
    if args.action == "pin":
        digest = subprocess.check_output(
            [
                "sudo",
                "docker",
                "image",
                "inspect",
                env["EVOLUTION_IMAGE"],
                "--format",
                "{{index .RepoDigests 0}}",
            ],
            text=True,
        ).strip()
        if not digest.startswith("evoapicloud/evolution-api@sha256:"):
            raise SystemExit("Digest inesperado; nenhuma configuração alterada")
        env["EVOLUTION_IMAGE"] = digest
        write_env(path, env)
        print(f"Imagem fixada: {digest}")
        return

    def request(route: str, data: dict | None = None) -> dict | list:
        req = urllib.request.Request(
            "http://127.0.0.1:8081/" + route,
            data=json.dumps(data).encode() if data is not None else None,
            headers={
                "apikey": env["AUTHENTICATION_API_KEY"],
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    if args.action == "instance":
        instances = request("instance/fetchInstances")
        if not any(
            instance.get("name") == env["FORNADA_INSTANCE"]
            or instance.get("instance", {}).get("instanceName")
            == env["FORNADA_INSTANCE"]
            for instance in instances
        ):
            request(
                "instance/create",
                {
                    "instanceName": env["FORNADA_INSTANCE"],
                    "token": env["FORNADA_INSTANCE_TOKEN"],
                    "integration": "WHATSAPP-BAILEYS",
                    "qrcode": False,
                    "rejectCall": True,
                    "msgCall": "",
                    "groupsIgnore": True,
                    "alwaysOnline": False,
                    "readMessages": False,
                    "readStatus": False,
                    "syncFullHistory": False,
                },
            )
        print(
            "Instância fornada preparada. Webhook desligado; WhatsApp ainda precisa de pareamento."
        )
    else:
        result = request("instance/connectionState/" + env["FORNADA_INSTANCE"])
        print(
            json.dumps(
                {
                    "instance": env["FORNADA_INSTANCE"],
                    "state": result.get("instance", {}).get("state"),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
