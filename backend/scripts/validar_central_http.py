"""Ensaio HTTP real, exclusivamente em PostgreSQL descartável localhost:55446.

Executar com o Python da central (psycopg/cryptography/pyotp instalados).
Cria dois bancos com nomes aleatórios, aplica migrations reais, inicia duas APIs
em localhost, usa workers reais e simula apenas a fronteira Evolution e a rede.
Nenhum telefone, credencial ou base de produção é aceito.
"""

import argparse
import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
from psycopg import sql
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--central-backend", type=Path, required=True)
    parser.add_argument("--fornada-python", type=Path, required=True)
    parser.add_argument("--postgres-url", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    info = psycopg.conninfo.conninfo_to_dict(args.postgres_url)
    if (
        info.get("host") != "127.0.0.1"
        or info.get("port") != "55446"
        or info.get("dbname") != "postgres"
    ):
        raise ValueError("Use somente o PostgreSQL descartável 127.0.0.1:55446/postgres")
    central_path = args.central_backend.resolve()
    fornada_path = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(central_path))
    from alembic.config import Config
    from app.config import FornadaConnector, Settings
    from app.fornada_adapter import adapters
    from app.messaging import consume_one, dispatch_one
    from app.models import (
        Business,
        Connection,
        Conversation,
        Operator,
        OperatorSession,
        PurchaseFlow,
        now,
    )
    from app.purchases import process_one
    from app.security import cipher, digest, hasher
    from cryptography.fernet import Fernet

    from alembic import command

    suffix = uuid4().hex
    names = ["fornada_central_test_" + suffix, "central_http_test_" + suffix]
    processes, handles, evidence = [], [], {"synthetic": True, "checks": []}
    engine = proxy = None
    bid, tid, uid, material_id = [str(uuid4()) for _ in range(4)]
    phone = "+5511999990001"
    token = "synthetic-http-central-service-token-2026"
    connection_id = str(uuid4())
    operator_token, csrf = uuid4().hex, uuid4().hex
    ports = []
    for _ in range(3):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            ports.append(sock.getsockname()[1])
    fornada_url, central_url, proxy_url = [f"http://127.0.0.1:{port}" for port in ports]

    def dburl(name, driver=""):
        # URL criada a partir de componentes analisados; não recebe destinos externos.
        from sqlalchemy.engine import URL

        return URL.create(
            "postgresql" + driver,
            username=info["user"],
            password=info.get("password"),
            host="127.0.0.1",
            port=55446,
            database=name,
        ).render_as_string(hide_password=False)

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        evidence["checks"].append(label)
        print("PASS " + label, flush=True)

    def run(command_line, cwd, env):
        result = subprocess.run(command_line, cwd=cwd, env=env, capture_output=True, timeout=120)
        if result.returncode:
            raise RuntimeError(
                result.stdout.decode(errors="replace")[-3000:]
                + result.stderr.decode(errors="replace")[-3000:]
            )

    def start(command_line, cwd, env, log):
        handle = open(log, "w", encoding="utf-8")
        handles.append(handle)
        processes.append(
            subprocess.Popen(command_line, cwd=cwd, env=env, stdout=handle, stderr=handle)
        )

    def wait_http(url, path):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                response = httpx.get(url + path, timeout=1, trust_env=False)
                if response.status_code < 500:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        raise RuntimeError("API local não iniciou; consulte os logs sintéticos")

    class NetworkFault(BaseHTTPRequestHandler):
        drop_execution = False
        execute_calls = 0

        def log_message(self, *_):
            pass

        def do_POST(self):
            content = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            with httpx.Client(trust_env=False, timeout=30) as client:
                response = client.post(
                    fornada_url + self.path,
                    content=content,
                    headers={
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/json",
                    },
                )
            if self.path.endswith("/execute"):
                type(self).execute_calls += 1
                if type(self).drop_execution:
                    type(self).drop_execution = False
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
            self.send_response(response.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response.content)))
            self.end_headers()
            self.wfile.write(response.content)

    class SyntheticEvolution:
        image = b""

        def media(self, connection, reference):
            assert connection.base_url == "https://synthetic.invalid"
            return self.image, "image/png"

        def send(self, connection, message, remote):
            assert connection.base_url == "https://synthetic.invalid"
            return "accepted", "synthetic-" + str(uuid4()), None

    try:
        with psycopg.connect(args.postgres_url, autocommit=True) as admin:
            for name in names:
                admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        fenv = os.environ.copy()
        fenv.update(
            DATABASE_URL=dburl(names[0], "+asyncpg"),
            SECRET_KEY="synthetic-local-secret-key-http-2026",
            GOOGLE_AI_API_KEY="",
            SENTRY_DSN="",
            IFOOD_ENABLED="false",
            IFOOD_NOTIFICATIONS_ENABLED="false",
            IFOOD_WHATSAPP_ENABLED="false",
            WHATSAPP_AUTH_ENABLED="false",
            EVOLUTION_ENABLED="false",
            ENVIRONMENT="test",
            DEBUG="false",
            PYTHONPATH=str(fornada_path),
            CENTRAL_ENABLED="true",
            CENTRAL_SERVICE_TOKEN=token,
            CENTRAL_BUSINESS_TENANTS=json.dumps({bid: tid}),
            CENTRAL_LOCAL_OCR_ENABLED="false",
        )
        run(
            [str(args.fornada_python), "-m", "alembic", "upgrade", "f3197cd42901"],
            fornada_path,
            fenv,
        )
        with psycopg.connect(dburl(names[0])) as db:
            db.execute(
                "INSERT INTO tenants (id,nome,plano,ativo) "
                "VALUES (%s,'Synthetic HTTP','starter',true)",
                (tid,),
            )
            db.execute(
                "INSERT INTO usuarios "
                "(id,tenant_id,email,senha_hash,nome,telefone,valor_hora,ativo,is_superuser) "
                "VALUES (%s,%s,%s,'unused','Synthetic',%s,0,true,false)",
                (uid, tid, suffix + "@example.invalid", phone),
            )
            db.execute(
                "INSERT INTO ingredientes "
                "(id,tenant_id,codigo,tipo,nome,unidade,estoque_atual,quantidade_reservada,"
                "estoque_minimo,custo_medio) "
                "VALUES (%s,%s,1,'ingrediente','Farinha','kg',0,0,0,0)",
                (material_id, tid),
            )
            db.execute(
                "INSERT INTO ifood_monitores (id,tenant_id,merchant_id,loja_nome) "
                "VALUES (%s,%s,%s,'Teste - preservação central')",
                (str(uuid4()), tid, str(uuid4())),
            )
            db.execute(
                "INSERT INTO ifood_alertas (id,tenant_id,merchant_id,order_id) "
                "VALUES (%s,%s,%s,%s)",
                (str(uuid4()), tid, str(uuid4()), str(uuid4())),
            )
        run([str(args.fornada_python), "-m", "alembic", "upgrade", "head"], fornada_path, fenv)
        run(
            [str(args.fornada_python), "-m", "alembic", "downgrade", "f3197cd42901"],
            fornada_path,
            fenv,
        )
        run([str(args.fornada_python), "-m", "alembic", "upgrade", "head"], fornada_path, fenv)
        with psycopg.connect(dburl(names[0])) as db:
            check(
                "migration preserva usuário e iFood após upgrade/downgrade/upgrade",
                db.execute("SELECT count(*) FROM usuarios WHERE id=%s", (uid,)).fetchone()[0] == 1
                and db.execute("SELECT to_regclass('ifood_alertas')").fetchone()[0] is not None
                and db.execute(
                    "SELECT count(*) FROM ifood_monitores WHERE tenant_id=%s", (tid,)
                ).fetchone()[0]
                == 1
                and db.execute(
                    "SELECT count(*) FROM ifood_alertas WHERE tenant_id=%s", (tid,)
                ).fetchone()[0]
                == 1
                and db.execute("SELECT version_num FROM alembic_version").fetchall()
                == [("a85c10b7d302",)],
            )
        settings = Settings(
            _env_file=None,
            database_url=dburl(names[1], "+psycopg"),
            environment="test",
            encryption_key=Fernet.generate_key().decode(),
            origin=central_url,
            cookie_secure=False,
            fornada_connectors={
                bid: FornadaConnector(
                    base_url=proxy_url,
                    service_token=token,
                    verified=True,
                    conformance_ref="synthetic-http",
                    automation_enabled=True,
                    activated_after=now() - timedelta(hours=1),
                )
            },
        )
        engine = create_engine(settings.database_url)
        with engine.begin() as conn:
            config = Config(str(central_path / "alembic.ini"))
            config.set_main_option("script_location", str(central_path / "migrations"))
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
        sessions = sessionmaker(engine, expire_on_commit=False)
        with sessions.begin() as db:
            operator = Operator(
                username="synthetic-http",
                password_hash=hasher.hash("SyntheticOnly2026"),
                totp_encrypted=cipher(settings).encrypt(b"JBSWY3DPEHPK3PXP").decode(),
            )
            db.add(operator)
            db.flush()
            db.add(
                OperatorSession(
                    token_hash=digest(operator_token),
                    operator_id=operator.id,
                    csrf=csrf,
                    expires_at=now() + timedelta(hours=1),
                )
            )
            db.add(
                Business(
                    id=bid,
                    name="Synthetic Fornada",
                    origin_system="fornada",
                    capabilities=["purchases.review", "stock.receive"],
                )
            )
            db.flush()
            db.add(
                Connection(
                    id=connection_id,
                    business_id=bid,
                    base_url="https://synthetic.invalid",
                    instance_name="synthetic",
                    api_key_encrypted=cipher(settings).encrypt(b"synthetic").decode(),
                    webhook_secret_encrypted=cipher(settings)
                    .encrypt(b"synthetic-webhook-secret-32-characters")
                    .decode(),
                    mode="active",
                    state="open",
                    observed_at=now(),
                    conformance_confirmed=True,
                )
            )
        cenv = os.environ.copy()
        cenv.update(
            CENTRAL_DATABASE_URL=settings.database_url,
            CENTRAL_ENVIRONMENT="test",
            CENTRAL_ENCRYPTION_KEY=settings.encryption_key,
            CENTRAL_ORIGIN=central_url,
            CENTRAL_COOKIE_SECURE="false",
            CENTRAL_FORNADA_CONNECTORS=json.dumps(
                {
                    bid: settings.fornada_connectors[bid].model_dump(mode="json")
                    | {"service_token": token}
                }
            ),
            CENTRAL_EVOLUTION_ALLOWED_ORIGINS='["https://synthetic.invalid"]',
            PYTHONPATH=str(central_path),
        )
        proxy = ThreadingHTTPServer(("127.0.0.1", ports[2]), NetworkFault)
        threading.Thread(target=proxy.serve_forever, daemon=True).start()
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        start(
            [
                str(args.fornada_python),
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(ports[0]),
                "--no-access-log",
            ],
            fornada_path,
            fenv,
            args.evidence.with_suffix(".fornada.log"),
        )
        start(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(ports[1]),
                "--no-access-log",
            ],
            central_path,
            cenv,
            args.evidence.with_suffix(".central.log"),
        )
        wait_http(fornada_url, "/health")
        wait_http(central_url, "/api/businesses")
        registry, media = adapters(settings), SyntheticEvolution()
        client = httpx.Client(
            base_url=central_url,
            trust_env=False,
            timeout=30,
            headers={"Origin": central_url, "X-CSRF-Token": csrf},
            cookies={"central_session": operator_token},
        )
        fclient = httpx.Client(
            base_url=fornada_url + "/api/v1/central/",
            trust_env=False,
            timeout=30,
            headers={"Authorization": "Bearer " + token},
        )

        def assert_response(response):
            assert response.status_code < 300, f"HTTP {response.status_code}: {response.text}"
            return response.json() if response.content else {}

        def webhook(cid, content):
            response = client.post(
                "/api/webhooks/evolution/" + connection_id,
                headers={"X-Webhook-Secret": "synthetic-webhook-secret-32-characters"},
                json={
                    "event": "messages.upsert",
                    "instance": "synthetic",
                    "data": {
                        "key": {
                            "id": str(uuid4()),
                            "remoteJid": phone[1:] + "@s.whatsapp.net",
                            "fromMe": False,
                        },
                        "messageTimestamp": int(time.time()),
                        "message": content,
                    },
                },
            )
            assert_response(response)
            while consume_one(sessions):
                pass

        def flow(cid):
            return assert_response(
                client.get(f"/api/businesses/{bid}/conversations/{cid}/purchases")
            )[0]

        def command(cid, fid, suffix, **fields):
            current = flow(cid)
            conv = assert_response(
                client.get(f"/api/conversations/{cid}", params={"business_id": bid})
            )
            return client.post(
                f"/api/businesses/{bid}/conversations/{cid}/purchases/{fid}/{suffix}",
                json={
                    "expected_version": current["version"],
                    "expected_control_version": conv["control_version"],
                    **fields,
                },
            )

        def prepare():
            # Nova conversa de teste com o mesmo remetente requer limpar só a conversa anterior.
            with sessions.begin() as db:
                previous = db.scalar(
                    select(Conversation).where(Conversation.connection_id == connection_id)
                )
                if previous:
                    previous.remote_identity = "archived-" + previous.id + "@s.whatsapp.net"
                conversation = Conversation(
                    connection_id=connection_id,
                    remote_identity=phone[1:] + "@s.whatsapp.net",
                    verified_phone=phone,
                    control_mode="agent_eligible",
                    agent_since=now() - timedelta(minutes=1),
                )
                db.add(conversation)
                db.get(Connection, connection_id).observed_at = now()
                db.flush()
                cid = conversation.id

            def chunk(kind, content):
                return (
                    struct.pack("!I", len(content))
                    + kind
                    + content
                    + struct.pack("!I", zlib.crc32(kind + content))
                )

            color = uuid4().bytes[:3]
            media.image = (
                b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack("!IIBBBBB", 10, 10, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress((b"\0" + color * 10) * 10))
                + chunk(b"IEND", b"")
            )
            webhook(cid, {"imageMessage": {"mimetype": "image/png"}})
            assert process_one(sessions, settings, registry, media)
            row = flow(cid)
            check(
                "imagem sem OCR abre revisão humana",
                row["state"] == "review" and row["source"]["state"] == "review",
            )
            reviewed = {
                "itens": [
                    {
                        "ingrediente_id": material_id,
                        "descricao_original": "FARINHA",
                        "quantidade": "2",
                        "unidade": "kg",
                        "custo_unitario": "10",
                        "preco_total": "20",
                        "aceitar_excecao": True,
                    }
                ]
            }
            assert_response(command(cid, row["id"], "review", reviewed=reviewed))
            check("salvar revisão não envia nem executa", flow(cid)["state"] == "prepared")
            assert_response(command(cid, row["id"], "send-summary"))
            assert dispatch_one(sessions, media, settings, software_adapters=registry)
            with sessions() as db:
                purchase = db.get(PurchaseFlow, row["id"])
                answer = f"APROVAR {purchase.token} {flow(cid)['source']['version']}"
            return cid, row["id"], answer

        cid, fid, answer = prepare()
        webhook(cid, {"conversation": answer})
        assert process_one(sessions, settings, registry, media)
        check(
            "compra manual confirma com referência real",
            flow(cid)["state"] == "confirmed" and bool(flow(cid)["result"]["external_reference"]),
        )
        assert dispatch_one(sessions, media, settings, software_adapters=registry)

        cid, fid, answer = prepare()
        NetworkFault.drop_execution = True
        before = NetworkFault.execute_calls
        webhook(cid, {"conversation": answer})
        assert process_one(sessions, settings, registry, media)
        check("resposta perdida após commit fica incerta", flow(cid)["state"] == "unknown")
        assert_response(command(cid, fid, "reconcile"))
        check(
            "reconciliação recupera sem novo execute",
            flow(cid)["state"] == "confirmed" and NetworkFault.execute_calls == before + 1,
        )
        # Reconciliação não delega automaticamente: a confirmação fica sujeita ao controle humano.
        cid, fid, answer = prepare()
        with psycopg.connect(dburl(names[0])) as db:
            db.execute("UPDATE usuarios SET ativo=false WHERE id=%s", (uid,))
        webhook(cid, {"conversation": answer})
        before = NetworkFault.execute_calls
        process_one(sessions, settings, registry, media)
        check(
            "revogação antes de executar não lança",
            flow(cid)["state"] != "confirmed" and NetworkFault.execute_calls == before,
        )
        with psycopg.connect(dburl(names[0])) as db:
            db.execute("UPDATE usuarios SET ativo=true WHERE id=%s", (uid,))

        # Duas requisições reais, cada uma com sessão/conexão própria no servidor Fornada.
        cid, fid, answer = prepare()
        row = flow(cid)
        identity = {"business_id": bid, "sender_phone": phone, "operation": "purchases.review"}
        assert_response(
            fclient.post(
                "decision",
                json=identity
                | {
                    "proposal_id": row["source"]["id"],
                    "expected_version": row["source"]["version"],
                    "summary_hash": row["source"]["summary_hash"],
                    "approved": True,
                    "incoming_message_id": str(uuid4()),
                },
            )
        )
        operation = {
            "operation_id": str(uuid4()),
            "command_id": str(uuid4()),
            "business_id": bid,
            "capability_code": "stock.receive",
            "payload": {"proposal_ref": row["source"]["id"]},
            "idempotency_key": str(uuid4()),
            "principal_ref": uid,
            "scope": row["source"]["scope"],
            "conversation_id": cid,
            "expected_resource_version": str(row["source"]["version"]),
        }
        barrier = threading.Barrier(2)

        def concurrent_execute(_):
            barrier.wait(timeout=10)
            with httpx.Client(trust_env=False, timeout=30) as remote:
                return assert_response(
                    remote.post(
                        fornada_url + "/api/v1/central/execute",
                        headers={"Authorization": "Bearer " + token},
                        json=operation,
                    )
                )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(concurrent_execute, range(2)))
        check("execuções HTTP concorrentes devolvem a mesma compra", results[0] == results[1])
        cid, fid, answer = prepare()
        conv = assert_response(client.get(f"/api/conversations/{cid}", params={"business_id": bid}))
        assert_response(
            client.post(
                f"/api/conversations/{cid}/control",
                params={"business_id": bid},
                json={"mode": "human", "expected_version": conv["control_version"]},
            )
        )
        before = NetworkFault.execute_calls
        webhook(cid, {"conversation": answer})
        process_one(sessions, settings, registry, media)
        check(
            "assumir conversa impede execução automática",
            flow(cid)["state"] != "confirmed" and NetworkFault.execute_calls == before,
        )
        with psycopg.connect(dburl(names[0])) as db:
            check(
                "três compras confirmadas e três movimentos no total",
                db.execute("SELECT count(*) FROM compras WHERE tenant_id=%s", (tid,)).fetchone()[0]
                == 3
                and db.execute(
                    "SELECT count(*) FROM movimentacoes_estoque WHERE tenant_id=%s", (tid,)
                ).fetchone()[0]
                == 3,
            )
            check(
                "estoque final equivale a três entradas de 2 kg",
                db.execute(
                    "SELECT estoque_atual FROM ingredientes WHERE id=%s", (material_id,)
                ).fetchone()[0]
                == 6,
            )
        client.close()
        fclient.close()
        evidence["status"] = "passed"
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for handle in handles:
            handle.close()
        if proxy:
            proxy.shutdown()
            proxy.server_close()
        if engine:
            engine.dispose()
        with psycopg.connect(args.postgres_url, autocommit=True) as admin:
            for name in names:
                assert name.endswith(suffix) and name.startswith(
                    ("fornada_central_test_", "central_http_test_")
                )
                admin.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
                )
        evidence.setdefault("status", "failed")
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
