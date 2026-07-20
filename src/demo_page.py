"""HTML demo dashboard served by the FastAPI ADM process."""

DEMO_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Demo DSID</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #667085;
      --line: #d9e0ea;
      --ok: #157f3b;
      --warn: #a15c00;
      --bad: #b42318;
      --blue: #155eef;
      --soft-blue: #e8f0ff;
      --soft-green: #e9f8ef;
      --soft-red: #ffeceb;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      font-size: 14px;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 16px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }

    h1 {
      margin: 0;
      font-size: 20px;
      line-height: 1.2;
    }

    main {
      display: grid;
      grid-template-columns: minmax(300px, 1.1fr) minmax(360px, 1.4fr);
      gap: 16px;
      padding: 16px 24px 24px;
    }

    section {
      min-width: 0;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
    }

    h2 {
      margin: 0 0 12px;
      font-size: 15px;
    }

    button {
      min-height: 36px;
      border: 1px solid #b8c4d6;
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      cursor: pointer;
      font-weight: 600;
    }

    button.primary {
      border-color: var(--blue);
      background: var(--blue);
      color: #fff;
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.55;
    }

    input, select {
      min-height: 36px;
      width: 100%;
      border: 1px solid #b8c4d6;
      border-radius: 6px;
      padding: 0 10px;
      background: #fff;
      color: var(--ink);
    }

    label {
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }

    th, td {
      padding: 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }

    th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }

    .toolbar, .form-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }

    .status-row {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 16px;
    }

    .metric {
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcff;
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }

    .metric strong {
      display: block;
      margin-top: 4px;
      font-size: 18px;
    }

    .grid {
      display: grid;
      gap: 16px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--soft-blue);
      color: var(--blue);
      font-weight: 700;
      font-size: 12px;
    }

    .badge.ok { background: var(--soft-green); color: var(--ok); }
    .badge.bad { background: var(--soft-red); color: var(--bad); }
    .muted { color: var(--muted); }
    .mono { font-family: Consolas, Monaco, monospace; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .wide { grid-column: 1 / -1; }

    .flow {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }

    .node {
      min-height: 74px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcff;
    }

    .node strong {
      display: block;
      margin-bottom: 6px;
      font-size: 14px;
    }

    .node span {
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }

    .node.active {
      border-color: #8bb4ff;
      background: var(--soft-blue);
    }

    .node.ok {
      border-color: #9bd6af;
      background: var(--soft-green);
    }

    .timeline {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
    }

    .roles {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }

    .role {
      min-height: 170px;
      display: grid;
      gap: 10px;
      align-content: start;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcff;
    }

    .role h3 {
      margin: 0;
      font-size: 14px;
    }

    .role p {
      min-height: 34px;
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }

    .role button {
      width: 100%;
    }

    .map {
      position: relative;
      min-height: 190px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 8px;
      background:
        linear-gradient(90deg, rgba(21, 94, 239, 0.08) 1px, transparent 1px),
        linear-gradient(0deg, rgba(21, 94, 239, 0.08) 1px, transparent 1px),
        #fbfcff;
      background-size: 32px 32px;
    }

    .route {
      position: absolute;
      left: 11%;
      right: 11%;
      top: 50%;
      height: 4px;
      border-radius: 999px;
      background: #b8c4d6;
    }

    .route-progress {
      display: block;
      width: 0%;
      height: 100%;
      border-radius: inherit;
      background: var(--blue);
      transition: width 220ms ease;
    }

    .place, .driver-dot {
      position: absolute;
      transform: translate(-50%, -50%);
    }

    .place {
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      border: 2px solid #98a2b3;
      border-radius: 50%;
      background: #fff;
      color: var(--muted);
      font-weight: 800;
      font-size: 12px;
    }

    .place.start { left: 11%; top: 50%; }
    .place.end { left: 89%; top: 50%; border-color: var(--ok); color: var(--ok); }

    .driver-dot {
      left: 11%;
      top: 50%;
      display: grid;
      place-items: center;
      width: 30px;
      height: 30px;
      border-radius: 50%;
      background: var(--blue);
      color: #fff;
      box-shadow: 0 8px 18px rgba(21, 94, 239, 0.25);
      font-size: 16px;
      transition: left 900ms linear;
    }

    .driver-dot.moving {
      box-shadow: 0 0 0 8px rgba(21, 94, 239, 0.12), 0 8px 18px rgba(21, 94, 239, 0.25);
    }

    .driver-dot.arrived {
      background: var(--ok);
    }

    .map-status {
      position: absolute;
      left: 12px;
      right: 12px;
      bottom: 12px;
      display: flex;
      justify-content: space-between;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }

    .route-details {
      position: absolute;
      top: 12px;
      right: 12px;
      display: grid;
      gap: 4px;
      min-width: 170px;
      padding: 8px 10px;
      border: 1px solid rgba(21, 94, 239, 0.18);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.92);
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }

    .route-details strong {
      color: var(--ink);
      font-size: 13px;
    }

    .step {
      min-height: 56px;
      padding: 9px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcff;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-align: center;
    }

    .step.done {
      border-color: #9bd6af;
      background: var(--soft-green);
      color: var(--ok);
    }

    #log {
      min-height: 112px;
      max-height: 220px;
      overflow: auto;
      padding: 10px;
      border-radius: 8px;
      background: #101828;
      color: #e4e7ec;
      font-family: Consolas, Monaco, monospace;
      font-size: 12px;
      white-space: pre-wrap;
    }

    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; padding: 12px; }
      header { align-items: flex-start; flex-direction: column; padding: 14px 12px; }
      .toolbar, .form-grid, .status-row { grid-template-columns: 1fr; }
      .flow, .timeline, .roles { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Painel DSID</h1>
      <div class="muted">ADM, rastreadores, pedidos e roteamento</div>
    </div>
    <div class="actions">
      <button id="refresh">Atualizar</button>
      <a class="badge" href="/docs">Swagger</a>
    </div>
  </header>

  <main>
    <div class="grid">
      <section>
        <h2>Cluster ADM</h2>
        <div class="status-row">
          <div class="metric"><span>Servidor</span><strong id="self-id">-</strong></div>
          <div class="metric"><span>Lider</span><strong id="leader-id">-</strong></div>
          <div class="metric"><span>RabbitMQ</span><strong id="rabbit">-</strong></div>
        </div>
        <table>
          <thead><tr><th>ADM</th><th>Estado</th><th>Lider</th></tr></thead>
          <tbody id="adms"></tbody>
        </table>
      </section>

      <section>
        <h2>Rastreadores</h2>
        <div class="toolbar">
          <button data-tracker="rastreador-1">KeepAlive R1</button>
          <button data-tracker="rastreador-2">KeepAlive R2</button>
          <button data-tracker="rastreador-3">KeepAlive R3</button>
        </div>
        <table>
          <thead><tr><th>Ativos</th><th>Expirados</th></tr></thead>
          <tbody id="trackers"></tbody>
        </table>
      </section>

      <section>
        <h2>Fluxo Distribuido</h2>
        <div class="flow" id="flow"></div>
      </section>
    </div>

    <div class="grid">
      <section>
        <h2>Comandos do Pedido</h2>
        <div class="form-grid">
          <label>Pedido <input id="pedido" class="mono"></label>
          <label>Cliente <input id="cliente" value="cliente-demo"></label>
          <label>Restaurante <input id="restaurante" value="restaurante-1"></label>
          <label>Entregador <input id="entregador" value="entregador-demo"></label>
          <label>Status <input id="command-status" readonly></label>
          <label>Atualizacao <input id="updated-at" readonly></label>
        </div>
        <div class="actions" style="margin-top: 12px">
          <button id="novo">Novo ID</button>
          <button class="primary" id="criar">Criar pedido</button>
          <button id="preparar">Preparar restaurante</button>
          <button id="aceitar">Aceitar pedido</button>
          <button id="confirmar">Confirmar entrega</button>
          <button id="demo-auto">Demo rápida</button>
        </div>
      </section>

      <section>
        <h2>Interfaces da Demo</h2>
        <div class="roles">
          <div class="role">
            <h3>Cliente</h3>
            <p id="cliente-view">Cria o pedido e acompanha a entrega.</p>
            <button class="primary" id="cliente-criar">Criar pedido</button>
            <button id="cliente-confirmar">Confirmar recebimento</button>
          </div>
          <div class="role">
            <h3>Restaurante</h3>
            <p id="restaurante-view">Aguarda pedido disponivel para preparo.</p>
            <button id="restaurante-preparar">Marcar como preparado</button>
          </div>
          <div class="role">
            <h3>Entregador</h3>
            <p id="entregador-view">Aceita pedido e inicia envio de GPS simulado.</p>
            <button id="entregador-aceitar">Aceitar pedido</button>
          </div>
        </div>
      </section>

      <section>
        <h2>Mapa Simulado</h2>
        <div class="map">
          <div class="route"><span class="route-progress" id="route-progress"></span></div>
          <div class="place start">R</div>
          <div class="place end">C</div>
          <div class="driver-dot" id="driver-dot">E</div>
          <div class="route-details">
            <strong id="route-percent">0% do fluxo</strong>
            <span id="route-coords" class="mono">GPS aguardando</span>
          </div>
          <div class="map-status">
            <span>Restaurante</span>
            <span id="map-status">Aguardando pedido</span>
            <span>Cliente</span>
          </div>
        </div>
      </section>

      <section>
        <h2>Etapas do Pedido</h2>
        <div class="timeline" id="timeline"></div>
      </section>

      <section>
        <h2>Pedidos e Roteamento</h2>
        <table>
          <thead><tr><th>Pedido</th><th>Status</th><th>Rest.</th><th>Rastreador</th></tr></thead>
          <tbody id="pedidos"></tbody>
        </table>
      </section>

      <section class="wide">
        <h2>Eventos da Demo</h2>
        <div id="log"></div>
      </section>
    </div>
  </main>

  <script>
    const state = { cluster: null };
    const $ = (id) => document.getElementById(id);
    const nowTs = () => Math.floor(Date.now() / 1000);
    const newId = () => crypto.randomUUID();
    const routeDurationMs = 24000;
    const deliveryStartProgress = 42;
    const routeOrigin = { lat: -23.55052, lon: -46.633308 };
    const routeDestination = { lat: -23.55612, lon: -46.63955 };

    function log(message) {
      const line = `[${new Date().toLocaleTimeString()}] ${message}`;
      $("log").textContent = `${line}\\n${$("log").textContent}`.slice(0, 5000);
    }

    function badge(text, kind = "") {
      return `<span class="badge ${kind}">${text}</span>`;
    }

    async function request(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      const text = await response.text();
      let body = {};
      if (text) {
        try {
          body = JSON.parse(text);
        } catch {
          body = { detail: text };
        }
      }
      if (!response.ok) {
        const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
        throw new Error(detail || `HTTP ${response.status}`);
      }
      return body;
    }

    function currentState() {
      if (!state.cluster) return null;
      return state.cluster.estados.find((item) => item.idServidor === state.cluster.idServidor);
    }

    function currentOrder() {
      const self = currentState();
      if (!self) return null;
      const detalhe = self.pedidosDetalhe || {};
      return detalhe[$("pedido").value] || Object.values(detalhe)[0] || null;
    }

    function routeStorageKey(order) {
      return `dsid-demo-route-start-${order.idPedido}`;
    }

    function routeProgress(order) {
      if (!order || !order.idEntregador) return 0;
      const key = routeStorageKey(order);
      let startedAt = Number(localStorage.getItem(key));
      if (!startedAt) {
        startedAt = Date.now();
        localStorage.setItem(key, String(startedAt));
      }
      const deliveryProgress = Math.min(((Date.now() - startedAt) / routeDurationMs) * 100, 100);
      return deliveryStartProgress + ((100 - deliveryStartProgress) * (deliveryProgress / 100));
    }

    function routeCoords(progress) {
      const ratio = Math.max(0, Math.min(progress, 100)) / 100;
      const lat = routeOrigin.lat + ((routeDestination.lat - routeOrigin.lat) * ratio);
      const lon = routeOrigin.lon + ((routeDestination.lon - routeOrigin.lon) * ratio);
      return `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
    }

    function renderFlow(order) {
      const self = currentState();
      const rabbit = self && self.rabbitmqHabilitado;
      const nodes = [
        ["Cliente", order ? order.idCliente : "-", Boolean(order)],
        ["ADM lider", state.cluster.liderAtual || "-", Boolean(order)],
        ["RabbitMQ", rabbit ? "broker ativo" : "broker off", rabbit],
        ["Restaurante", order ? order.idRestaurante : "-", Boolean(order && order.restaurantePreparou)],
        ["Entregador", order && order.idEntregador ? order.idEntregador : "-", Boolean(order && order.idEntregador)],
        ["Rastreador/SUP", order && order.servidorRastreadorResponsavel ? order.servidorRastreadorResponsavel : "-", Boolean(order && order.servidorRastreadorResponsavel)],
      ];
      $("flow").innerHTML = nodes.map(([name, detail, active]) => {
        return `<div class="node ${active ? "active" : ""}"><strong>${name}</strong><span>${detail}</span></div>`;
      }).join("");
    }

    function renderTimeline(order) {
      const steps = [
        ["Pedido criado", Boolean(order)],
        ["Restaurante preparou", Boolean(order && order.restaurantePreparou)],
        ["Entregador aceitou", Boolean(order && order.idEntregador)],
        ["Rastreador atribuido", Boolean(order && order.servidorRastreadorResponsavel)],
        ["Entrega confirmada", false],
      ];
      $("timeline").innerHTML = steps.map(([label, done]) => {
        return `<div class="step ${done ? "done" : ""}">${label}</div>`;
      }).join("");
    }

    function renderRoleViews(order) {
      const pedidoId = $("pedido").value || "-";
      const cliente = $("cliente").value || "cliente";
      const restaurante = $("restaurante").value || "restaurante";
      const entregador = $("entregador").value || "entregador";

      $("cliente-view").textContent = order
        ? `${cliente} acompanha pedido ${pedidoId.slice(0, 8)}.`
        : `${cliente} ainda nao criou pedido.`;
      $("restaurante-view").textContent = order && order.restaurantePreparou
        ? `${restaurante} marcou o pedido como preparado.`
        : order
          ? `${restaurante} recebeu o pedido e pode preparar.`
          : `${restaurante} aguarda novo pedido.`;
      $("entregador-view").textContent = order && order.idEntregador
        ? `${order.idEntregador} esta em rota via ${order.servidorRastreadorResponsavel || "rastreador"}.`
        : order
          ? `${entregador} pode aceitar o pedido disponivel.`
          : `${entregador} aguarda pedidos disponiveis.`;
    }

    function renderMap(order) {
      let progress = 0;
      let status = "Aguardando pedido";
      let coords = "GPS aguardando";
      if (order) {
        progress = 18;
        status = "Pedido enviado ao restaurante";
      }
      if (order && order.restaurantePreparou) {
        progress = deliveryStartProgress;
        status = "Pedido pronto; aguardando entregador";
      }
      if (order && order.idEntregador) {
        progress = routeProgress(order);
        const rounded = Math.round(progress);
        status = progress >= 100
          ? `Destino alcancado (${order.servidorRastreadorResponsavel || "rastreador"})`
          : `Em rota ${rounded}% (${order.servidorRastreadorResponsavel || "rastreador"})`;
        coords = routeCoords(progress);
      }
      const left = 11 + (progress * 0.78);
      $("route-progress").style.width = `${progress}%`;
      $("driver-dot").style.left = `${left}%`;
      $("driver-dot").classList.toggle("moving", Boolean(order && order.idEntregador && progress < 100));
      $("driver-dot").classList.toggle("arrived", Boolean(order && order.idEntregador && progress >= 100));
      $("map-status").textContent = status;
      $("route-percent").textContent = `${Math.round(progress)}% do fluxo`;
      $("route-coords").textContent = coords;
    }

    function renderCluster() {
      const cluster = state.cluster;
      const self = currentState();
      const order = currentOrder();
      const claimedLeaders = cluster.estados.filter((adm) => adm.online && adm.souLider);
      $("self-id").textContent = cluster.idServidor;
      $("leader-id").textContent = cluster.liderAtual;
      $("rabbit").textContent = self && self.rabbitmqHabilitado ? "on" : "off";

      $("adms").innerHTML = cluster.estados.map((adm) => {
        const status = adm.online ? badge("online", "ok") : badge("offline", "bad");
        const lider = adm.souLider && claimedLeaders.length > 1
          ? badge("lider local", "bad")
          : adm.souLider
            ? badge("lider", "ok")
            : `<span class="muted">${adm.liderAtual || "-"}</span>`;
        return `<tr><td class="mono">${adm.idServidor}</td><td>${status}</td><td>${lider}</td></tr>`;
      }).join("");

      const ativos = self ? self.rastreadoresAtivos : [];
      const expirados = self ? self.rastreadoresComHeartbeatExpirado : [];
      $("trackers").innerHTML = `<tr><td>${ativos.join(", ") || "-"}</td><td>${expirados.join(", ") || "-"}</td></tr>`;

      const pedidos = self ? Object.values(self.pedidosDetalhe || {}) : [];
      $("pedidos").innerHTML = pedidos.map((pedido) => {
        return `<tr>
          <td class="mono">${pedido.idPedido}</td>
          <td>${pedido.status}</td>
          <td>${pedido.restaurantePreparou ? badge("ok", "ok") : badge("pendente")}</td>
          <td>${pedido.servidorRastreadorResponsavel || "-"}<br>${pedido.idEntregador || "-"}</td>
        </tr>`;
      }).join("") || `<tr><td colspan="4" class="muted">Sem pedidos ativos</td></tr>`;
      renderFlow(order);
      renderTimeline(order);
      renderRoleViews(order);
      renderMap(order);

      const souLider = self && self.souLider;
      for (const id of ["criar", "preparar", "aceitar", "confirmar", "demo-auto"]) $(id).disabled = !souLider;
      for (const id of ["cliente-criar", "restaurante-preparar", "entregador-aceitar", "cliente-confirmar"]) $(id).disabled = !souLider;
      $("command-status").value = claimedLeaders.length > 1
        ? "Cluster inconsistente: reinicie os ADMs"
        : souLider ? "ADM lider" : "Abra comandos no lider";
      $("updated-at").value = new Date().toLocaleTimeString();
    }

    async function refresh() {
      state.cluster = await request("/demo/cluster");
      renderCluster();
    }

    async function criarPedido() {
      if (!$("pedido").value) $("pedido").value = newId();
      const body = {
        idPedido: $("pedido").value,
        idCliente: $("cliente").value,
        idRestaurante: $("restaurante").value,
        timestamp: nowTs(),
      };
      const pedido = await request("/pedidos", { method: "POST", body: JSON.stringify(body) });
      log(`pedido criado ${pedido.idPedido}`);
      await refresh();
    }

    function novoPedido() {
      $("pedido").value = newId();
      log(`novo pedido selecionado ${$("pedido").value}`);
      renderCluster();
    }

    async function aceitarPedido() {
      const body = {
        idPedido: $("pedido").value,
        idEntregador: $("entregador").value,
        timestamp: nowTs(),
      };
      const pedido = await request("/pedidos/aceitar", { method: "POST", body: JSON.stringify(body) });
      log(`pedido aceito ${pedido.idPedido} -> ${pedido.servidorRastreadorResponsavel}`);
      await refresh();
    }

    async function prepararPedido() {
      const body = {
        idPedido: $("pedido").value,
        idRestaurante: $("restaurante").value,
        timestamp: nowTs(),
      };
      const pedido = await request("/pedidos/preparar", { method: "POST", body: JSON.stringify(body) });
      log(`restaurante preparou ${pedido.idPedido}`);
      await refresh();
    }

    async function confirmarEntrega() {
      const order = currentOrder();
      const body = {
        idPedido: $("pedido").value,
        idCliente: $("cliente").value,
        timestamp: nowTs(),
      };
      const evento = await request("/pedidos/confirmar", { method: "POST", body: JSON.stringify(body) });
      if (order) localStorage.removeItem(routeStorageKey(order));
      log(`entrega confirmada ${evento.idPedido}`);
      await refresh();
    }

    async function keepAlive(tracker) {
      const body = { idServidor: tracker, tipoServidor: "RASTREADOR", timestamp: nowTs() };
      await request("/infra/keepalive", { method: "POST", body: JSON.stringify(body) });
      log(`keepAlive ${tracker}`);
      await refresh();
    }

    async function demoRapida() {
      await keepAlive("rastreador-1");
      await keepAlive("rastreador-2");
      await criarPedido();
      await prepararPedido();
      await aceitarPedido();
    }

    $("pedido").value = newId();
    $("refresh").addEventListener("click", () => refresh().catch((err) => log(err.message)));
    $("novo").addEventListener("click", () => novoPedido());
    $("criar").addEventListener("click", () => criarPedido().catch((err) => log(err.message)));
    $("aceitar").addEventListener("click", () => aceitarPedido().catch((err) => log(err.message)));
    $("preparar").addEventListener("click", () => prepararPedido().catch((err) => log(err.message)));
    $("confirmar").addEventListener("click", () => confirmarEntrega().catch((err) => log(err.message)));
    $("cliente-criar").addEventListener("click", () => criarPedido().catch((err) => log(err.message)));
    $("restaurante-preparar").addEventListener("click", () => prepararPedido().catch((err) => log(err.message)));
    $("entregador-aceitar").addEventListener("click", () => aceitarPedido().catch((err) => log(err.message)));
    $("cliente-confirmar").addEventListener("click", () => confirmarEntrega().catch((err) => log(err.message)));
    $("demo-auto").addEventListener("click", () => demoRapida().catch((err) => log(err.message)));
    document.querySelectorAll("[data-tracker]").forEach((button) => {
      button.addEventListener("click", () => keepAlive(button.dataset.tracker).catch((err) => log(err.message)));
    });

    refresh().catch((err) => log(err.message));
    setInterval(() => refresh().catch(() => {}), 3000);
    setInterval(() => renderMap(currentOrder()), 500);
  </script>
</body>
</html>
"""
