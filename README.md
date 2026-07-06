# Sistema Distribuído de Rastreamento de Entregas

## 1. Visão Geral

Este projeto implementa um sistema distribuído para rastreamento de entregas em
tempo real, desenvolvido como prova de conceito para a disciplina de Sistemas
Distribuídos.

A comunicação do sistema é híbrida:

- **Síncrona (Request/Response)** via FastAPI para operações pontuais, como a
  criação de um pedido (`CriarPedido`), a aceitação por um entregador
  (`AceitarPedido`) e a confirmação de entrega (`ConfirmarEntrega`).
- **Assíncrona (Publish/Subscribe)** via um Message Broker (RabbitMQ + `pika`)
  para eventos em tempo real, como a publicação da localização de um
  entregador (`LocalizacaoEntregador`) e sua entrega aos clientes assinantes
  (`EventoLocalizacao`).

O sistema é composto por três tipos de servidor, cada um com uma
responsabilidade distinta:

- **Servidor Administrador (ADM):** gerencia a eleição de líder (Bully
  Algorithm) e mantém o mapa de qual Servidor Rastreador é responsável por
  qual pedido.
- **Servidor Rastreador (R):** recebe localizações dos entregadores e
  gerencia as conexões ativas com os clientes.
- **Servidor de Suporte (SUP):** mantém um backup dos rastreios de um
  Servidor Rastreador específico, usado para recuperação em caso de falha.

A distribuição de carga entre Servidores Rastreadores é feita por hash
determinístico (`hash(idPedido) mod N`), e a consistência dos dados de
localização é eventual, resolvida por comparação de timestamps.

Os detalhes completos de arquitetura e regras de negócio estão documentados
em [`docs/spec.md`](docs/spec.md) e [`docs/especificacao.md`](docs/especificacao.md).

## 2. Arquitetura de Pastas

```
src/
├── core/       # Contratos de dados e lógica de domínio pura
│   ├── models.py    # Modelos Pydantic de todas as mensagens e entidades da spec
│   └── routing.py   # Hash determinístico para descoberta do servidor responsável
├── broker/     # Camada de integração com o Message Broker (RabbitMQ/pika)
│   ├── connection.py  # Gerenciamento da conexão com o broker
│   ├── publisher.py   # Publicação de eventos (Publish)
│   └── subscriber.py  # Assinatura de eventos (Subscribe)
├── servers/    # Os três papéis de servidor descritos na spec
│   ├── adm_server.py       # Servidor Administrador
│   ├── tracker_server.py   # Servidor Rastreador (R)
│   └── support_server.py   # Servidor de Suporte (SUP)
└── clients/    # Simuladores usados para testes sem dispositivos reais
    ├── mock_driver.py     # Simula um entregador publicando localizações
    └── mock_customer.py   # Simula um cliente criando pedidos e assinando rastreio

tests/          # Testes automatizados (pytest), espelhando a estrutura de src/
docs/           # Fonte da verdade: especificação de arquitetura e regras de negócio
```

A dependência entre camadas segue uma direção única: `servers/` e `clients/`
dependem de `core/` e `broker/`, mas `core/` não depende de nenhuma outra
camada do projeto — ele contém apenas os contratos de dados e a lógica de
domínio pura (ex: o hash de roteamento).

## 3. Metodologia: Spec-Driven Development (SDD)

Este projeto segue a metodologia **Spec-Driven Development**: nenhuma linha de
código de negócio é escrita sem uma base clara e explícita nos documentos da
pasta [`docs/`](docs/). Se uma especificação estiver ambígua ou incompleta, o
passo correto é esclarecê-la antes de implementar — não inventar
comportamento.

O arquivo [`CLAUDE.md`](CLAUDE.md), na raiz do repositório, define as regras
de colaboração com o assistente de IA usado no desenvolvimento deste projeto
(Claude Code). Ele estabelece que:

- A pasta `docs/` é a fonte da verdade para toda decisão de implementação.
- O desenvolvimento deve ocorrer em passos curtos e incrementais, com
  validação humana entre cada etapa.
- Não deve haver reescrita de arquivos inteiros ou introdução de bibliotecas
  além do estritamente necessário para a tarefa em questão.

**Se você (colega de grupo) for continuar este projeto com ajuda de IA,
leia o `CLAUDE.md` antes de pedir novas implementações** — ele garante que o
assistente siga o mesmo fluxo de trabalho (ler a spec, planejar, validar,
executar, testar) usado até aqui, mantendo consistência entre as
contribuições do grupo.

## 4. Como Rodar o Projeto

### Pré-requisitos

- Python 3.10 ou superior

### Passo a passo

1. Crie e ative o ambiente virtual (a partir da raiz do repositório):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Rode os testes de roteamento (hash determinístico de distribuição de
   pedidos entre Servidores Rastreadores):

   ```bash
   pytest tests/test_routing.py -v
   ```

> **Nota:** `tests/test_models.py` ainda é um esqueleto (assinaturas de teste
> sem implementação, aguardando a próxima etapa do SDD) e falha
> propositalmente se executado. Por isso, `pytest` sem argumentos ainda não
> passa por completo — use o caminho específico acima enquanto isso não for
> implementado.

Para desativar o ambiente virtual quando terminar, use `deactivate`.
