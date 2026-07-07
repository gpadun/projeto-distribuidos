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
  core/
    models.py            # Contratos de mensagens e entidades
    routing.py           # Hash deterministico de roteamento
    serialization.py     # Compatibilidade Pydantic v1/v2
  broker/
    connection.py        # Conexao RabbitMQ
    publisher.py         # Publicacao em exchanges topic
    subscriber.py        # Assinatura de topicos
  servers/
    adm_server.py        # Coordenacao, pedidos, heartbeats e eleicao
    tracker_server.py    # Rastreio e publicacao de localizacao
    support_server.py    # Backup dos rastreios de um R
  clients/
    mock_customer.py     # Simulador de cliente
    mock_driver.py       # Simulador de entregador
tests/
  test_routing.py
  test_models.py
  test_distributed_flow.py
docs/
  especificacao.md
  spec.md
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

Suba a API:

```bash
python main.py
```

A API fica em `http://127.0.0.1:8000`, com documentacao interativa em
`http://127.0.0.1:8000/docs`.

## Endpoints principais

- `POST /pedidos`: cria pedido e publica `PedidoDisponivel`;
- `POST /pedidos/aceitar`: associa entregador e servidor rastreador;
- `POST /pedidos/confirmar`: confirma entrega e publica `EntregaConfirmada`;
- `POST /infra/keepalive`: registra heartbeat;
- `POST /infra/eleicao`: executa eleicao Bully simplificada;
- `GET /estado`: inspeciona o estado atual do ADM.

## Observacao sobre RabbitMQ

Os modulos em `src/broker/` estao prontos para RabbitMQ real. Os testes usam
publicadores injetaveis em memoria para validar a logica sem exigir Docker ou
broker ativo.
