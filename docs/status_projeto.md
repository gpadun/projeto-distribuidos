# Checklist do Projeto DSID

Fonte principal da especificacao:

[`Trabalho DSID Especificacoes.pdf`](Trabalho%20DSID%20Especificacoes.pdf)

Ultima validacao:

```text
pytest -q
75 passed

# sem RabbitMQ (docker compose stop):
# 72 passed, 3 skipped

pytest -q -m integration
3 passed

# sem RabbitMQ:
# 3 skipped
```

## Documentacao

- [x] Usar `Trabalho DSID Especificacoes.pdf` como fonte principal.
- [x] Atualizar `docs/spec.md` para seguir o PDF.
- [x] Atualizar `docs/especificacao.md` para seguir o PDF.
- [x] Atualizar `README.md` com a arquitetura atual.
- [x] Criar este checklist de acompanhamento.
- [x] Adicionar no README um roteiro completo de apresentacao.
- [ ] Adicionar no README comandos para rodar todos os componentes.
- [x] Adicionar no README como simular falha de servidor.

## Contratos de Dados

- [x] Implementar `CriarPedido`.
- [x] Implementar `AceitarPedido`.
- [x] Implementar `ConfirmarEntrega`.
- [x] Implementar `PedidoDisponivel`.
- [x] Implementar `LocalizacaoEntregador`.
- [x] Implementar `EventoLocalizacao`.
- [x] Implementar `SubscribeRastreio`.
- [x] Garantir `SubscribeRastreio` com `idPedido` e `idServidorRastreador`.
- [x] Implementar `EntregaConfirmada`.
- [x] Implementar `KeepAlive`.
- [x] Garantir `KeepAlive` com `idServidor`, `tipoServidor` e `timestamp`.
- [x] Implementar `AtualizacaoRoteamento`.
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
- [ ] Testar rebalanceamento com entrada de novo servidor R.
- [ ] Testar rebalanceamento com saida de servidor R em processo real.

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
- [x] Testar API com requests HTTP reais usando ASGI transport.
- [x] Retornar mensagens de erro limpas em excecoes da API.
- [ ] Adicionar exemplos de payload no README.

## Servidor ADM

- [x] Manter lista de pedidos.
- [x] Manter lista de pedidos sem entregador.
- [x] Publicar `PedidoDisponivel`.
- [x] Processar `AceitarPedido`.
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
- [x] Ignorar chaves invalidas em backup do SUP durante failover.
- [x] Implementar Bully Algorithm simplificado.
- [x] Interpretar IDs como `adm-10` corretamente na escolha do maior ID.
- [x] Simular multiplos ADMs em processos separados.
- [x] Implementar troca real de mensagens de eleicao entre ADMs.
- [ ] Replicar mapa pedido -> servidor rastreador entre ADMs.

## Servidor Rastreador R

- [x] Registrar entregador associado a pedido.
- [x] Guardar localizacao mais recente.
- [x] Publicar `EventoLocalizacao`.
- [x] Ignorar localizacao antiga por timestamp.
- [x] Sincronizar rastreios com SUP.
- [x] Notificar desconexao de entregador.
- [ ] Rodar R como processo proprio.
- [ ] Consumir `LocalizacaoEntregador` real via RabbitMQ.
- [ ] Encaminhar eventos reais para cliente via RabbitMQ.
- [ ] Enviar `KeepAlive` periodico ao ADM.

## Servidor SUP

- [x] Manter backup dos rastreios de um R associado.
- [x] Retornar lista de backup ao ADM.
- [x] Guardar horario do ultimo sync.
- [ ] Rodar SUP como processo proprio.
- [ ] Receber sincronizacao real do R via mensagem ou endpoint.
- [ ] Avisar/atender ADM em cenario real de falha.

## Clientes Mock

- [x] Criar `mock_customer.py`.
- [x] Criar pedido pelo mock customer.
- [x] Confirmar entrega pelo mock customer.
- [x] Criar `mock_driver.py`.
- [x] Gerar coordenadas falsas.
- [x] Enviar localizacoes periodicas quando conectado a um Tracker injetado.
- [ ] Fazer mock customer assinar rastreio real via RabbitMQ.
- [ ] Fazer mock driver publicar `LocalizacaoEntregador` real via RabbitMQ.
- [ ] Criar modo de demo com comandos simples.

## Testes

- [x] Testar modelos principais.
- [x] Testar campos do `SubscribeRastreio`.
- [x] Testar campos do `KeepAlive`.
- [x] Testar roteamento deterministico legado.
- [x] Testar consistent hashing.
- [x] Testar fluxo criar -> aceitar -> rastrear -> confirmar.
- [x] Testar descarte de localizacao antiga.
- [x] Testar rejeicao de localizacao para pedido desconhecido.
- [x] Testar redistribuicao apos falha de rastreador.
- [x] Testar escolha de lider com sufixo numerico em IDs como `adm-10`.
- [x] Testar serializacao JSON-native.
- [x] Testar endpoints FastAPI com `httpx`.
- [x] Testar expirar rastreador sem heartbeat renovado.
- [x] Testar backup de SUP com chave invalida.
- [x] Testar cache do anel de consistent hashing.
- [x] Testar ack/nack do subscriber.
- [x] Testar rejeicao de payload JSON nao-objeto no subscriber.
- [x] Testar reuso de conexao RabbitMQ ao recriar canal.
- [x] Testar heartbeat usando tempo local.
- [x] Testar ordem estavel de heartbeats expirados.
- [x] Testar broker real com RabbitMQ.
- [ ] Testar cenario de falha com processos reais.

## Demonstracao Fim a Fim

- [x] Criar script para subir ADM.
- [ ] Criar script para subir R1.
- [ ] Criar script para subir R2.
- [ ] Criar script para subir SUP de R1.
- [ ] Criar script para cliente.
- [ ] Criar script para entregador.
- [ ] Cliente cria pedido.
- [ ] Entregador recebe pedido disponivel.
- [ ] Entregador aceita pedido.
- [ ] ADM atribui pedido a um R.
- [ ] Entregador envia localizacoes.
- [ ] Cliente recebe localizacoes.
- [ ] Cliente confirma entrega.

## Demonstracao de Falha

- [ ] Subir pelo menos dois servidores R.
- [ ] Associar pedido ao R1.
- [ ] Sincronizar backup no SUP.
- [ ] Simular queda do R1.
- [ ] ADM detectar ausencia de `KeepAlive`.
- [ ] ADM solicitar backup ao SUP.
- [ ] ADM redistribuir pedido para R2.
- [ ] Mostrar rastreio continuando pelo novo servidor.

## Logs de Apresentacao

- [ ] Logar pedido criado.
- [ ] Logar pedido aceito.
- [ ] Logar servidor rastreador escolhido.
- [ ] Logar localizacao recebida.
- [ ] Logar localizacao ignorada por timestamp antigo.
- [ ] Logar heartbeat recebido.
- [ ] Logar falha detectada.
- [ ] Logar backup recebido do SUP.
- [ ] Logar pedido redistribuido.
- [ ] Logar novo lider eleito.

## Proximos Passos Recomendados

- [x] Criar `docker-compose.yml` do RabbitMQ.
- [x] Criar scripts de execucao dos componentes.
- [x] Implementar demo local com multiplos processos.
- [ ] Adicionar logs de apresentacao.
- [x] Atualizar README com roteiro final.

## Observacoes

- [x] Projeto correto como prova de conceito em memoria seguindo o PDF.
- [x] Testes atuais passando.
- [x] Demo ADM com 3 processos e RabbitMQ real implementadas; falta E2E completo (R, SUP, cliente e entregador via broker).
- [x] Atualizar este checklist sempre que uma etapa nova for implementada.