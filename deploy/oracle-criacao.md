# Criar a VPS gratuita para o Fornada

Guia conferido em 06/10/2026. A VM ainda não foi criada. Este roteiro descreve
ações no console da Oracle; não provisiona recursos automaticamente.

## 1. Região e cota

No console https://cloud.oracle.com/, usar a home region da conta.
Conferir a cota em Governance & Administration → Limits, Quotas and Usage.
Configuração pretendida: uma VM.Standard.A1.Flex com 2 OCPUs e 12 GB RAM.
Somar os recursos de outras VMs A1 antes de alocar. Disco inicial: 50 GB.
Verificar elegibilidade Always Free da imagem e dos recursos, sem depender dos
créditos temporários do trial.

Fonte da cota e do armazenamento:
https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm.

## 2. Rede

Networking → Virtual Cloud Networks → Start VCN Wizard → Create VCN with
Internet Connectivity. Se já houver uma VCN adequada, reutilizá-la.
Nome: fornada-vcn. IPv4 VCN: 10.20.0.0/16; subnet pública: 10.20.0.0/24;
subnet privada: 10.20.1.0/24. Confirmar que não conflitam com redes existentes.
Nesta etapa, não habilitar IPv6.

O wizard pode criar NAT Gateway e Service Gateway além do Internet Gateway;
verificar os recursos mostrados antes de concluir. A VM do piloto utiliza a
subnet pública e a rota de saída 0.0.0.0/0 pelo Internet Gateway.

Fonte: https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/quickstartnetworking.htm.

## 3. Instância

Compute → Instances → Create instance.

| Campo | Valor escolhido para o piloto |
| --- | --- |
| Nome | fornada-piloto |
| Imagem | Canonical Ubuntu 24.04 LTS compatível com ARM |
| Shape | Ampere → VM.Standard.A1.Flex |
| OCPUs / memória | 2 / 12 GB |
| Rede | fornada-vcn, subnet pública |
| IPv4 público | Atribuir automaticamente |
| Disco de boot | 50 GB; desempenho padrão elegível gratuito |
| Chaves SSH | Generate a key pair for me ou chave pública existente |

Preferir Ubuntu padrão. Não selecionar Windows, imagem paga de Marketplace,
GPU ou outra shape para contornar indisponibilidade.
Se gerar chave no console, baixar a chave privada e pública antes de criar a VM.
Guardar a privada fora do repositório e não enviar seu conteúdo no chat.
Revisar o resumo e concluir Create. Se houver "out of host capacity", tentar
outro availability domain da mesma home region ou aguardar.

Fonte: https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm.

## 4. SSH na rede

Networking → Virtual Cloud Networks → fornada-vcn → subnet pública → Security
Lists → lista associada → Ingress Rules. A regra efetiva deve permitir TCP 22
somente a partir do IPv4 público da sua conexão, com máscara /32. Usar porta
de origem All e porta de destino 22; regra stateful.
Se houver regra SSH aberta para 0.0.0.0/0, restringi-la. Verificar também NSGs
ligados à VM: regras são aditivas; uma regra ampla em outro grupo continua aberta.
Se sua conexão trocar de IP, atualizar a origem da regra.

Para o piloto por túnel, não abrir 80/443 nem 8080. Não alterar indiscriminadamente
regras ICMP ou de saída criadas pelo wizard.

## 5. Primeira conexão

Esperar Running e copiar o IPv4 público da VM. No PowerShell do Windows:

```powershell
ssh -i "C:\Users\Leonardo\.ssh\fornada-oracle.key" ubuntu@IP_PUBLICO_DA_VPS
```

Substituir caminho da chave e IP pelos valores reais. Conferir que está acessando
a VM correta antes de aceitar a chave do host na primeira conexão.
Se houver erro "UNPROTECTED PRIVATE KEY FILE", corrigir as permissões do arquivo
local; se houver timeout, revisar IP público, subnet, rota e regra TCP 22.

Dentro da VPS, executar somente a inspeção inicial:

```sh
cat /etc/os-release
uname -m
free -h
df -h /
```

Esperado: Ubuntu 24.04 e aarch64. RAM e disco podem aparecer menores que o tamanho
nominal por unidades/reservas. Usuário Ubuntu é ubuntu; Oracle Linux usa opc.
Fonte: https://docs.oracle.com/en-us/iaas/Content/Compute/tutorials/first-linux-instance/overview.htm.

## 6. Preparação após confirmar a VM

Instalar Docker Engine pelo repositório oficial para Ubuntu e os plugins
docker-buildx-plugin/docker-compose-plugin. Validar `sudo docker version` e
`sudo docker compose version` (2.24.4+). O passo completo será aplicado somente
após confirmar sistema, arquitetura e conectividade.
Fonte: https://docs.docker.com/engine/install/ubuntu/.

Depois, seguir [homologação privada](oracle.md). O código atualizado ainda está
no working tree local: clonar o GitHub sozinho pode não incluir as preparações
desta revisão. Transferir apenas fontes e configurações necessárias; não enviar
.env, chave SSH, node_modules, .venv ou .git com um upload indiscriminado.

Manter backup fora da VM, pois instâncias Always Free ociosas podem ser recuperadas
pela Oracle conforme sua política. Não criar carga artificial para evitar isso.

## Roteiro interativo opcional

O script `deploy/oracle-wizard.sh` apresenta as etapas de criação e registra somente
metadados públicos em `.env.oracle-setup.local`, ao lado dele. Não instala nem
executa comandos na VPS. Requer Git Bash ou WSL; não exige chave privada.
No Git Bash, a partir da raiz do projeto:

```sh
bash deploy/oracle-wizard.sh
```
