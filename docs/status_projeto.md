# Checklist do Projeto DSID

Fonte principal da especificacao:

[`Trabalho DSID Especificacoes.pdf`](Trabalho%20DSID%20Especificacoes.pdf)

Ultima validacao:

```text
pytest -q
# confira a contagem atual apos o merge (com RabbitMQ: suite completa)

# sem RabbitMQ (docker compose stop):
# testes @pytest.mark.integration sao pulados

pytest -q -m integration
4 passed

# sem RabbitMQ:
# 4 skipped

# validacao manual sem RabbitMQ:
# API ADM isolada: keepAlive -> criar -> aceitar -> confirmar OK
# SUP HTTP: /estado e /backup OK

# validacao manual com processos reais:
# scripts/validate_cluster_manual.ps1
# R3 entra por keepAlive real -> adm-3 falha -> adm-2 lider -> confirmar OK
```

## Documentacao

- [x] Usar `Trabalho DSID Especificacoes.pdf` como fonte principal.
- [x] Atualizar `docs/spec.md` para seguir o PDF.
- [x] Atualizar `docs/especificacao.md` para seguir o PDF.
- [x] Documentar CAP/AP, tipos de falha e recuperacao conforme o PDF.
- [x] Documentar maioria na replicacao ADM conforme o PDF.
- [x] Documentar rebalanceamento por entrada/saida de R conforme o PDF.
- [x] Atualizar `README.md` com a arquitetura atual.
- [x] Criar este checklist de acompanhamento.
- [x] Adicionar no README um roteiro completo de apresentacao.
- [x] Adicionar no README comandos para rodar todos os componentes.
- [x] Adicionar no README demo com multiplos clientes e entregadores.
- [x] Documentar fila de pedidos sem entregador e retentativa ao liberar entregador.
- [x] Adicionar no README como simular falha de servidor.
- [x] Adicionar painel web simples em `/demo` para apresentacao.
- [x] Adicionar visualizacao do fluxo distribuido no painel `/demo`.

## Contratos de Dados

- [x] Implementar `CriarPedido`.
- [x] Implementar `AceitarPedido`.
- [x] Implementar `ConfirmarEntrega`.
- [x] Implementar `PrepararPedido`.
- [x] Implementar `PedidoDisponivel`.
- [x] Implementar `PedidoPreparado`.
- [x] Implementar `LocalizacaoEntregador`.
- [x] Implementar `EventoLocalizacao`.
- [x] Implementar `SubscribeRastreio`.
- [x] Garantir `SubscribeRastreio` com `idPedido` e `idServidorRastreador`.
- [x] Implementar `EntregaConfirmada`.
- [x] Implementar `KeepAlive`.
- [x] Garantir `KeepAlive` com `idServidor`, `tipoServidor` e `timestamp`.
- [x] Implementar `AtualizacaoRoteamento`.
- [x] Implementar `ReplicacaoRoteamento` (snapshot ADM lider → peers).
- [x] Implementar entidades `Cliente`, `Entregador`, `Restaurante` e `Pedido`.
- [x] Implementar entidades `ServidorAdministrador`, `ServidorRastreador` e `ServidorSuporte`.

## Roteamento e Consistencia

- [x] Implementar consistent hashing com nos virtuais.
- [x] Usar `hash(idServidor + "#" + indice)` para nos virtuais.
- [x] Usar `hash(idPedido)` para posicionar pedido no anel.
- [x] Escolher o primeiro no virtual no sentido horario.
- [x] Cachear o anel de consistent hashing para evitar reconstrucoes repetidas.
- [x] Manter helper antigo `calcular_servidor_responsavel` para compatibilidade dos testes.
- [x] Aplicar roteamento por consistent hashing no ADM.
- [x] Usar timestamp para aceitar apenas a localizacao mais recente.
- [x] Ignorar localizacao antiga quando timestamp for menor.
- [x] Rejeitar localizacao de pedido nao registrado no Rastreador.
- [x] Testar entrada de novo servidor R configurado por processo real.
- [x] Rebalancear pedidos afetados quando novo servidor R entra no anel.
- [x] Testar saida de servidor R em processo real por failover.

## Broker e Comunicacao Assincrona

- [x] Criar camada de conexao RabbitMQ em `src/broker/connection.py`.
- [x] Criar publicador em `src/broker/publisher.py`.
- [x] Criar assinante em `src/broker/subscriber.py`.
- [x] Publicar mensagens em exchange topic.
- [x] Serializar mensagens Pydantic para JSON.
- [x] Garantir serializacao JSON-native para Pydantic v1 e v2.
- [x] Recriar canal RabbitMQ quando o canal anterior estiver fechado.
- [x] Reutilizar conexao RabbitMQ aberta ao recriar canal fechado.
- [x] Tratar erro de payload/callback no subscriber com `basic_nack`.
- [x] Rejeitar payload JSON que nao seja objeto no subscriber.
- [x] Implementar `stop_consuming` no subscriber para encerrar assinaturas.
- [x] Criar `docker-compose.yml` para RabbitMQ.
- [x] Validar publicacao real usando RabbitMQ rodando.
- [x] Validar assinatura real usando RabbitMQ rodando.
- [x] Documentar painel RabbitMQ e credenciais.

## API Sincrona

- [x] Criar `src/api.py` com FastAPI.
- [x] Criar endpoint para `CriarPedido`.
- [x] Criar endpoint para `AceitarPedido`.
- [x] Criar endpoint para `ConfirmarEntrega`.
- [x] Criar endpoint para `KeepAlive`.
- [x] Criar endpoint para eleicao.
- [x] Criar endpoint para consultar estado.
- [x] Criar endpoint `/demo/cluster` para o painel.
- [x] Testar API com requests HTTP reais usando ASGI transport.
- [x] Testar API manualmente via HTTP local sem RabbitMQ.
- [x] Retornar mensagens de erro limpas em excecoes da API.
- [x] Retornar erro limpo quando nao ha rastreador ativo para aceitar pedido.
- [x] Permitir lista de rastreadores via `ADM_TRACKERS`.
- [x] Permitir SUPs extras via `ADM_SUPPORT_URLS`.
- [x] Adicionar exemplos de payload no README.

## Servidor ADM

- [x] Manter lista de pedidos.
- [x] Manter lista de pedidos sem entregador.
- [x] Publicar `PedidoDisponivel`.
- [x] Processar `PrepararPedido` enviado pelo restaurante.
- [x] Publicar `PedidoPreparado`.
- [x] Processar `AceitarPedido`.
- [x] Rejeitar segundo aceite do mesmo pedido (409 `pedido_ja_aceito`).
- [x] Escolher Servidor Rastreador por consistent hashing.
- [x] Publicar `AtualizacaoRoteamento`.
- [x] Processar `ConfirmarEntrega`.
- [x] Publicar `EntregaConfirmada`.
- [x] Processar `KeepAlive`.
- [x] Detectar heartbeat expirado.
- [x] Expirar rastreador conhecido que nunca renovou heartbeat.
- [x] Registrar heartbeat pelo tempo local de recebimento.
- [x] Retornar heartbeats expirados em ordem estavel.
- [x] Redistribuir pedido apos falha de R.
- [x] Consultar backup do SUP.
- [x] Continuar failover de R usando mapa local quando SUP HTTP estiver offline.
- [x] Ignorar chaves invalidas em backup do SUP durante failover.
- [x] Implementar Bully Algorithm simplificado.
- [x] Interpretar IDs como `adm-10` corretamente na escolha do maior ID.
- [x] Simular multiplos ADMs em processos separados.
- [x] Implementar troca real de mensagens de eleicao entre ADMs.
- [x] Replicar mapa pedido -> servidor rastreador entre ADMs.
- [x] Replicar pedidos ativos entre ADMs (criar/aceitar/confirmar + sync na eleicao).
- [x] Exigir confirmacao de maioria na replicacao lider -> ADMs.
- [x] Sincronizar estado ADM dos peers ao assumir lideranca.
- [x] Tolerar peer ADM offline no transporte HTTP (keepalive/eleicao/replicacao).

## Servidor Rastreador R

- [x] Registrar entregador associado a pedido.
- [x] Guardar localizacao mais recente.
- [x] Publicar `EventoLocalizacao`.
- [x] Ignorar localizacao antiga por timestamp.
- [x] Sincronizar rastreios com SUP.
- [x] Notificar desconexao de entregador.
- [x] Rodar R como processo proprio.
- [x] Consumir `LocalizacaoEntregador` real via RabbitMQ.
- [x] Encaminhar eventos reais para cliente via RabbitMQ.
- [x] Enviar `KeepAlive` periodico ao ADM.

## Servidor SUP

- [x] Manter backup dos rastreios de um R associado.
- [x] Retornar lista de backup ao ADM.
- [x] Guardar horario do ultimo sync.
- [x] Rodar SUP como processo proprio.
- [x] Testar SUP manualmente via HTTP local.
- [x] Receber sincronizacao real do R via mensagem ou endpoint.
- [x] Avisar/atender ADM em cenario real de falha.

## Clientes Mock

- [x] Criar `mock_customer.py`.
- [x] Criar pedido pelo mock customer.
- [x] Confirmar entrega pelo mock customer.
- [x] Criar `mock_restaurant.py`.
- [x] Fazer mock restaurant assinar `PedidoDisponivel` real via RabbitMQ.
- [x] Fazer mock restaurant preparar pedido via ADM lider.
- [x] Criar `mock_driver.py`.
- [x] Gerar coordenadas falsas.
- [x] Enviar localizacoes periodicas quando conectado a um Tracker injetado.
- [x] Fazer mock customer assinar rastreio real via RabbitMQ.
- [x] Fazer mock customer assinar `EntregaConfirmada` e encerrar rastreio ao confirmar.
- [x] Fazer mock driver publicar `LocalizacaoEntregador` real via RabbitMQ.
- [x] Entregador ignorar novos pedidos enquanto ocupado (fila permanece no ADM).
- [x] Entregador assumir pedido pendente da fila ao ficar livre.
- [x] Entregador redescobrir ADM lider ao aceitar pedido apos falha de ADM.
- [x] Suportar multiplos clientes e entregadores via `-IdCliente` / `-IdEntregador`.
- [x] Criar modo de demo com comandos simples.

## Testes

- [x] Testar modelos principais.
- [x] Testar campos do `SubscribeRastreio`.
- [x] Testar campos do `KeepAlive`.
- [x] Testar contratos de restaurante (`PrepararPedido` e `PedidoPreparado`).
- [x] Testar roteamento deterministico legado.
- [x] Testar consistent hashing.
- [x] Testar fluxo criar -> aceitar -> rastrear -> confirmar.
- [x] Testar descarte de localizacao antiga.
- [x] Testar rejeicao de localizacao para pedido desconhecido.
- [x] Testar redistribuicao apos falha de rastreador.
- [x] Testar escolha de lider com sufixo numerico em IDs como `adm-10`.
- [x] Testar serializacao JSON-native.
- [x] Testar endpoints FastAPI com `httpx`.
- [x] Testar disponibilidade do painel `/demo`.
- [x] Testar resumo `/demo/cluster`.
- [x] Testar fluxo de restaurante preparando pedido.
- [x] Testar cliente restaurante filtrando pedidos do proprio restaurante.
- [x] Testar expirar rastreador sem heartbeat renovado.
- [x] Testar backup de SUP com chave invalida.
- [x] Testar failover de R quando SUP HTTP estiver indisponivel.
- [x] Testar cache do anel de consistent hashing.
- [x] Testar ack/nack do subscriber.
- [x] Testar rejeicao de payload JSON nao-objeto no subscriber.
- [x] Testar reuso de conexao RabbitMQ ao recriar canal.
- [x] Testar heartbeat usando tempo local.
- [x] Testar ordem estavel de heartbeats expirados.
- [x] Testar broker real com RabbitMQ.
- [x] Testar replicacao de roteamento e pedidos entre ADMs.
- [x] Testar falha quando replicacao ADM nao atinge maioria.
- [x] Testar rebalanceamento de pedido afetado pela entrada de novo R.
- [x] Testar rejeicao de aceite duplicado de pedido.
- [x] Testar fila de pedidos pendentes ao liberar entregador.
- [x] Testar confirmar entrega no novo lider apos falha do lider ADM.
- [x] Testar cenario de falha com processos reais.
- [x] Automatizar validacao multiprocesso real com `pytest -m integration`.

## Demonstracao Fim a Fim

- [x] Criar script para subir ADM.
- [x] Criar script para subir R1.
- [x] Criar script para subir R2.
- [x] Criar script para subir SUP de R1.
- [x] Criar script para cliente.
- [x] Criar script para restaurante.
- [x] Criar script para entregador.
- [x] Cliente cria pedido.
- [x] Restaurante recebe pedido e marca preparo.
- [x] Entregador recebe pedido disponivel.
- [x] Entregador aceita pedido.
- [x] ADM atribui pedido a um R.
- [x] Entregador envia localizacoes.
- [x] Entregador simula trajeto com origem e destino fixos.
- [x] Cliente recebe localizacoes.
- [x] Cliente confirma entrega.
- [x] Cliente encerra automaticamente ao receber `EntregaConfirmada` (confirmacao de outro terminal).
- [x] Demo com multiplos clientes e entregadores (fila no ADM).

## Demonstracao de Falha

- [x] Subir pelo menos dois servidores R.
- [x] Associar pedido ao R1.
- [x] Sincronizar backup no SUP.
- [x] Simular queda do R1.
- [x] ADM detectar ausencia de `KeepAlive`.
- [x] ADM solicitar backup ao SUP.
- [x] ADM redistribuir pedido para R2.
- [x] Mostrar rastreio continuando pelo novo servidor.

## Demonstracao ADM (replicacao + eleicao)

- [x] Criar script `demo_roteamento.ps1` (roteamento e pedidos nos 3 ADMs).
- [x] `demo_estado.ps1` exibe campo `roteamento`.
- [x] Criar script `validate_cluster_manual.ps1`.
- [x] Criar painel visual para observar ADMs, rastreadores, pedidos e roteamento.
- [x] Mostrar etapas do pedido no painel: cliente, restaurante, entregador e rastreador.
- [x] Demo manual: replicacao apos aceitar pedido (3 ADMs com mesmo mapa).
- [x] Demo manual: eleicao apos matar lider com estado preservado no novo lider.
- [x] Demo manual: confirmar entrega no novo lider em processos reais.
- [x] Demo multiprocesso coberta por teste de integracao automatizado.

## Logs de Apresentacao

- [x] Logar pedido criado (`[adm]` + `[cliente]`).
- [x] Logar pedido recebido/preparado pelo restaurante.
- [x] Logar pedido aceito (`[adm]` + `[entregador]`).
- [x] Logar pedido em espera no ADM quando entregador ocupado (`[entregador]`).
- [x] Logar pedido pendente assumido da fila (`[entregador]`).
- [x] Logar entrega confirmada no cliente e encerramento do rastreio (`[cliente]`).
- [x] Logar servidor rastreador escolhido (`[adm]` na aceitacao + `[rastreador]` no roteamento).
- [x] Logar localizacao recebida (`[rastreador]` + `[cliente]`).
- [x] Logar chegada ao destino simulado (`[entregador]`).
- [x] Logar localizacao ignorada por timestamp antigo (`[rastreador]`).
- [x] Logar heartbeat recebido (primeira ativacao do rastreador no lider ADM).
- [x] Logar falha detectada (`[adm]` ao processar heartbeat expirado).
- [x] Logar backup recebido do SUP (`[adm]` + `[sup]` no GET `/backup`).
- [x] Logar pedido redistribuido (`[adm]`).
- [x] Logar novo lider eleito (`[adm]` na eleicao Bully).

Desabilitar logs: `PRESENTATION_LOG=0`.

## Proximos Passos Recomendados

- [x] Criar `docker-compose.yml` do RabbitMQ.
- [x] Criar scripts de execucao dos componentes.
- [x] Implementar demo local com multiplos processos.
- [x] Adicionar logs de apresentacao.
- [x] Atualizar README com roteiro final.
- [ ] Endpoint dedicado `GET /pedidos/sem-entregador` (hoje entregador usa `GET /estado`).
- [ ] Timeout opcional no cliente para avisar "ainda na fila" durante demo longa.

## Observacoes

- [x] Projeto correto como prova de conceito em memoria seguindo o PDF, com
  replicacao entre ADMs e backup nos SUPs durante a execucao, mas sem
  persistencia duravel se todos os processos forem reiniciados simultaneamente.
- [x] Testes atuais passando (confira com `pytest -q`).
- [x] Demo ADM com 3 processos e RabbitMQ real implementadas.
- [x] Demo E2E completa (R1/R2, SUP, cliente, restaurante e entregador via broker) e failover manual validados.
- [x] Replicacao ADM (roteamento + pedidos) validada manualmente com eleicao de lider.
- [x] Fila de pedidos sem entregador conforme spec; entregador retenta ao ficar livre.
- [x] Cliente encerra rastreio ao receber `EntregaConfirmada` publicada pelo ADM.
- [x] GPS do entregador usa trajeto deterministico com destino simulado; a
  finalizacao ainda depende da confirmacao manual do cliente.
- [x] Atualizar este checklist sempre que uma etapa nova for implementada.
