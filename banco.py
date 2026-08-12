"""
Banco local do app de transcrição.

Motivo de existir: as transcrições viviam como .txt em pasta, com nome de
UUID, e as pastas misturavam cliente com estágio ("Postados Fulano") e com
pauta ("Fulano - buracos"). Nesse formato não dá para responder "quais
vídeos do candidato já foram publicados" — que é a pergunta central do
produto. Aqui cliente, pauta e status são dimensões separadas.
"""

import sqlite3
import json
import threading
from pathlib import Path
from datetime import datetime

BANCO_PATH = Path(__file__).parent / "transcricoes.db"

# Fluxo de um vídeo. A ordem importa: é usada para ordenar e para saber
# se um status é "mais avançado" que outro.
STATUS = ["transcrito", "legenda_gerada", "aprovado", "publicado"]

_lock = threading.Lock()

ESQUEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clientes (
    id         INTEGER PRIMARY KEY,
    nome       TEXT    NOT NULL UNIQUE,
    estilo     TEXT    NOT NULL DEFAULT '',
    criado_em  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS videos (
    id              INTEGER PRIMARY KEY,
    cliente_id      INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    titulo          TEXT    NOT NULL,
    pauta           TEXT    NOT NULL DEFAULT '',
    arquivo_origem  TEXT,
    duracao_seg     REAL,
    transcricao     TEXT    NOT NULL DEFAULT '',
    segmentos_json  TEXT,
    locutores_json  TEXT,
    status          TEXT    NOT NULL DEFAULT 'transcrito',
    transcrito_em   TEXT,
    publicado_em    TEXT,
    plataforma      TEXT,
    link_post       TEXT,
    origem_import   TEXT,
    UNIQUE (cliente_id, titulo)
);

CREATE TABLE IF NOT EXISTS legendas (
    id         INTEGER PRIMARY KEY,
    video_id   INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    headline   TEXT NOT NULL DEFAULT '',
    legenda    TEXT NOT NULL DEFAULT '',
    aprovada   INTEGER NOT NULL DEFAULT 0,
    origem     TEXT NOT NULL DEFAULT 'manual',
    criada_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cortes (
    id          INTEGER PRIMARY KEY,
    video_id    INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    inicio_seg  REAL    NOT NULL,
    fim_seg     REAL    NOT NULL,
    texto       TEXT    NOT NULL DEFAULT '',
    locutor     TEXT    NOT NULL DEFAULT '',
    rotulo      TEXT    NOT NULL DEFAULT '',
    origem      TEXT    NOT NULL DEFAULT 'manual',
    criado_em   TEXT    NOT NULL,
    UNIQUE (video_id, inicio_seg, fim_seg)
);

CREATE INDEX IF NOT EXISTS idx_cortes_video    ON cortes (video_id);
CREATE INDEX IF NOT EXISTS idx_videos_cliente  ON videos (cliente_id);
CREATE INDEX IF NOT EXISTS idx_videos_status   ON videos (status);
CREATE INDEX IF NOT EXISTS idx_legendas_video  ON legendas (video_id);
CREATE INDEX IF NOT EXISTS idx_legendas_aprov  ON legendas (video_id, aprovada);
"""


def conectar():
    con = sqlite3.connect(BANCO_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def iniciar():
    """Cria o banco se não existir. Idempotente."""
    with _lock, conectar() as con:
        con.executescript(ESQUEMA)
    return BANCO_PATH


def _agora():
    return datetime.now().isoformat(timespec="seconds")


# ── Clientes ──────────────────────────────────────────────────────────

def criar_cliente(nome, estilo=""):
    nome = nome.strip()
    if not nome:
        raise ValueError("nome do cliente não pode ser vazio")
    with _lock, conectar() as con:
        cur = con.execute(
            "INSERT INTO clientes (nome, estilo, criado_em) VALUES (?, ?, ?) "
            "ON CONFLICT(nome) DO UPDATE SET nome = nome RETURNING id",
            (nome, estilo, _agora()))
        return cur.fetchone()["id"]


def listar_clientes():
    with _lock, conectar() as con:
        return [dict(r) for r in con.execute("""
            SELECT c.id, c.nome, c.estilo,
                   COUNT(v.id)                                        AS videos,
                   SUM(v.status = 'publicado')                        AS publicados,
                   SUM(v.status != 'publicado')                       AS pendentes
              FROM clientes c
              LEFT JOIN videos v ON v.cliente_id = c.id
             GROUP BY c.id
             ORDER BY c.nome
        """)]


# ── Vídeos ────────────────────────────────────────────────────────────

def salvar_video(cliente_id, titulo, transcricao, *, pauta="", arquivo_origem=None,
                 duracao_seg=None, segmentos=None, locutores=None,
                 status="transcrito", origem_import=None):
    """
    Grava ou atualiza um vídeo. Chave natural é (cliente, título): re-salvar
    a mesma transcrição atualiza em vez de duplicar.
    O status só avança — regravar a transcrição de um vídeo já publicado não
    o rebaixa para 'transcrito'.
    """
    with _lock, conectar() as con:
        atual = con.execute(
            "SELECT id, status FROM videos WHERE cliente_id = ? AND titulo = ?",
            (cliente_id, titulo)).fetchone()

        if atual and STATUS.index(atual["status"]) > STATUS.index(status):
            status = atual["status"]

        cur = con.execute("""
            INSERT INTO videos (cliente_id, titulo, pauta, arquivo_origem, duracao_seg,
                                transcricao, segmentos_json, locutores_json, status,
                                transcrito_em, origem_import)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT (cliente_id, titulo) DO UPDATE SET
                pauta          = CASE WHEN excluded.pauta != ''
                                      THEN excluded.pauta ELSE videos.pauta END,
                arquivo_origem = COALESCE(excluded.arquivo_origem, videos.arquivo_origem),
                duracao_seg    = COALESCE(excluded.duracao_seg, videos.duracao_seg),
                transcricao    = excluded.transcricao,
                segmentos_json = COALESCE(excluded.segmentos_json, videos.segmentos_json),
                locutores_json = COALESCE(excluded.locutores_json, videos.locutores_json),
                status         = excluded.status
            RETURNING id
        """, (cliente_id, titulo, pauta, arquivo_origem, duracao_seg, transcricao,
              json.dumps(segmentos) if segmentos else None,
              json.dumps(locutores) if locutores else None,
              status, _agora(), origem_import))
        return cur.fetchone()["id"]


def marcar_publicado(video_id, plataforma=None, link=None, quando=None):
    with _lock, conectar() as con:
        con.execute("""UPDATE videos SET status='publicado', publicado_em=?,
                       plataforma=?, link_post=? WHERE id=?""",
                    (quando or _agora(), plataforma, link, video_id))
    return True


def definir_status(video_id, status):
    if status not in STATUS:
        raise ValueError(f"status inválido: {status}")
    with _lock, conectar() as con:
        con.execute("UPDATE videos SET status=? WHERE id=?", (status, video_id))
    return True


def listar_videos(cliente_id=None, status=None, busca=None):
    sql = """SELECT v.*, c.nome AS cliente
               FROM videos v JOIN clientes c ON c.id = v.cliente_id
              WHERE 1=1"""
    args = []
    if cliente_id:
        sql += " AND v.cliente_id = ?";                     args.append(cliente_id)
    if status:
        sql += " AND v.status = ?";                         args.append(status)
    if busca:
        sql += " AND (v.titulo LIKE ? OR v.transcricao LIKE ? OR v.pauta LIKE ?)"
        args += [f"%{busca}%"] * 3
    sql += " ORDER BY v.transcrito_em DESC"
    with _lock, conectar() as con:
        return [dict(r) for r in con.execute(sql, args)]


def resumo_cliente(cliente_id):
    """Responde 'o que já saiu e o que está parado' de um cliente."""
    with _lock, conectar() as con:
        linhas = con.execute(
            "SELECT status, COUNT(*) n FROM videos WHERE cliente_id=? GROUP BY status",
            (cliente_id,)).fetchall()
        return {s: 0 for s in STATUS} | {r["status"]: r["n"] for r in linhas}


# ── Legendas ──────────────────────────────────────────────────────────

def salvar_legenda(video_id, headline, legenda, origem="manual", aprovada=False):
    with _lock, conectar() as con:
        cur = con.execute("""INSERT INTO legendas (video_id, headline, legenda,
                             aprovada, origem, criada_em) VALUES (?,?,?,?,?,?)
                             RETURNING id""",
                          (video_id, headline, legenda, int(aprovada), origem, _agora()))
        lid = cur.fetchone()["id"]
        if aprovada:
            con.execute("UPDATE legendas SET aprovada=0 WHERE video_id=? AND id!=?",
                        (video_id, lid))
            con.execute("""UPDATE videos SET status='aprovado' WHERE id=?
                           AND status IN ('transcrito','legenda_gerada')""", (video_id,))
        else:
            con.execute("""UPDATE videos SET status='legenda_gerada' WHERE id=?
                           AND status='transcrito'""", (video_id,))
        return lid


# ── Cortes ────────────────────────────────────────────────────────────

def salvar_corte(video_id, inicio, fim, texto="", locutor="", rotulo="", origem="manual"):
    with _lock, conectar() as con:
        cur = con.execute("""
            INSERT INTO cortes (video_id, inicio_seg, fim_seg, texto, locutor,
                                rotulo, origem, criado_em)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT (video_id, inicio_seg, fim_seg) DO UPDATE SET
                rotulo = excluded.rotulo,
                texto  = excluded.texto
            RETURNING id
        """, (video_id, float(inicio), float(fim), texto, locutor,
              rotulo, origem, _agora()))
        return cur.fetchone()["id"]


def listar_cortes(video_id):
    with _lock, conectar() as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM cortes WHERE video_id=? ORDER BY inicio_seg", (video_id,))]


def remover_corte(corte_id):
    with _lock, conectar() as con:
        con.execute("DELETE FROM cortes WHERE id=?", (corte_id,))
    return True


def exemplos_de_estilo(cliente_id, limite=8):
    """
    Pares transcrição→legenda aprovada, para alimentar o few-shot da IA.
    É isto que faz a legenda sair no tom do assessorado sem treinar modelo.
    """
    with _lock, conectar() as con:
        return [dict(r) for r in con.execute("""
            SELECT v.transcricao, l.headline, l.legenda
              FROM legendas l JOIN videos v ON v.id = l.video_id
             WHERE v.cliente_id = ? AND l.aprovada = 1
             ORDER BY l.criada_em DESC LIMIT ?
        """, (cliente_id, limite))]
