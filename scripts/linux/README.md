# Scripts Linux (equivalentes aos `.ps1`)

Estes scripts fazem, em bash, exatamente o que os `.ps1` da pasta `scripts/`
fazem no Windows: exportam as mesmas variáveis de ambiente e chamam o
mesmo `main.py` / `support_main.py` / módulo Python. Os `.ps1` continuam
intactos para quem usa Windows.

Rode tudo a partir da raiz do projeto, com o `.venv` já criado:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
chmod +x scripts/linux/*.sh   # só na primeira vez
```

## Scripts disponíveis

| Script | Equivalente Windows | Uso |
|---|---|---|
| `start_cluster.sh` | `start_cluster.ps1` | `./scripts/linux/start_cluster.sh` — tenta abrir 3 terminais (adm-1/2/3); se não achar um emulador conhecido, imprime os comandos para rodar manualmente |
| `start_adm.sh` | `start_adm.ps1` | `./scripts/linux/start_adm.sh <adm-id> <port>` — ex: `start_adm.sh adm-1 8001` |
| `start_support.sh` | `start_support.ps1` | `./scripts/linux/start_support.sh [id-servidor] [id-rastreador] [porta]` — padrão: `sup-1 rastreador-1 9101` |
| `start_tracker.sh` | `start_tracker.ps1` | `./scripts/linux/start_tracker.sh [id-servidor] [adm-url] [sup-url]` — padrão: `rastreador-1`, líder detectado automaticamente |
| `start_driver.sh` | `start_driver.ps1` | `./scripts/linux/start_driver.sh [id-entregador] [adm-url]` — padrão: `entregador-1` |
| `start_restaurant.sh` | `start_restaurant.ps1` | `./scripts/linux/start_restaurant.sh [id-restaurante] [adm-url] [--sem-preparo-auto]` |
| `start_customer.sh` | `start_customer.ps1` | `./scripts/linux/start_customer.sh [id-cliente] [acao] [id-pedido] [id-restaurante] [adm-url]` — `acao`: `criar`\|`rastrear`\|`demo`\|`confirmar` |
| `demo_estado.sh` | `demo_estado.ps1` | `./scripts/linux/demo_estado.sh` |
| `demo_roteamento.sh` | `demo_roteamento.ps1` | `./scripts/linux/demo_roteamento.sh` |
| `demo_falha_rastreador.sh` | `demo_falha_rastreador.ps1` | `./scripts/linux/demo_falha_rastreador.sh [adm-url]` |
| `demo_pedido.sh` | `demo_pedido.ps1` | `./scripts/linux/demo_pedido.sh [url] [tentativas]` |
| `resolve_adm_lider.sh` | `resolve_adm_lider.ps1` | não roda sozinho — é `source`d pelos outros scripts para descobrir o líder ADM atual |

## O que NÃO foi portado

`validate_cluster_manual.ps1` não tem equivalente aqui. Ele sobe o cluster
inteiro em background, espera condições específicas via polling e mata o
líder automaticamente — é bastante complexo de portar com a mesma robustez
em bash. Para o teste de failover do ADM líder, siga os passos manuais
(Bloco 6 de `roteiro.md` / seção "Failover do ADM líder" em `teste.txt`),
que reproduzem o mesmo cenário passo a passo.

## Exemplo de sequência completa

```bash
./scripts/linux/start_cluster.sh          # ou start_adm.sh manual em 3 terminais
sleep 10
./scripts/linux/demo_estado.sh

./scripts/linux/start_support.sh                                  # sup-1 / rastreador-1 / 9101
./scripts/linux/start_support.sh sup-2 rastreador-2 9102          # em outro terminal

./scripts/linux/start_tracker.sh                                  # rastreador-1
./scripts/linux/start_tracker.sh rastreador-2                     # em outro terminal

./scripts/linux/start_driver.sh
./scripts/linux/start_restaurant.sh
./scripts/linux/start_customer.sh cliente-1 demo

./scripts/linux/demo_roteamento.sh
./scripts/linux/start_customer.sh cliente-1 confirmar "UUID-DO-PEDIDO"
```
