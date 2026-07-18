# Sistema Distribuido de Rastreamento de Entregas

Prova de conceito para a disciplina de Sistemas Distribuidos. O sistema combina:

- comunicacao sincrona via FastAPI para comandos como `CriarPedido`,
  `AceitarPedido` e `ConfirmarEntrega`;
- comunicacao assincrona via RabbitMQ/pika para eventos publish-subscribe como
  `PedidoDisponivel`, `EventoLocalizacao` e `EntregaConfirmada`;
- roteamento deterministico por consistent hashing com nos virtuais;
- tolerancia a falhas com heartbeat, redistribuicao de rastreios e backup em
  servidor SUP;
- eleicao de lider ADM pelo Bully Algorithm simplificado, em que o maior ID vira
  lider.

## Estrutura

```text
src/
  api.py                 # API FastAPI para comandos sincronos
  broker/
    config.py            # Configuracao RabbitMQ via env vars
    topology.py          # Exchanges e routing keys
    factory.py           # Factory de Publisher/Subscriber
    connection.py        # Conexao RabbitMQ
    publisher.py         # Publicacao em exchanges topic
    subscriber.py        # Assinatura de topicos
  infra/
    adm_transport.py     # Transporte HTTP entre ADMs
  core/
    models.py            # Contratos de mensagens e entidades
    routing.py           # Hash deterministico de roteamento
    serialization.py     # Compatibilidade Pydantic v1/v2
  servers/
    adm_server.py        # Coordenacao, pedidos, heartbeats e eleicao
    tracker_server.py    # Rastreio e publicacao de localizacao
    support_server.py    # Backup dos rastreios de um R
  clients/
    mock_customer.py     # Simulador de cliente
    mock_driver.py       # Simulador de entregador
scripts/
  start_adm.ps1          # Sobe um ADM
  start_cluster.ps1      # Sobe cluster de 3 ADMs
  demo_estado.ps1        # Consulta estado dos ADMs
  demo_pedido.ps1        # Testa criacao de pedido
tests/
  test_routing.py
  test_models.py
  test_distributed_flow.py
  test_broker_integration.py
docker-compose.yml       # RabbitMQ local
docs/
  especificacao.md
  spec.md
  status_projeto.md
```

A dependencia entre camadas segue uma direcao unica: `servers/` e `clients/`
dependem de `core/` e `broker/`, mas `core/` nao depende de nenhuma outra
camada do projeto. Ele contem apenas os contratos de dados e a logica de dominio
pura, como o roteamento por consistent hashing.

## Metodologia: Spec-Driven Development (SDD)

Este projeto segue a metodologia **Spec-Driven Development**: nenhuma linha de
codigo de negocio deve ser escrita sem uma base clara e explicita nos documentos
da pasta [`docs/`](docs/) e no arquivo
[`Trabalho DSID Especificacoes.pdf`](docs/Trabalho%20DSID%20Especificacoes.pdf). Se uma
especificacao estiver ambigua ou incompleta, o passo correto e esclarecer antes
de implementar, nao inventar comportamento.

Regras praticas para continuar o projeto:

- A especificacao do trabalho e a fonte da verdade para toda decisao de
  implementacao.
- O desenvolvimento deve ocorrer em passos curtos e incrementais.
- Cada etapa deve ser validada com testes ou com um roteiro de demonstracao.
- Novas dependencias devem ser introduzidas apenas quando forem necessarias para
  cumprir a especificacao.
- O checklist em [`docs/status_projeto.md`](docs/status_projeto.md) deve ser
  atualizado sempre que uma etapa for concluida.

## Como Rodar o Projeto

Crie o ambiente e instale as dependencias:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Rode os testes:

```bash
pytest -q
```

Com RabbitMQ rodando (`docker compose up -d`), a suite completa passa com
**75 testes**. Sem o broker, os 3 testes de integracao sao pulados
(**72 passed, 3 skipped**).

Suba a API:

```bash
python main.py
```

A API fica em `http://127.0.0.1:8000`, com documentacao interativa em
`http://127.0.0.1:8000/docs`.

## Demo com 3 processos ADM

Esta demonstracao sobe tres instancias ADM independentes, cada uma em uma porta
diferente, comunicando-se por HTTP (keepalive, eleicao Bully e propagacao de
novo lider). Comandos de pedido (`CriarPedido`, `AceitarPedido`,
`ConfirmarEntrega`) so sao aceitos pelo lider atual; os demais ADMs respondem
com HTTP 409 e indicam qual servidor e o lider.

### Pre-requisitos

- Ambiente virtual ativado e dependencias instaladas (ver secao anterior).
- RabbitMQ rodando (`docker compose up -d`) para publicar eventos reais.
- Scripts em `scripts/`:
  - `start_adm.ps1` — sobe um ADM com variaveis de ambiente corretas;
  - `start_cluster.ps1` — abre tres terminais (adm-1, adm-2, adm-3);
  - `demo_estado.ps1` — consulta lider e estado dos tres ADMs;
  - `demo_pedido.ps1` — tenta criar pedido em um ADM especifico.

### Subir o cluster

Na raiz do projeto:

```powershell
.\scripts\start_cluster.ps1
```

Isso inicia:

| ADM   | URL                      | Docs Swagger               |
|-------|--------------------------|----------------------------|
| adm-1 | http://127.0.0.1:8001    | http://127.0.0.1:8001/docs |
| adm-2 | http://127.0.0.1:8002    | http://127.0.0.1:8002/docs |
| adm-3 | http://127.0.0.1:8003    | http://127.0.0.1:8003/docs |

Aguarde **5 a 10 segundos** para os heartbeats entre os ADMs. Depois confira:

```powershell
.\scripts\demo_estado.ps1
```

Estado esperado no inicio (maior ID vira lider):

| ADM   | souLider | liderAtual |
|-------|----------|------------|
| adm-1 | false    | adm-3      |
| adm-2 | false    | adm-3      |
| adm-3 | true     | adm-3      |

### Cenario 1 — operacao normal

**1. Consultar o lider:**

```powershell
Invoke-RestMethod http://127.0.0.1:8001/infra/lider
Invoke-RestMethod http://127.0.0.1:8003/infra/lider
```

**2. Tentar criar pedido em um ADM que nao e lider (deve retornar 409):**

```powershell
.\scripts\demo_pedido.ps1 -Url "http://127.0.0.1:8001"
```

**3. Criar pedido no lider (deve retornar 200):**

```powershell
.\scripts\demo_pedido.ps1 -Url "http://127.0.0.1:8003"
```

**4. Inspecionar o estado do lider:**

```powershell
Invoke-RestMethod http://127.0.0.1:8003/estado
```

O campo `pedidos` deve listar o UUID criado. Com RabbitMQ ativo, `rabbitmqHabilitado`
deve ser `true`.

### Cenario 2 — falha do lider e nova eleicao

**1. Encerre o processo do lider (`adm-3`)** — feche o terminal ou use Ctrl+C.

**2. Aguarde cerca de 10 a 15 segundos** para o timeout de heartbeat e a nova
eleicao (intervalo de monitoramento: 5 s; timeout de heartbeat: 10 s).

**3. Verifique o novo lider:**

```powershell
.\scripts\demo_estado.ps1
```

Estado esperado apos a falha:

| ADM   | souLider | liderAtual |
|-------|----------|------------|
| adm-1 | false    | adm-2      |
| adm-2 | true     | adm-2      |
| adm-3 | offline  | —          |

**4. Criar pedido no novo lider:**

```powershell
.\scripts\demo_pedido.ps1 -Url "http://127.0.0.1:8002"
```

**5. Confirmar que adm-1 ainda rejeita o comando:**

```powershell
.\scripts\demo_pedido.ps1 -Url "http://127.0.0.1:8001"
```

Deve retornar 409 com `liderAtual: adm-2`.

### Subir um ADM manualmente (alternativa)

Em vez de `start_cluster.ps1`, abra tres terminais e configure as variaveis
conforme `scripts/start_adm.ps1`.

## RabbitMQ (Message Broker)

O sistema usa **RabbitMQ** com exchanges do tipo **topic** para eventos
assincronos. Comandos de pedido continuam via HTTP/FastAPI; eventos como
`PedidoDisponivel` vao pelo broker.

### Subir o broker

Requisito: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
instalado.

Na raiz do projeto:

```powershell
docker compose up -d
docker compose ps
```

O container `dsid-rabbitmq` deve ficar `healthy`.

### Painel de administracao

| Item    | Valor                        |
|---------|------------------------------|
| URL     | http://localhost:15672       |
| Usuario | `dsid`                       |
| Senha   | `dsid123`                    |

No painel voce pode inspecionar exchanges, filas e mensagens publicadas durante
a demo.

### Variaveis de ambiente

Copie `.env.example` para `.env` (opcional):

```powershell
Copy-Item .env.example .env
```

| Variavel                  | Descricao                                | Padrao                   |
|---------------------------|------------------------------------------|--------------------------|
| `RABBITMQ_HOST`           | Host do broker                           | `localhost`              |
| `RABBITMQ_PORT`           | Porta AMQP                               | `5672`                   |
| `RABBITMQ_USER`           | Usuario                                  | `dsid`                   |
| `RABBITMQ_PASSWORD`       | Senha                                    | `dsid123`                |
| `RABBITMQ_ENABLED`        | `1` conecta o ADM ao broker; `0` desliga | `0`                      |
| `RABBITMQ_MANAGEMENT_URL` | URL do painel web                        | `http://localhost:15672` |

Os scripts `start_adm.ps1` e `start_cluster.ps1` ja definem `RABBITMQ_ENABLED=1`.

### Topologia de mensagens

| Exchange   | Routing key                        | Publicado por | Consumido por (futuro) |
|------------|------------------------------------|---------------|------------------------|
| `pedidos`  | `pedido.disponivel`                | ADM (lider)   | Entregador             |
| `pedidos`  | `pedido.{id}.entrega_confirmada`   | ADM (lider)   | Entregador             |
| `infra`    | `roteamento.{servidor_rastreador}` | ADM (lider)   | Rastreador R           |
| `rastreio` | `pedido.{id}`                      | Rastreador R  | Cliente                |
| `rastreio` | `pedido.{id}.desconexao`           | Rastreador R  | Cliente / ADM          |

Definicoes centralizadas em `src/broker/topology.py`.

### Validar publicacao manual

Com RabbitMQ e ADM lider rodando (`RABBITMQ_ENABLED=1`):

```powershell
.\scripts\demo_pedido.ps1 -Url "http://127.0.0.1:8003"
```

No painel RabbitMQ, aba **Exchanges**, deve aparecer a exchange `pedidos` apos o
primeiro pedido.

### Testes com RabbitMQ real

Testes de integracao (exigem broker rodando):

```powershell
docker compose up -d
pytest -q -m integration
```

Esperado: **3 passed**.

Suite completa:

```powershell
pytest -q
```

Esperado: **75 passed** (com Docker) ou **72 passed, 3 skipped** (sem Docker).

Rodar sem integracao:

```powershell
pytest -q -m "not integration"
```

### Comandos uteis do Docker

```powershell
docker compose stop      # parar broker
docker compose start     # subir novamente
docker compose down      # remover container (volume permanece)
docker compose down -v   # remover container e dados
docker compose logs -f rabbitmq
```

## Endpoints principais

### Comandos (somente no lider ADM)

- `POST /pedidos`: cria pedido e publica `PedidoDisponivel`;
- `POST /pedidos/aceitar`: associa entregador e servidor rastreador;
- `POST /pedidos/confirmar`: confirma entrega e publica `EntregaConfirmada`.

Resposta **409** em nao-lideres, com `liderAtual` no corpo.

### Infraestrutura ADM

- `POST /infra/keepalive`: registra heartbeat;
- `POST /infra/eleicao`: executa eleicao Bully;
- `POST /infra/eleicao/iniciar`: recebe inicio de eleicao;
- `POST /infra/eleicao/resposta`: recebe resposta de eleicao;
- `POST /infra/eleicao/novo-lider`: propaga novo lider;
- `POST /infra/replicar-roteamento`: replica mapa pedido → rastreador entre ADMs;
- `GET /infra/lider`: consulta lider atual;
- `GET /estado`: inspeciona estado do ADM (inclui `rabbitmqHabilitado`).

Documentacao interativa: `http://127.0.0.1:8000/docs` (ou porta do ADM).

## Roteiro rapido de apresentacao (5 minutos)

### Cluster ADM + eleicao

1. `docker compose up -d` — painel RabbitMQ em `:15672`
2. `.\scripts\start_cluster.ps1` — 3 ADMs
3. `.\scripts\demo_estado.ps1` — lider inicial `adm-3`
4. Matar adm-3 → aguardar ~15s → logs `[adm ...] novo lider eleito: adm-2`
5. `.\scripts\demo_pedido.ps1` no adm-1 → 409; no lider → 200

### Fluxo E2E (pedido → rastreio → confirmacao)

1. `.\scripts\start_support.ps1` (9101) e `-IdServidor sup-2 -IdRastreador rastreador-2 -Port 9102`
2. `.\scripts\start_tracker.ps1` e `-IdServidor rastreador-2`
3. `.\scripts\start_driver.ps1`
4. `.\scripts\start_customer.ps1 -Acao demo`
5. Acompanhar logs:
   - ADM: `[adm] pedido criado`, `pedido aceito ... rastreador=...`
   - Entregador: `pedido disponivel`, `pedido aceito`
   - Rastreador: `pedido ... atribuido`, `localizacao recebida`
   - Cliente: `localizacao: pedido=...`
   - SUP: `sync recebido ...`

### Failover de rastreador

1. Com fluxo E2E rodando, matar o rastreador do log do entregador
2. Aguardar ~15s
3. ADM: `falha detectada`, `backup recebido do SUP`, `pedido redistribuido`
4. SUP: `backup enviado ao ADM`
5. Entregador: `rastreador atualizado pedido=... -> rastreador-2`
6. `.\scripts\demo_falha_rastreador.ps1` — confirmar roteamento no R2

Logs podem ser silenciados com `PRESENTATION_LOG=0`.

## O que ainda nao esta nesta versao

- Teste automatizado de falha com multiplos processos reais
- Exemplos de payload HTTP no README
- Secao unificada no README com todos os comandos de subida
