# Ativação do login por WhatsApp

O código do fluxo está implementado, mas o envio real permanece desativado. Não houve instalação da Evolution nem envio de mensagens nesta execução.

## Contrato verificado

Adaptador usa `POST /message/sendText/{instance}`, header `apikey` e corpo com `number` (E.164 sem o sinal +) e `text`. Referências primárias consultadas em 06/10/2026:

- [Router de mensagens da Evolution](https://github.com/EvolutionAPI/evolution-api/blob/main/src/api/routes/sendMessage.router.ts)
- [DTO de mensagem de texto](https://github.com/EvolutionAPI/evolution-api/blob/main/src/api/dto/sendMessage.dto.ts)

Conferir a versão efetivamente instalada antes de ativar. Resposta HTTP aceita significa aceitação do envio pela API, não comprovação de entrega ao aparelho.

## Configuração necessária

```dotenv
WHATSAPP_AUTH_ENABLED=false
EVOLUTION_API_URL=https://sua-evolution.exemplo.com
EVOLUTION_API_KEY=preencher-no-servidor
EVOLUTION_INSTANCE=instancia-conectada
```

Primeiro configurar uma instância conectada e validar envio para um número de teste autorizado. Só depois habilitar a flag. O backend exige HTTPS em produção. Credenciais permanecem fora do navegador e do Git. O Compose repassa essas variáveis ao backend.

O login usa Redis para desafios, provas e limites. Cache indisponível retorna erro recuperável; não existe código fixo nem bypass de produção. TTL do código 5 minutos, prova 10 minutos, até 5 tentativas, reenvio após 60 segundos, até 5 envios por telefone/hora e 20 por IP/hora. O IP é o observado pelo servidor; para acesso público por proxy, configurar encaminhamento e confiança do proxy de forma restrita antes de ampliar o piloto.

## Contas existentes

Entrar por e-mail e abrir Configurações → Acesso por WhatsApp. Validar o número e vinculá-lo à sessão atual. Não existe associação automática baseada no e-mail digitado. A troca de número já vinculado exige recuperação assistida; recuperação autônoma ainda não foi implementada.

## Limites da validação atual

Redis real foi usado para verificar expiração, tentativas, consumo único e concorrência. O onboarding/login foi testado com transporte capturado, sem mensagens externas. A interface móvel usou respostas fictícias do provedor. Ainda falta testar conexão/entrega da instância real antes da ativação.
