# Resumo da Especificacao do Trabalho DSID

Fonte principal: [`Trabalho DSID Especificacoes.pdf`](Trabalho%20DSID%20Especificacoes.pdf).

## Visao Geral

Sistema distribuido para administrar o rastreio de entregadores por clientes,
minimizando o impacto percebido quando componentes falham.

## Arquitetura

- Modelo fisico: cliente-servidor em nuvem.
- Modelo logico: publish-subscribe/event-based.
- Arquitetura interna: camadas, com clientes simples de console ou web.
- Restaurantes: pre-cadastrados/hardcoded para simplificar a prova de conceito.
- Entregadores: simulados por scripts que enviam latitude, longitude e timestamp.

## Comunicacao

- Operacoes pontuais usam request/response, implementadas com FastAPI.
- Eventos de rastreio usam publish-subscribe por Message Broker.
- A implementacao usa RabbitMQ com `pika`.

## Mensagens

Comandos:

- `CriarPedido`: `idPedido`, `idCliente`, `idRestaurante`, `timestamp`.
- `AceitarPedido`: `idPedido`, `idEntregador`, `timestamp`.
- `ConfirmarEntrega`: `idPedido`, `idCliente`, `timestamp`.

Eventos:

- `PedidoDisponivel`: `idPedido`, `idRestaurante`, `timestamp`.
- `LocalizacaoEntregador`: `idEntregador`, `idPedido`, `latitude`, `longitude`, `timestamp`.
- `EventoLocalizacao`: `idPedido`, `latitude`, `longitude`, `timestamp`.
- `SubscribeRastreio`: `idPedido`, `idServidorRastreador`.

Infraestrutura:

- `keepAlive`: `idServidor`, `tipoServidor`, `timestamp`.
- `AtualizacaoRoteamento`: atualiza qual servidor rastreador esta responsavel por quais pedidos.

## Roteamento

O PDF especifica consistent hashing com nos virtuais:

- cada Servidor Rastreador e inserido em um anel logico;
- cada no virtual usa `hash(idServidor + "#" + indice)`;
- cada pedido usa `hash(idPedido)`;
- o servidor responsavel e o primeiro no virtual no sentido horario.

## Consistencia e Falhas

- Modelo de consistencia eventual.
- Atualizacoes de localizacao usam timestamp; a mais recente substitui as antigas.
- Nao ha necessidade de exclusao mutua distribuida para localizacao.
- Falhas sao detectadas por ausencia de `keepAlive`.
- O ADM redistribui rastreios quando um servidor R falha.
- O SUP mantem uma lista secundaria dos rastreios do servidor R associado.
- A eleicao entre ADMs usa Bully Algorithm: o maior ID ativo torna-se lider.

## Componentes

ADM:

- acompanha disponibilidade dos servidores R;
- mantem pedidos ainda sem entregador;
- mantem relacao pedido -> servidor rastreador;
- redistribui pedidos em falhas;
- participa da eleicao de lider.

Rastreador:

- mantem entregadores conectados;
- guarda a localizacao mais recente;
- publica/encaminha localizacao para os assinantes;
- notifica desconexao de entregador.

SUP:

- mantem backup dos rastreios de um R;
- envia a lista de backup quando o ADM detecta falha do R.
