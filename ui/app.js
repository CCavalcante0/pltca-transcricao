// Estado local
const state = {
  fila: [],
  resultados: {},   // { path: texto }
  selecionado: null,
  transcrevendo: false,
};

// ── Inicialização ─────────────────────────────────────────────────

window.addEventListener("pywebviewready", () => {
  // pronto
});

// ── Ações do usuário ──────────────────────────────────────────────

async function adicionarArquivos() {
  const fila = await pywebview.api.selecionar_arquivos();
  state.fila = fila;
  renderFila();
}

async function limparFila() {
  const res = await pywebview.api.limpar_fila();
  if (res.ok) {
    state.fila = [];
    renderFila();
    setStatus("");
  } else {
    setStatus(res.msg || "Não é possível limpar agora.");
  }
}

async function transcrever() {
  if (state.transcrevendo || state.fila.length === 0) return;
  const res = await pywebview.api.iniciar_transcricao();
  if (res.ok) {
    setTranscribing(true);
  }
}

async function copiar() {
  const texto = getTextoAtivo();
  if (!texto) return;
  await pywebview.api.copiar(texto);
  setStatus("Copiado!");
  setTimeout(() => setStatus(""), 2000);
}

async function salvar() {
  const texto = getTextoAtivo();
  if (!texto) return;
  const nome = state.selecionado
    ? state.selecionado.split("/").pop().replace(/\.[^.]+$/, "") + ".txt"
    : "transcricao.txt";
  await pywebview.api.salvar(texto, nome);
}

function selecionarVideo(path) {
  state.selecionado = path;
  renderSidebar();
  mostrarTranscricao(path);
}

// ── Chamadas do Python ────────────────────────────────────────────

function setProgress(pct, status) {
  document.getElementById("progress-fill").style.width = (pct * 100) + "%";
  setStatus(status);
}

function setStatus(msg) {
  document.getElementById("status-text").textContent = msg;
}

function setQueueActive(idx) {
  // atualiza visual da fila com item ativo
  renderFila(idx);
}

function updatePreview(path, texto) {
  // seleciona automaticamente o primeiro vídeo que começa a ser transcrito
  if (!state.selecionado) {
    state.selecionado = path;
    renderSidebar();
    document.getElementById("results-filename").textContent =
      path.split("/").pop();
  }
  if (state.selecionado === path) {
    const box = document.getElementById("transcription-box");
    box.textContent = texto;
    box.scrollTop = box.scrollHeight;
  }
}

function addResult(path, nome, texto) {
  state.resultados[path] = texto;
  state.selecionado = state.selecionado || path;
  renderSidebar();
  if (state.selecionado === path) {
    mostrarTranscricao(path);
  }
}

function setTranscribing(val) {
  state.transcrevendo = val;
  const btn = document.getElementById("btn-transcribe");
  btn.disabled = val;
  btn.textContent = val ? "Transcrevendo…" : "Transcrever";
}

function onComplete() {
  state.fila = [];
  renderFila();
}

// ── Render ────────────────────────────────────────────────────────

function renderFila(activeIdx) {
  const el = document.getElementById("queue-list");
  if (state.fila.length === 0) {
    el.innerHTML = '<span class="placeholder">Nenhum arquivo adicionado</span>';
    return;
  }
  el.innerHTML = state.fila.map((nome, i) => {
    const ativo = activeIdx !== undefined && i === activeIdx;
    return `
      <div class="queue-item ${ativo ? "active" : ""}">
        <span class="queue-dot"></span>
        <span>${escHtml(nome)}</span>
      </div>`;
  }).join("");
}

function renderSidebar() {
  const el = document.getElementById("results-sidebar");
  const paths = Object.keys(state.resultados);
  if (paths.length === 0) {
    el.innerHTML = '<span class="placeholder small">Nenhum vídeo<br>transcrito ainda</span>';
    return;
  }
  el.innerHTML = paths.map(path => {
    const nome = path.split("/").pop();
    const ativo = path === state.selecionado;
    return `
      <button class="video-btn ${ativo ? "active" : ""}"
              onclick="selecionarVideo(${JSON.stringify(path)})"
              title="${escHtml(nome)}">
        ${escHtml(nome)}
      </button>`;
  }).join("");
}

function mostrarTranscricao(path) {
  const texto = state.resultados[path] || "";
  const nome = path.split("/").pop();
  document.getElementById("results-filename").textContent = nome;
  const box = document.getElementById("transcription-box");
  if (texto) {
    box.textContent = texto;
  } else {
    box.innerHTML = '<span class="placeholder">A transcrição aparecerá aqui…</span>';
  }
}

function getTextoAtivo() {
  if (!state.selecionado) return null;
  return state.resultados[state.selecionado] || null;
}

function escHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
