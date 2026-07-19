# Especificacao Implementavel do Projeto

Este arquivo consolida, em formato de trabalho do repositorio, as regras do
arquivo [`Trabalho DSID Especificacoes.pdf`](Trabalho%20DSID%20Especificacoes.pdf).
Em caso de conflito, o PDF e a
fonte de verdade.

## 1. Introducao

O sistema administra o rastreamento de entregadores por clientes. O foco e
tolerar falhas de componentes de forma que o cliente perceba o minimo possivel
enquanto o sistema se reorganiza.

## 2. Modelo Arquitetural

O modelo fisico e cliente-servidor em nuvem: cliente, entregador e restaurante
atuam como clientes e nao se comunicam diretamente.

O modelo logico e publish-subscribe/event-based. O entregador publica
localizacoes, o Servidor Rastreador responsavel consome e mantem o estado mais
recente, e os clientes acompanham o rastreio do pedido.

## 3. Software Interno

A prova de conceito usa aplicacoes simples de console ou web. Os restaurantes
sao pre-cadastrados e os entregadores sao simulados por scripts que enviam
latitude, longitude e timestamp periodicamente.

O restaurante tambem pode rodar como processo simples de demonstracao. Ele
assina `PedidoDisponivel` no broker, filtra pedidos pelo seu `idRestaurante` e
envia `PrepararPedido` ao ADM lider quando o pedido foi preparado.

## 4. Middleware

O sistema usa Message Broker como middleware orientado a mensagens. Neste
repositorio, a escolha implementada e RabbitMQ com a biblioteca `pika`.

## 5. Comunicacao

Operacoes pontuais usam request/response:

```json
{
  "idPedido": "uuid",
  "idCliente": "123",
  "idRestaurante": "456",
  "timestamp": 1710000000
}
```

```json
{
  "idPedido": "uuid",
  "idEntregador": "789",
  "timestamp": 1710000001
}
```

```json
{
  "idPedido": "uuid",
  "idCliente": "123",
  "timestamp": 1710000003
}
```

```json
{
  "idPedido": "uuid",
  "idRestaurante": "456",
  "timestamp": 1710000002
}
```

Eventos usam publish-subscribe:

```json
{
  "idPedido": "uuid",
  "idRestaurante": "456",
  "timestamp": 1710000000
}
```

```json
{
  "idEntregador": "789",
  "idPedido": "uuid",
  "latitude": -23.55,
  "longitude": -46.63,
  "timestamp": 1710000002
}
```

```json
{
  "idPedido": "uuid",
  "latitude": -23.55,
  "longitude": -46.63,
  "timestamp": 1710000002
}
```

```json
{
  "idPedido": "uuid",
  "idServidorRastreador": "R1"
}
```

```json
{
  "idPedido": "uuid",
  "idRestaurante": "456",
  "timestamp": 1710000002
}
```

Mensagens internas:

```json
{
  "idServidor": "R1",
  "tipoServidor": "RASTREADOR",
  "timestamp": 1710000004
}
```

`AtualizacaoRoteamento` informa qual servidor rastreador esta responsavel por
quais pedidos.

## 6. Fluxo Principal

1. Cliente envia `CriarPedido` ao servidor.
2. Servidor publica `PedidoDisponivel`.
3. Restaurante assina pedidos disponiveis, filtra seu restaurante e envia
   `PrepararPedido`.
4. Servidor publica `PedidoPreparado`.
5. Entregador assina pedidos disponiveis e envia `AceitarPedido`.
6. Servidor associa pedido ao entregador e ao Servidor Rastreador.
7. Cliente assina o rastreio com `SubscribeRastreio`.
8. Entregador publica `LocalizacaoEntregador`.
9. Rastreador publica/encaminha `EventoLocalizacao`.
10. Cliente envia `ConfirmarEntrega`.
11. Servidor publica `EntregaConfirmada`.

## 7. Nomeacao e Roteamento

Os pedidos usam UUID para garantir unicidade. Cliente, entregador, restaurante,
ADM, Rastreador e SUP possuem identificadores proprios.

O servidor rastreador responsavel e escolhido por consistent hashing com nos
virtuais:

1. cada servidor R gera nos virtuais com `hash(idServidor + "#" + indice)`;
2. cada pedido gera uma posicao com `hash(idPedido)`;
3. o responsavel e o primeiro no virtual no sentido horario;
4. se o fim do anel for alcancado, a busca volta ao inicio.

## 8. Coordenacao

Nao ha exclusao mutua distribuida para localizacoes. Em caso de atualizacoes
concorrentes ou atrasadas, vale a mensagem com maior timestamp.

O sistema usa eleicao de lider entre ADMs pelo Bully Algorithm. Servidores tem
IDs, detectam falha do lider por heartbeat e o maior ID ativo assume.

## 9. Replicacao e Consistencia

O modelo e consistencia eventual. O dado principal replicado e a lista de
rastreios. Cada servidor R possui um SUP associado que mantem uma copia
secundaria dos rastreios atuais.

Quando um R falha, o ADM solicita a lista de backup ao SUP e redistribui os
rastreios para servidores ativos. Se o backup nao chegar, o ADM pode usar sua
propria lista.

Os ADMs usam replicacao baseada em lider. Apenas o ADM lider altera a tabela de
mapeamento pedido -> servidor rastreador. Depois de alterar seu estado local, o
lider propaga o snapshot para os demais ADMs e considera a operacao confirmada
somente quando a maioria do cluster reconhece a replicacao. Em um cluster de
tres ADMs, isso significa o lider local mais pelo menos um ADM adicional.

A distribuicao de copias se adapta a entrada e saida de servidores
rastreadores. Quando um R entra no sistema e envia `keepAlive`, seus nos
virtuais passam a fazer parte do anel; apenas os pedidos afetados pelo novo anel
sao remapeados. Quando um R falha, seus nos virtuais sao removidos e apenas os
pedidos sob responsabilidade dele sao redistribuidos.

O projeto prioriza disponibilidade e tolerancia a particoes, aceitando
inconsistencias temporarias durante falhas ou recuperacao. Mensagens antigas de
localizacao sao descartadas por timestamp, e falhas parciais sao tratadas por
timeouts, redirecionamento para o lider atual, redistribuicao de rastreios e
eleicao de novo lider ADM.

Falhas cobertas pela prova de conceito:

- falha por crash de ADM lider;
- falha por crash/omissao de Rastreador;
- atraso de mensagens de localizacao;
- resposta de comando enviada a ADM nao lider;
- indisponibilidade temporaria de peer ADM durante replicacao.

## 10. Tarefas dos Servidores

ADM:

- acompanhar disponibilidade dos servidores R;
- solicitar informacoes de rastreios com apenas um R associado;
- enviar informacoes obtidas para outro servidor R;
- registrar preparo do pedido informado pelo restaurante;
- manter pedidos sem entregador;
- manter relacao entre rastreios e servidores rastreadores;
- participar da eleicao de lider.

R:

- manter entregadores conectados e localizacao mais recente;
- enviar/publicar localizacao do entregador associado ao cliente;
- notificar cliente e restaurante sobre desconexao do entregador.

SUP:

- enviar sua versao da lista de rastreio quando notar falha de um R;
- manter lista temporaria possivelmente desatualizada ate o ADM remanejar os
  rastreios.
