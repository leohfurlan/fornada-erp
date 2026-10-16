"""Na VPS Fornada, recebe credenciais por stdin; nunca imprime segredos."""

import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    root = Path('/opt/fornada')
    os.chdir(root)
    lock = (root / '.deploy.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    values = json.load(sys.stdin)
    required = {'EVOLUTION_API_URL', 'EVOLUTION_API_KEY', 'EVOLUTION_INSTANCE',
                'EVOLUTION_WEBHOOK_SECRET'}
    if set(values) != required or any('\n' in v or '\r' in v for v in values.values()):
        raise SystemExit('Credenciais inválidas')
    if values['EVOLUTION_API_URL'] != 'https://evolution.atospd.com':
        raise SystemExit('Destino inesperado')
    if len(values['EVOLUTION_WEBHOOK_SECRET']) < 32:
        raise SystemExit('Segredo inválido')
    values.update(EVOLUTION_ENABLED='true', WHATSAPP_AUTH_ENABLED='true',
                  FRONTEND_URL='https://fornada.atospd.com')
    env = root / '.env.production'
    original = env.read_text()
    stat = env.stat()
    backup = root / 'backups' / ('env-before-whatsapp-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.parent.mkdir(mode=0o700, exist_ok=True)
    backup.write_text(original)
    backup.chmod(0o600)
    lines = []
    seen = set()
    for line in original.splitlines():
        key = line.split('=', 1)[0].strip()
        if key in values:
            if key not in seen:
                lines.append(key + '=' + values[key])
                seen.add(key)
        else:
            lines.append(line)
    lines.extend(k + '=' + v for k, v in values.items() if k not in seen)
    dc = ['docker', 'compose', '--env-file', '.env.production', '-f',
          'docker-compose.prod.yml', '-f', 'docker-compose.micro.yml', '--profile', 'worker']
    try:
        env.write_text('\n'.join(lines) + '\n')
        env.chmod(0o600)
        os.chown(env, stat.st_uid, stat.st_gid)
        subprocess.run(dc + ['config', '--quiet'], check=True)
        subprocess.run(dc + ['up', '-d', '--no-build', '--no-deps', 'backend', 'celery'], check=True)
        for _ in range(40):
            health = subprocess.check_output(['docker', 'inspect', 'fornada-prod-backend-1',
                        '--format', '{{.State.Health.Status}}'], text=True).strip()
            if health == 'healthy':
                print('Backend saudável; worker ativado. Backup restrito:', backup.name)
                return
            time.sleep(2)
        raise RuntimeError('Backend não ficou saudável')
    except Exception:
        env.write_text(original)
        env.chmod(0o600)
        os.chown(env, stat.st_uid, stat.st_gid)
        subprocess.run(dc + ['up', '-d', '--no-build', '--no-deps', 'backend'], check=False)
        subprocess.run(dc + ['stop', 'celery'], check=False)
        raise SystemExit('Ativação falhou; configuração anterior restaurada') from None


if __name__ == '__main__':
    main()
