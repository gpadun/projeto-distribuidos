Especificações: Aula 1 - Arquitetura
- Entregáveis: Desenho de Arquitetura: link da arquitetura
Perguntas Norteadoras:
● Dos modelos estudados, algum se encaixa? Em camadas, (micro) serviços, pub sub,
peer-to-peer (estruturado ou não estruturado)?
● Arquitetura de software interna?
● Como o sistema será testado?
● Faz sentido algum tipo de middleware?
1. Dos modelos estudados, algum se encaixa?
Modelo Físico (Cliente-Servidor em Nuvem)
O aplicativo no celular do entregador, o celular do cliente e o aplicativo do
restaurante atuam como clientes do sistema. Esses clientes não se comunicam diretamente
entre si; todas as interações passam por um servidor central, hospedado em uma
infraestrutura de computação em nuvem (como AWS, Google Cloud ou Azure), responsável
por processar as requisições e coordenar o funcionamento do sistema.
Modelo Lógico (Publish-Subscribe ou Event-Based)
Para permitir a atualização em tempo real da localização do entregador no mapa do
cliente, o sistema pode utilizar o modelo Publish-Subscribe. Nesse modelo, o aplicativo do
entregador publica sua localização GPS no sistema, enquanto o aplicativo do cliente assina
as atualizações relacionadas ao pedido. Dessa forma, os componentes permanecem
desacoplados, pois o entregador não precisa conhecer diretamente o cliente, nem
vice-versa.
Para pedidos ainda sem entregador correspondente , é necessário um PubSub, a
partir daí os entregadores que estariam subscritos podem solicitar que sejam responsáveis
por um pedido específico.
2. Arquitetura de Software Interna
A arquitetura interna do sistema pode seguir o modelo de arquitetura em camadas
(multitier), que divide a aplicação em três níveis principais:
Camada de Apresentação (Interface do Usuário)
Responsável pela interação com o usuário. Inclui o aplicativo do cliente, do
entregador e do restaurante. Essa camada exibe informações como o mapa, o status do
pedido e as notificações, sem realizar processamento complexo.
Simulação de entregadores:
Para viabilizar testes no contexto da disciplina, os entregadores não serão usuários
reais, mas sim simulados através de scripts automatizados.
Esses scripts enviarão periodicamente atualizações de localização (latitude,
longitude, timestamp), permitindo reproduzir cenários de múltiplos entregadores ativos
simultaneamente.
Isso possibilita a realização de testes de carga e comportamento do sistema sem
dependência de dispositivos móveis reais.
Aplicação de restaurantes:
Para simplificação da prova de conceito, os restaurantes serão considerados
entidades pré-cadastradas (hardcoded) no sistema.
Dessa forma, reduz-se a complexidade da implementação e permite maior foco nos
aspectos distribuídos do sistema.
Interface de acesso:
A prova de conceito será implementada utilizando aplicações simples (por exemplo,
aplicações de console ou web), eliminando a necessidade de desenvolvimento mobile.
Essa decisão permite focar nos aspectos de comunicação distribuída, tolerância a
falhas e escalabilidade.
Camada de Lógica de Negócios (Processamento)
Executada nos servidores na nuvem, essa camada contém as regras de negócio do
sistema. É responsável por funções como atribuir entregadores aos pedidos, calcular tempo
estimado de entrega e processar pagamentos. Em arquiteturas modernas, essa camada
pode ser implementada utilizando microsserviços, nos quais cada serviço é responsável por
uma funcionalidade específica do sistema.
Camada de Dados
Responsável pelo armazenamento persistente das informações do sistema. Inclui
bancos de dados que guardam registros de usuários, pedidos, restaurantes, histórico de
entregas e informações de pagamento.
3. Faz sentido usar algum tipo de Middleware?
O uso de middleware é altamente recomendado nesse tipo de sistema distribuído,
pois ele facilita a comunicação entre diferentes componentes da aplicação. O middleware
abstrai a complexidade da rede e permite que sistemas diferentes se comuniquem de forma
transparente, mesmo utilizando plataformas ou redes distintas.
Para o rastreamento em tempo real, é adequado utilizar um Message Broker
(corretor de mensagens), que é um tipo de Middleware Orientado a Mensagens (MOM).
Nesse modelo, os aplicativos enviam mensagens para um intermediário responsável por
distribuí-las para os interessados.
Uma analogia útil é pensar no Message Broker como uma central de triagem dos
Correios. O entregador envia a informação de localização ao sistema, e o broker se
encarrega de encaminhá-la aos aplicativos que estão interessados naquela atualização.
4. Como o sistema será testado?
Testes de Resiliência de Rede
Como dispositivos móveis podem perder sinal com frequência, os testes devem
simular situações em que o entregador entra em áreas sem cobertura de rede. O sistema
deve garantir que os dados de localização sejam armazenados temporariamente no
dispositivo e enviados quando a conexão for restabelecida.
Testes de Integração Fim a Fim (End-to-End)
Esse tipo de teste valida o funcionamento completo do sistema. Um usuário realiza
um pedido, o restaurante o aceita e o entregador realiza a entrega, permitindo verificar se
todas as partes do sistema (cliente, restaurante e entregador) estão corretamente
sincronizadas.
Comunicação
Tipo de comunicação
A comunicação do sistema é majoritariamente assíncrona, baseada em troca de
mensagens via um broker (modelo publish-subscribe).
Para eventos em tempo real (como localização), utiliza-se conexão duradoura (ex:
WebSocket ou TCP persistente).
Para operações pontuais (como criação de pedido), utiliza-se comunicação síncrona
via requisições curtas (request/response).
Tipos de mensagens?
Mensagens de comando (requisições diretas): request/response (cliente -> servidor)
Mensagem: CriarPedido
{
"idPedido": "uuid",
"idCliente": "123",
"idRestaurante": "456",
"timestamp": 1710000000
}
Mensagem: AceitarPedido
{
"idPedido": "uuid",
"idEntregador": "789",
"timestamp": 1710000001
}
Mensagem: ConfirmarEntrega
{
"idPedido": "uuid",
"idCliente": "123",
"timestamp": 1710000003
}
Mensagens de evento (modelo Publish-Subscribe)
Mensagem: PedidoDisponivel (PUBLISH)
{
"idPedido": "uuid",
"idRestaurante": "456",
"timestamp": 1710000000
}
Mensagem: LocalizacaoEntregador (PUBLISH)
{
"idEntregador": "789",
"idPedido": "uuid",
"latitude": -23.55,
"longitude": -46.63,
"timestamp": 1710000002
}
Mensagem: EventoLocalizacao (DELIVERED PELO BROKER)
{
"idPedido": "uuid",
"latitude": -23.55,
"longitude": -46.63,
"timestamp": 1710000002
}
Mensagem: SubscribeRastreio
{
"idPedido": "uuid"
}
Mensagens internas (infraestrutura do sistema)
keepAlive (Servidor -> Servidor)
- Verifica disponibilidade entre nós
AtualizacaoRoteamento (Servidor -> Servidor)
- Atualiza qual servidor está responsável por quais pedidos
Diagramas de sequência:
title Fluxo a partir da criação do pedido\n
Cliente->(1)Serv. ADM:Cria pedido
Serv. ADM->(1)PubSubPedidoSemEntregador: Repassa pedido
Entregador->(1)Serv. ADM:Aceita pedido
Serv. ADM->(1)Serv.R: Atribui pedido
linear
Serv.R->(1)Cliente: Informa cliente sobre qual pubsub se subscrever
Serv.R->(1)Entregador: Passa seu ID/IP ao entregador
linear off
space 2
Cliente->(1)PubSubRastreio:Subscribe
Entregador->(1)Serv.R: Envia localização
Serv.R->(1)PubSubRastreio: Publica localização
PubSubRastreio->(1)Cliente: Envia localização
title Fluxo a partir da criação do pedido\n
Cliente->(1)Serv. ADM:Cria pedido
Serv. ADM->(1)PubSubPedidoSemEntregador: Repassa pedido
Entregador->(1)Serv. ADM:Aceita pedido
Serv. ADM->(1)Serv.R: Atribui pedido
linear
Serv.R->(1)Cliente: Informa cliente sobre qual pubsub se subscrever
Serv.R->(1)Entregador: Passa seu ID/IP ao entregador
linear off
space 2
Cliente->(1)PubSubRastreio:Subscribe
Entregador->(1)Serv.R: Envia localização
Serv.R->(1)PubSubRastreio: Publica localização
PubSubRastreio->(1)Cliente: Envia localização
NOVO:
Fluxo a partir da criação do pedido
Cliente -> Servidor: CriarPedido
Servidor -> Broker: PUBLISH PedidoDisponivel
Entregador -> Broker: SUBSCRIBE PedidoDisponivel
Entregador -> Servidor: AceitarPedido
Servidor: associa pedido ao entregador
Cliente -> Broker: SUBSCRIBE (idPedido)
Entregador -> Broker: PUBLISH LocalizacaoEntregador
Broker -> Cliente: EVENTO Localizacao
NOVO:
Cliente confirma recebimento
Cliente -> Servidor: ConfirmarEntrega
Servidor -> Broker: PUBLISH EntregaConfirmada
Broker -> Entregador: EVENTO EntregaConfirmada
Falha no KeepAlive:
title Queda de servidor de Rastreio
Serv.ADM -x(1)Serv.R.1:Falha no \n keepalive
Serv.ADM->(1)Serv.SUP: Solicita lista mais recente\n de pedidos associados.
Serv.SUP->(1)Serv.ADM: Envia lista
Serv.ADM->(1)Serv.R.2/3/.../n:Redistribui pedidos
Serv.R.2/3/.../n->(1)Entregadores:Enviam ID do pedido que \n é responsável e se identifica
Serv.R.2/3/.../n->(1)Clientes: Enviam ID do pedido que \n é responsável e se identifica
Clientes->(1)PubSubRastreio: Se subscrevem
NOVO:
title Queda de componente do sistema
Componente -x: Falha
Outros componentes detectam falha via ausência de heartbeat (keepAlive)
Possíveis detalhes adicionais:
Nomeação
Como Garantir Unicidade?
Para garantir a unicidade global dos identificadores (principalmente de pedidos),
será utilizado um identificador único gerado no momento da criação do pedido.
Esse identificador pode ser implementado como um UUID (Universally Unique
Identifier) ou como uma combinação de:
- ID do cliente
- Timestamp de alta precisão
- Um contador incremental local
Dessa forma, mesmo em um ambiente distribuído com múltiplos servidores, é
possível garantir que não haverá colisão de identificadores.
Qual servidor cuida do pedido? Resolução de nome
(descoberta do servidor responsável)?
Para determinar qual servidor de rastreio é responsável por um determinado pedido,
será utilizado um mecanismo determinístico baseado em hash.
A partir do identificador único do pedido (idPedido), aplica-se uma função de hash:
servidorResponsavel = (hash(idPedido) mod N)
Onde N é o número de servidores de rastreio disponíveis.
Dessa forma:
- Qualquer componente do sistema pode calcular diretamente qual servidor é responsável
- Não é necessário consultar um servidor central (reduzindo acoplamento)
- O sistema escala melhor com o aumento do número de servidores
Quais recursos precisam ser nomeados/identificados?
Cliente e seu conjunto de pedidos
Entregador
Restaurante
Pedido Recém Criado
Pedido com Entregador
Pedido com Servidor Rastreador Atribuído
Servidor Administrador (porque se teremos vários, precisamos ter um método de
identificação porque é necessário realizar eleição de líder ou reeleição)
Servidor Rastreador
Servidor de Suporte
Qual o esquema de nomeação que será utilizado?
Baseado em atributos
● Cliente: ID como identificador, se assumirmos que o Cliente é incapaz de se mover,
seu IP também pode ser um meio de identificação mais conveniente
<ID/IP>
● Entregador: Id puramente, porque seu IP pode se alterar visto que ele vai se mover
<ID>
● Restaurante: Só ID, e podem ser hardcoded (se não forem podem ser por IP porque
restaurantes são fixos)
<ID/IP>
● Pedido Recém Criado
<id_cliente/IP_cliente, id_Restaurante, timestap>
● Pedido com Entregador
<id_cliente/IP_cliente, id_Entregador, id_Restaurante, timestamp>
Timestamp será de quando ele foi criado
● Pedido com Servidor Rastreador Atribuído
<id_cliente/IP_cliente, id_Entregador, id_Restaurante, timestamp,
servidorRastreioResponsável>
Ter a informação do responsável aqui possibilita que um cliente possa perguntar
diretamente a localização para o servidor de rastreio, essa informação porém pode
mudar se um servidor de rastreio cair então o último campo deverá ser mútavel.
● Servidor Rastreador
<ID/IP>
● Servidor de administração
<ID/IP>
● Servidor de Suporte
<ID/IP , ID_Servidor_de_Rastreio>
Já que cada servidor de rastreio tem um de suporte associado
Servidor stateful ou stateless?
● Stateless
● A informação é armazenada em tempo real, sendo desnecessário consultar o
histórico de Pedido de um Entregador ou Cliente
Faz sentido usar threads?
Cliente:
● Thread de networking (recebe localização)
● Cálculo do tempo de entrega
● Renderizar a localização
Entregador, Restaurante, Sup, ADM, Rast:
● Thread de networking
Faz sentido usar técnicas de virtualização?
Não faz sentido usar em nenhum servidor,
Coordenação
● Será necessário algum mecanismo de sincronização? Relógio digital ou lógico?
Sim, nos baseamos em timestamp e no caso do rastreio, apenas a localização mais
recente será renderizada pelo lado do cliente
● Será necessário empregar exclusão mútua (distribuída)? Qual algoritmo?
Não é necessário empregar exclusão mútua distribuída neste sistema. As operações
principais consistem no envio e repasse de atualizações de localização dos entregadores,
que não representam recursos críticos compartilhados que exijam acesso exclusivo. Caso
múltiplas atualizações sejam recebidas simultaneamente, a mais recente simplesmente
substitui a anterior, não causando inconsistência no sistema.
Além disso, a arquitetura baseada em publish-subscribe e mensagens assíncronas reduz a
necessidade de controle rígido de concorrência, pois os componentes do sistema operam
de forma desacoplada.
● Será necessário algum algoritmo de eleição? Qual?
Sim, pois precisamos de ao menos 2 servidores pois se um servidor ADM cair, outro
precisa assumir responsabilidades de coordenação.
Possíveis algoritmos: Bully Algorithm, lottery algorithm
Funcionamento:
● Servidores possuem IDs.
● Se um servidor percebe que o líder caiu, inicia eleição.
● O servidor com maior ID vira líder.
Vantagens:
● Simples
● Rápido
● Adequado para clusters pequenos.
● Se usar pub/sub, como será implementado?
O modelo Publish-Subscribe pode ser implementado usando um Message Broker.
Exemplos:
● Kafka
● RabbitMQ
● Google Pub/Sub
● AWS SNS/SQS
Publicador:
● Entregador publica localização:
- id entregador
- latitude
- longitude
- timestamp
Broker: O message broker recebe essa mensagem e envia para os interessados.
Assinantes:
● Cliente (acompanhar entrega)
● Restaurante
● Servidor de rastreio
Fluxo: Entregador -> Broker -> Cliente/Restaurante/Rastreio
Perguntas Norteadoras (Replicação e Consistência)
Haverá replicação no projeto?
Sim. A arquitetura do sistema foi desenhada com foco em tolerância a falhas e prevê a
replicação de componentes e dados.
Se não houvesse, quais seriam as consequências?
Embora o projeto tenha replicação, se não a tivesse, o sistema teria pontos únicos de falha.
Por exemplo, a queda de um servidor responsável por acompanhar uma entrega causaria a
interrupção do rastreio em tempo real, impactando a experiência do cliente e a
sincronização do entregador até que o componente fosse restaurado manualmente.
Se sim: Quais dados e/ou entidades serão replicados?
Listas de Rastreio (Dados): As informações de rastreio em tempo real dos entregadores são
o principal dado replicado. Cada rastreio é mantido por no mínimo dois servidores
simultaneamente.
Servidores Rastreadores e de Suporte (Entidades): Para cada Servidor Rastreador (R),
existe um Servidor de Suporte (SUP) que mantém uma lista secundária (cópia) dos
rastreios atuais.
Servidores Administradores (Entidades): O sistema exige pelo menos dois Servidores
Administradores (ADM) operando para manter a redundância do controle e da coordenação
geral, eles precisam manter uma lista contendo a relação entre rastreios e Servidores
Rastreadores ® consistente entre si.
Qual modelo de consistência adotado?
O projeto adota um modelo de Consistência Eventual focado na atualização mais recente,
guiado por timestamps (relógio lógico/físico).
Como as localizações chegam a todo momento, o sistema não aplica bloqueios ou exclusão
mútua distribuída.
Se o sistema receber múltiplas atualizações concorrentes, a mensagem com o timestamp
mais recente simplesmente substitui a anterior.
Há uma tolerância explícita a dados temporariamente inconsistentes (por exemplo, um
servidor de suporte pode enviar uma lista de rastreio temporária e possivelmente
desatualizada enquanto o sistema se reorganiza após uma falha).
No caso de queda do servidor administrador principal, infelizmente clientes que
iniciaram um pedido recentemente terão que fazer outra solicitação quando um servidor
admin líder finalmente for eleito após o problema ser identificado
Como distribuir as cópias? Estática ou dinâmica?
A distribuição das cópias e das responsabilidades é dinâmica.
A distribuição de carga é baseada em uma função de hash (hash(idPedido) mod N) que
mapeia dinamicamente qual servidor é responsável por qual pedido com base na
quantidade de servidores ativos no momento.
Quando um Servidor Rastreador (R) cai, os Servidores Administradores (ADM) notam a
falha, recebem a lista de backup do Servidor de Suporte (SUP) e redistribuem
dinamicamente esses rastreios para outros servidores que estejam operacionais, se o
backup não chegar, o ADM líder usará a sua própria lista (provavelmente com alguns
rastreios extras que finalizaram recentemente)
Isso exige um rebalanceamento dinâmico sempre que nós entram ou saem (falham) no
sistema.
Qual protocolo de consistência? Implementar ou usar uma biblioteca?
O projeto usará uma abordagem híbrida, combinando bibliotecas prontas para a mensageria
e implementação própria para a coordenação dos nós.
Uso de Biblioteca (Message Broker): Toda a infraestrutura de consistência de mensagens e
roteamento dos eventos (Publish-Subscribe) será delegada a ferramentas de mercado
consolidadas, como Kafka, RabbitMQ, Google Pub/Sub ou AWS SQS/SNS. O Broker
garantirá a entrega das mensagens sem que precise codificar essa complexidade.
Implementação Própria (Eleição e Resolução): Para decidir qual Servidor Administrador
(ADM) é o líder em caso de falhas, será implementado um algoritmo de eleição, como o
Bully Algorithm. A consistência dos dados de GPS será resolvida no próprio código
descartando atualizações antigas através da comparação de timestamps.
No caso de queda do servidor administrador líder, é necessário que os servidores
administradores restantes contenham réplicas das relações entre pedidos e servidores de
rastreamento.
Para possibilitar a consistência das listas com essas relações, será usado o modelo
baseado em primário, toda vez que o servidor administrador líder tomar uma decisão, ele
vai propagar essa decisão, e aguardar a resposta de mais de metade dos servidores
administradores (que irão aplicar essa decisão sobre sua própria lista) para então executar
essa decisão. No caso de falha do servidor líder, infelizmente vai ocorrer inconsistência
entre a lista real e a lista dos servidores, mas essa abordagem tenta minimizar esse
problema.
Tolerância a falhas
- Para seu projeto, é importante disponibilidade ou confiabilidade
Disponibilidade, algumas falhas podem ser toleradas, mas o sistema deve
estar no ar
- Quais tipos de falha deseja-se tolerar? (crash, omissão, temporal, resposta,
bizantina)
- Falha de crash: Não tem muito a se fazer
Falha de omissão(servidor não responde ou envia resposta quando deveria, ou
recebe mensagem e não trata ela)
Falha temporal: No caso em que uma mensagem de localização se atrasa, deve-se
usar a mais recente
● No caso onde um cliente faz 2 pedidos em pouco tempo, revise
- Falha de resposta: Só tentar de novo em todos os casos
- Falha bizantina: Pode ocorrer no processo de votação de líder, que se for
determinístico não tem problemas, mas em caso de votação por loteria, é necessário
que ⅔ dos nós concordem em quem é o líder
- Quantos processos falhantes serão suportados?
Todos exceto crash total
- Qual estratégia para detectar falhas: verificar timeout por timestamp ou
disponibilidade de servidores
- Qual protocolo utilizar: ver protocolos de tolerancia a falha
- Quais as consequências do teorema CAP para o projeto?
Temos foco em tolerância a falhas, pois possívelmente ter inconsistência sobre
dados (lista de pedidos que um rastreador possuí) é
- Como recuperar da falha?
- Falha de crash: Não tem muito a se fazer
Falha de omissão: servidor não responde ou envia resposta quando deveria, ou
recebe mensagem e não trata ela. Nesse caso, ele refaz o pedido
Falha temporal: No caso em que uma mensagem de localização se atrasa, deve-se
usar a mais recente
● No caso onde um cliente faz 2 pedidos em pouco tempo, revise
● servidor envia a lista de pedidos no momento errado: servidor ADM recebe a
lista e verifica se o servidor de rastreio líder ainda está funcional. Se sim,
ignora lista recebida, se não, utiliza a lista mais recente, e daí, redistribui os
pedidos.
- Falha de resposta: Só tentar de novo em todos os casos
- Falha bizantina: Pode ocorrer no processo de votação de líder, que se for
determinístico não tem problemas, mas em caso de votação por loteria, é necessário
que ⅔ dos nós concordem em quem é o líder
Tolerância a falhas:
No caso de um servidor cair, como é possível minimizar o impacto disso para o
cliente/entregador/restaurante?
3 tipos de servidores:
● Administrador(ADM): Contém uma lista de todos os rastreios ocorrendo e a quais
servidores rastreadores cada rastreio está relacionado
● Rastreador(R): É responsável por uma parte de todos os rastreios
● Suporte(SUP): Mantém uma lista secundária dos rastreios atuais de um servidor R
para repassar aos servidores ADM caso seu R caia.
Cada rastreio será mantido por (no mínimo) 2 servidores R, de forma que se um deles tiver
uma falha crítica os servidores ADM decidirão a qual servidor R um rastreio deve ser
adicionado. São necessários pelo menos 2 servidores ADM.
NOVO:
A tolerância a falhas do sistema é baseada no desacoplamento entre os
componentes, proporcionado pelo uso do modelo publish-subscribe com um message
broker. Nesse modelo, produtores (entregadores) e consumidores (clientes e restaurantes)
não se comunicam diretamente, o que reduz o impacto de falhas em componentes
individuais.
Em caso de falha:
- Se um entregador (produtor) falhar, as atualizações de localização deixam de ser
publicadas temporariamente, sem impactar outros pedidos ou usuários.
- Se um cliente (consumidor) falhar, ele pode se reconectar ao sistema e reassinar o tópico
correspondente ao seu pedido.
- Se um nó intermediário falhar, outros componentes continuam operando normalmente,
pois não há dependência de um único coordenador central.
Além disso, o broker atua como intermediário na comunicação, garantindo que os
eventos sejam distribuídos aos interessados, mesmo com a entrada e saída dinâmica de
componentes no sistema. Esse modelo permite que o sistema seja resiliente a falhas
parciais, mantendo seu funcionamento sem necessidade de reconfiguração manual dos
clientes.
Tarefas dos servidores:
● ADM:
1. Acompanhar a avaliabilidade dos servidores R
2. Solicitar informações de rastreios com apenas um R associado
3. Enviar informações obtidas para segundo (ou mais) servidor R.
4. Manter uma lista com os pedidos que ainda não foram atribuídos para um
entregador
● R:
1. Manter lista de entregadores conectados e sua localização mais recente
2. Enviar localização mais recente do entregador associado para o cliente
quando solicitado
3. Notificar cliente e restaurante sobre desconexão do entregador
● SUP:
1. Mandar sua versão da lista de rastreio quando notar falha de um servidor R
2. Caso seu servidor R retorne rapidamente pode enviar uma lista temporária
(possivelmente desatualizada) até que os servidores ADM notem e
remanejem os rastreios para ele.