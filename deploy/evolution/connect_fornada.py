"""Na VPS Evolution: exportação por pipe SSH e configuração autenticada do webhook."""

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

from configure import load_env


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['export', 'enable', 'verify', 'disable'])
    args = parser.parse_args()
    env = load_env(Path('/opt/evolution-fornada/.env'))
    if args.action == 'export':
        # Apenas para stdout canalizado diretamente ao SSH da Fornada; não executar no terminal.
        print(json.dumps({
            'EVOLUTION_API_URL': env['SERVER_URL'],
            'EVOLUTION_API_KEY': env['FORNADA_INSTANCE_TOKEN'],
            'EVOLUTION_INSTANCE': env['FORNADA_INSTANCE'],
            'EVOLUTION_WEBHOOK_SECRET': env['FORNADA_WEBHOOK_SECRET'],
        }))
        return
    url = 'https://fornada.atospd.com/api/v1/whatsapp/webhook'

    def request(route, data=None):
        req = urllib.request.Request('http://127.0.0.1:8081/' + route,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'apikey': env['FORNADA_INSTANCE_TOKEN'], 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    if args.action in {'enable', 'disable'}:
        request('webhook/set/' + env['FORNADA_INSTANCE'], {'webhook': {
            'enabled': args.action == 'enable', 'url': url,
            'events': ['MESSAGES_UPSERT'], 'byEvents': False, 'base64': False,
            'headers': {'X-Webhook-Secret': env['FORNADA_WEBHOOK_SECRET']},
        }})
    config = request('webhook/find/' + env['FORNADA_INSTANCE'])
    print('Webhook:', bool(config.get('enabled')), 'URL:', config.get('url'),
          'eventos:', config.get('events'))
    if args.action == 'disable':
        return
    assert config.get('enabled') and config.get('url') == url
    assert config.get('headers', {}).get('X-Webhook-Secret') == env['FORNADA_WEBHOOK_SECRET']
    assert config.get('events') == ['MESSAGES_UPSERT']
    assert config.get('webhookByEvents') is False and config.get('webhookBase64') is False
    # Evento próprio: testa autenticação/contrato sem enviar mensagens ou alterar dados.
    payload = {'instance': env['FORNADA_INSTANCE'], 'event': 'messages.upsert',
               'data': {'key': {'fromMe': True}, 'message': {}}}
    for authenticated in (False, True):
        headers = {'Content-Type': 'application/json'}
        if authenticated:
            headers['X-Webhook-Secret'] = env['FORNADA_WEBHOOK_SECRET']
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                code = response.status
                body = json.load(response)
        except urllib.error.HTTPError as exc:
            code, body = exc.code, {}
        print('Webhook autenticado' if authenticated else 'Webhook sem segredo', code)
        assert code == (202 if authenticated else 401)
        if authenticated:
            assert body == {'status': 'ignorado'}
    print('Contrato HTTPS e segredo validados; sem mensagem real enviada.')


if __name__ == '__main__':
    main()
