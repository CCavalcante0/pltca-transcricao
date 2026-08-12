import webview
import threading
import subprocess
import traceback
import tempfile
import tarfile
import shutil
import queue
import time
import json
import sys
import os
from urllib.request import urlopen
from pathlib import Path
from datetime import date

import banco

WINDOWS = sys.platform.startswith("win")
MACOS   = sys.platform == "darwin"

MODELO = "large-v3-turbo"
EXTENSOES = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".opus", ".webm"}
PROJETOS_DIR  = Path(__file__).parent / "projetos"
GRAVACOES_DIR = Path(__file__).parent / "gravacoes"
MODELOS_DIR   = Path(__file__).parent / "modelos"
SEG_MODEL     = MODELOS_DIR / "sherpa-onnx-pyannote-segmentation-3-0" / "model.onnx"
EMB_MODEL     = MODELOS_DIR / "campplus.onnx"


_REL = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
URL_SEG = f"{_REL}/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
URL_EMB = (f"{_REL}/speaker-recongition-models/"
           "3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx")


def _baixar(url, destino: Path, rotulo, progresso=None):
    """Baixa com barra de progresso. Escreve em .parcial e só renomeia no fim,
    para um download interrompido não passar por modelo válido."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_suffix(destino.suffix + ".parcial")
    with urlopen(url) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        lido = 0
        with open(parcial, "wb") as f:
            while True:
                bloco = resp.read(262144)
                if not bloco:
                    break
                f.write(bloco)
                lido += len(bloco)
                if progresso and total:
                    progresso(rotulo, lido / total)
    parcial.replace(destino)


def progresso_console():
    """Callback de progresso para os instaladores: uma linha a cada 10%,
    em vez de uma por bloco (\\r não limpa quando a saída não é terminal)."""
    ultimo = {}

    def _p(rotulo, frac):
        marca = int(frac * 100) // 10
        if ultimo.get(rotulo) != marca:
            ultimo[rotulo] = marca
            print(f"  {rotulo}: {marca * 10}%", flush=True)
    return _p


def garantir_modelos_diarizacao(progresso=None):
    """
    Baixa os ~34 MB de diarização na primeira vez que forem necessários.
    Ficam fora do repositório de propósito: código é 120 KB, modelo não.
    """
    if SEG_MODEL.exists() and EMB_MODEL.exists():
        return True

    MODELOS_DIR.mkdir(parents=True, exist_ok=True)

    if not SEG_MODEL.exists():
        tar_tmp = MODELOS_DIR / "seg.tar.bz2"
        _baixar(URL_SEG, tar_tmp, "modelo de segmentação", progresso)
        with tarfile.open(tar_tmp, "r:bz2") as tf:
            membros = [m for m in tf.getmembers()
                       if not (m.name.startswith("/") or ".." in Path(m.name).parts)]
            tf.extractall(MODELOS_DIR, members=membros)
        tar_tmp.unlink(missing_ok=True)

    if not EMB_MODEL.exists():
        _baixar(URL_EMB, EMB_MODEL, "modelo de voz", progresso)

    return SEG_MODEL.exists() and EMB_MODEL.exists()


def ffmpeg_ok():
    """ffmpeg é dependência dura: gravação, duração e diarização passam por ele."""
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def copiar_clipboard(texto: str) -> bool:
    """Copia texto para a área de transferência em macOS, Windows e Linux."""
    try:
        if MACOS:
            subprocess.run("pbcopy", input=texto.encode("utf-8"), check=True)
            return True
        if WINDOWS:
            # clip.exe estraga acento; PowerShell lendo UTF-8 de arquivo não.
            tmp = Path(tempfile.gettempdir()) / "_transcricao_clip.txt"
            tmp.write_text(texto, encoding="utf-8")
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-Content -Raw -Encoding UTF8 '{tmp}' | Set-Clipboard"],
                check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            tmp.unlink(missing_ok=True)
            return True
        for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
            if shutil.which(cmd[0]):
                subprocess.run(cmd, input=texto.encode("utf-8"), check=True)
                return True
        return False
    except Exception:
        return False


def abrir_no_gerenciador(pasta: Path):
    """Abre a pasta no Finder / Explorer / gerenciador do Linux."""
    try:
        if WINDOWS:
            os.startfile(str(pasta))            # noqa: S606 — só no Windows
        elif MACOS:
            subprocess.run(["open", str(pasta)], check=False)
        else:
            subprocess.run(["xdg-open", str(pasta)], check=False)
        return True
    except Exception:
        return False


def notificar_sistema(titulo: str, msg: str):
    """Notificação nativa onde existir; um bipe onde não existir."""
    try:
        if MACOS:
            subprocess.run(
                ["osascript", "-e",
                 f'display notification "{msg}" with title "{titulo}" sound name "Glass"'],
                check=False, capture_output=True)
        elif WINDOWS:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        elif shutil.which("notify-send"):
            subprocess.run(["notify-send", titulo, msg], check=False)
    except Exception:
        pass


def get_duracao(path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True
        )
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return None


def _fmt_time(segundos: float) -> str:
    """Converte segundos em HH:MM:SS."""
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _fmt_srt_time(segundos: float) -> str:
    """Converte segundos em HH:MM:SS,mmm (formato SRT)."""
    h  = int(segundos // 3600)
    m  = int((segundos % 3600) // 60)
    s  = int(segundos % 60)
    ms = int(round((segundos % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _salvar_txt(destino: Path, texto: str):
    """Salva texto em UTF-8. Retorna True se sucesso."""
    try:
        destino.write_text(texto, encoding="utf-8")
        return True
    except Exception:
        return False


class API:
    def __init__(self):
        self.fila          = []
        self.resultados    = {}          # { video_path: texto }
        self.segmentos     = {}          # { video_path: [{start, end, text}] }
        self.whisper_model = None
        self.transcrevendo = False
        # Diarização (quem falou o quê)
        self.diarizando      = False
        self.locutores       = {}        # { path: [{start, end, speaker}] }
        self.nomes_locutores = {}        # { path: {idx_locutor: "Roberto"} }
        self._diar_lock      = threading.Lock()
        self.video_ids       = {}        # { path da sessão: id no banco }
        banco.iniciar()
        self.window        = None
        self._model_lock   = threading.Lock()
        self.projeto_ativo = None
        self._salvos_sessao = set()     # (projeto, video_path) já salvos nesta sessão
        self._escritos_por_nos = set()  # .txt que este app criou (pode sobrescrever)
        # Gravação de áudio — streaming direto pro disco via ffmpeg.
        # Nada de acumular frames na RAM: 90 min a 44.1kHz seriam ~900 MB.
        self.gravando           = False
        self._gravacao_sr       = 44100
        self._gravacao_stream   = None
        self._gravacao_proc     = None
        self._gravacao_fila     = None    # queue.Queue de bytes PCM
        self._gravacao_writer   = None
        self._gravacao_path     = None
        self._gravacao_erro     = None
        self._gravacao_perdidos = 0       # blocos descartados por fila cheia
        PROJETOS_DIR.mkdir(exist_ok=True)
        GRAVACOES_DIR.mkdir(exist_ok=True)

    def _js(self, fn, *args):
        """Envia chamada JS de forma não-bloqueante (thread separada)."""
        args_str = ", ".join(json.dumps(a) for a in args)
        js = f"{fn}({args_str})"
        threading.Thread(target=self.window.evaluate_js, args=(js,), daemon=True).start()

    # ── Projetos ──────────────────────────────────────────────────────────

    # "Projeto" na interface é "cliente" no banco. O banco é a fonte da
    # verdade desde 12/08/2026 — pasta com .txt não respondia "já publiquei
    # esse vídeo?", que é a pergunta que o social media faz o dia inteiro.

    def listar_projetos(self):
        try:
            return [c["nome"] for c in banco.listar_clientes()]
        except Exception:
            return []

    def criar_projeto(self, nome):
        nome = (nome or "").strip()
        if not nome:
            return {"ok": False, "msg": "Nome não pode ser vazio."}
        if nome in self.listar_projetos():
            return {"ok": False, "msg": "Cliente já existe."}
        banco.criar_cliente(nome)
        self.projeto_ativo = nome
        return {"ok": True, "projetos": self.listar_projetos(), "ativo": nome}

    def _cliente_id(self, nome=None):
        nome = nome or self.projeto_ativo
        if not nome:
            return None
        for c in banco.listar_clientes():
            if c["nome"] == nome:
                return c["id"]
        return None

    def set_projeto_ativo(self, nome):
        self.projeto_ativo = nome
        return {"ok": True, "transcricoes": self.listar_transcricoes(nome)}

    def listar_transcricoes(self, projeto):
        cid = self._cliente_id(projeto)
        if not cid:
            return []
        return [
            {"nome": v["titulo"], "path": f"db:{v['id']}",
             "status": v["status"], "pauta": v["pauta"]}
            for v in banco.listar_videos(cliente_id=cid)
        ]

    def ler_transcricao(self, chave):
        if str(chave).startswith("db:"):
            try:
                vid = int(str(chave)[3:])
            except ValueError:
                return {"ok": False, "texto": ""}
            for v in banco.listar_videos():
                if v["id"] == vid:
                    return {"ok": True, "texto": v["transcricao"], "status": v["status"]}
            return {"ok": False, "texto": ""}
        # compatibilidade com .txt antigos abertos por caminho
        p = Path(chave).resolve()
        if not str(p).startswith(str(PROJETOS_DIR.resolve())):
            return {"ok": False, "texto": ""}
        try:
            return {"ok": True, "texto": p.read_text(encoding="utf-8")}
        except Exception:
            return {"ok": False, "texto": ""}

    def _persistir_video(self, path, status="transcrito"):
        """Grava o vídeo da sessão no banco sob o cliente ativo. Devolve o id."""
        cid = self._cliente_id()
        if not cid:
            return None
        vid = banco.salvar_video(
            cid, Path(path).stem, self.resultados.get(path, ""),
            arquivo_origem=path,
            duracao_seg=get_duracao(path),
            segmentos=self.segmentos.get(path),
            locutores=self.nomes_locutores.get(path),
            status=status,
        )
        self.video_ids[path] = vid
        return vid

    def filtrar_nao_salvos(self, projeto, paths):
        """Retorna apenas os paths que ainda não foram salvos neste projeto nesta sessão."""
        return [p for p in paths if (projeto, p) not in self._salvos_sessao]

    def atualizar_texto(self, path, texto):
        """
        Recebe do JS o texto editado à mão.
        Sem isto, self.resultados guardava só a versão original do Whisper e
        salvar_no_projeto/exportar_todos gravavam a correção do usuário fora.
        """
        if path not in self.resultados:
            return {"ok": False}
        if self.resultados[path] == texto:
            return {"ok": True}
        self.resultados[path] = texto
        # Texto mudou: libera regravar nos projetos onde já havia sido salvo.
        for chave in [c for c in self._salvos_sessao if c[1] == path]:
            self._salvos_sessao.discard(chave)
        return {"ok": True}

    def salvar_no_projeto(self, projeto, paths):
        """
        Salva as transcrições no projeto E uma cópia .txt na pasta de origem do vídeo.
        Retorna quais foram salvos, pulados (duplicatas) e se a cópia local funcionou.
        """
        pasta_projeto = PROJETOS_DIR / projeto
        pasta_projeto.mkdir(exist_ok=True)
        salvos  = []
        pulados = []
        hoje    = date.today().isoformat()

        for path in paths:
            if (projeto, path) in self._salvos_sessao:
                pulados.append(os.path.basename(path))
                continue

            texto = self.resultados.get(path, "")
            if not texto:
                continue

            base = Path(path).stem

            # 1. Salva no projeto (com data no nome)
            nome_projeto = f"{hoje} {base}.txt"
            destino_projeto = pasta_projeto / nome_projeto
            if destino_projeto.exists():
                i = 2
                while (pasta_projeto / f"{hoje} {base} ({i}).txt").exists():
                    i += 1
                destino_projeto = pasta_projeto / f"{hoje} {base} ({i}).txt"
            _salvar_txt(destino_projeto, texto)

            # 2. Salva cópia ao lado do vídeo original.
            # Só sobrescreve o que este app escreveu — um .txt de anotação do
            # usuário com o mesmo nome não pode ser apagado calado.
            copia_local = Path(path).parent / (base + ".txt")
            if copia_local.exists() and copia_local not in self._escritos_por_nos:
                # Nome ocupado por um .txt que não fomos nós que criamos.
                # Sufixo fixo em vez de (2), (3)…: salvar de novo atualiza o
                # mesmo arquivo em vez de encher a pasta de cópias.
                copia_local = Path(path).parent / f"{base}.transcricao.txt"
            if _salvar_txt(copia_local, texto):
                self._escritos_por_nos.add(copia_local)

            # O registro no banco é o que importa; os .txt acima são cópia
            # de conveniência para quem prefere abrir arquivo.
            anterior = self.projeto_ativo
            self.projeto_ativo = projeto
            vid = self._persistir_video(path)
            self.projeto_ativo = anterior

            self._salvos_sessao.add((projeto, path))
            salvos.append({"nome": Path(path).stem, "path": f"db:{vid}"})

        return {
            "ok": True,
            "salvos":      salvos,
            "pulados":     pulados,
            "transcricoes": self.listar_transcricoes(projeto),
        }

    def abrir_pasta_projeto(self, projeto):
        if not projeto:
            return {"ok": False}
        pasta = PROJETOS_DIR / projeto
        pasta.mkdir(exist_ok=True)
        abrir_no_gerenciador(pasta)
        return {"ok": True}

    # ── Gravação de áudio ─────────────────────────────────────────────────

    def listar_dispositivos(self):
        """Retorna lista de dispositivos de entrada disponíveis."""
        try:
            import sounddevice as sd
            devs = sd.query_devices()
            return [
                {"idx": i, "nome": d["name"]}
                for i, d in enumerate(devs)
                if d["max_input_channels"] > 0
            ]
        except Exception as e:
            return []

    def iniciar_gravacao(self, dispositivo_idx):
        if self.gravando:
            return {"ok": False, "msg": "Já está gravando."}
        try:
            import sounddevice as sd
            from datetime import datetime

            device_info = sd.query_devices(int(dispositivo_idx), "input")
            sr = int(device_info["default_samplerate"])

            nome = f"gravacao_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.m4a"
            path = str(GRAVACOES_DIR / nome)

            # ffmpeg lê PCM cru do stdin e escreve AAC no disco conforme grava.
            # 90 min viram ~130 MB em vez de ~900 MB de WAV.
            proc = subprocess.Popen(
                ["ffmpeg", "-hide_banner", "-loglevel", "error",
                 "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0",
                 "-c:a", "aac", "-b:a", "128k", "-y", path],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

            self._gravacao_sr       = sr
            self._gravacao_path     = path
            self._gravacao_proc     = proc
            self._gravacao_erro     = None
            self._gravacao_perdidos = 0
            # ~4096 blocos de 1024 frames ≈ 95 s de colchão a 44.1 kHz, por 16 MB
            # de RAM. Precisa ser grande: se o disco engasgar numa gravação de
            # 90 min, o que transborda daqui é fala perdida para sempre.
            self._gravacao_fila     = queue.Queue(maxsize=4096)
            self.gravando           = True

            # O callback do sounddevice roda em thread de áudio de tempo real:
            # ele só enfileira. Quem bloqueia escrevendo no ffmpeg é o writer.
            def _writer():
                while True:
                    bloco = self._gravacao_fila.get()
                    if bloco is None:
                        break
                    try:
                        proc.stdin.write(bloco)
                    except Exception as e:
                        self._gravacao_erro = str(e)
                        break
                try:
                    proc.stdin.close()
                except Exception:
                    pass

            def _callback(indata, frames, time_info, status):
                try:
                    self._gravacao_fila.put_nowait(indata.tobytes())
                except queue.Full:
                    self._gravacao_perdidos += 1

            stream = sd.InputStream(samplerate=sr, device=int(dispositivo_idx),
                                    channels=1, dtype="float32", callback=_callback)
            stream.start()

            self._gravacao_stream = stream
            self._gravacao_writer = threading.Thread(target=_writer, daemon=True)
            self._gravacao_writer.start()
            return {"ok": True}
        except Exception as e:
            self.gravando = False
            self._encerrar_gravacao()
            return {"ok": False, "msg": str(e)}

    def _encerrar_gravacao(self):
        """Fecha stream, writer e ffmpeg. Seguro de chamar mais de uma vez."""
        if self._gravacao_stream is not None:
            try:
                self._gravacao_stream.stop()
                self._gravacao_stream.close()
            except Exception:
                pass
            self._gravacao_stream = None

        if self._gravacao_fila is not None:
            try:
                self._gravacao_fila.put_nowait(None)   # sinaliza fim ao writer
            except queue.Full:
                # fila entupida: esvazia o suficiente para o sinal entrar
                try:
                    self._gravacao_fila.get_nowait()
                    self._gravacao_fila.put_nowait(None)
                except Exception:
                    pass

        if self._gravacao_writer is not None:
            self._gravacao_writer.join(timeout=10)
            self._gravacao_writer = None

        proc = self._gravacao_proc
        self._gravacao_proc = None
        if proc is not None:
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                _, err = proc.communicate(timeout=30)
                if proc.returncode not in (0, None) and not self._gravacao_erro:
                    self._gravacao_erro = (err or b"").decode(errors="replace")[:200]
            except Exception:
                proc.kill()

    def parar_gravacao(self):
        if not self.gravando:
            return {"ok": False, "msg": "Nenhuma gravação ativa."}
        self.gravando = False

        path = self._gravacao_path
        self._encerrar_gravacao()

        if self._gravacao_erro:
            return {"ok": False, "msg": f"Erro ao gravar: {self._gravacao_erro}"}
        if not path or not os.path.exists(path) or os.path.getsize(path) < 1024:
            return {"ok": False, "msg": "Nenhum áudio capturado."}

        if path not in self.fila:
            self.fila.append(path)

        aviso = ""
        if self._gravacao_perdidos:
            aviso = f" ({self._gravacao_perdidos} bloco(s) descartado(s) — disco lento)"

        return {"ok": True, "path": path, "nome": os.path.basename(path),
                "aviso": aviso,
                "fila": [os.path.basename(p) for p in self.fila]}

    # ── Fila ──────────────────────────────────────────────────────────────

    def selecionar_arquivos(self):
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=(
                "Vídeo e áudio (*.mp4;*.mkv;*.avi;*.mov;*.m4v;*.mp3;*.wav;*.m4a;*.ogg;*.flac;*.opus;*.webm)",
                "Todos os arquivos (*.*)",
            ),
        )
        if result:
            for p in result:
                if os.path.splitext(p)[1].lower() in EXTENSOES and p not in self.fila:
                    self.fila.append(p)
        return [os.path.basename(p) for p in self.fila]

    def adicionar_por_paths(self, paths):
        for p in paths:
            if os.path.splitext(p)[1].lower() in EXTENSOES and p not in self.fila:
                self.fila.append(p)
        return [os.path.basename(p) for p in self.fila]

    def limpar_fila(self):
        if self.transcrevendo:
            return {"ok": False, "msg": "Não é possível limpar durante a transcrição."}
        self.fila.clear()
        return {"ok": True}

    def iniciar_transcricao(self):
        if not self.fila or self.transcrevendo:
            return {"ok": False}
        self.transcrevendo = True
        threading.Thread(target=self._processar_fila, daemon=True).start()
        return {"ok": True}

    # ── Modelo ────────────────────────────────────────────────────────────

    def precarregar_modelo(self):
        threading.Thread(target=self._carregar_modelo, daemon=True).start()

    def _carregar_modelo(self):
        from faster_whisper import WhisperModel
        with self._model_lock:
            if self.whisper_model is not None:
                return
            try:
                self._js("setStatus", "Carregando modelo…")
                self.whisper_model = WhisperModel(MODELO, device="cpu", compute_type="int8")
                self._js("setStatus", "Pronto.")
                time.sleep(2)
                self._js("setStatus", "")
            except Exception as e:
                self._js("setStatus", f"Erro ao carregar modelo: {e}")

    # ── Utilitários ───────────────────────────────────────────────────────

    def copiar(self, texto):
        if copiar_clipboard(texto):
            return {"ok": True}
        return {"ok": False, "msg": "Não foi possível copiar neste sistema."}

    def salvar(self, texto, nome_sugerido):
        result = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=nome_sugerido,
            file_types=("Texto (*.txt)",),
        )
        if not result:
            return {"ok": False}
        path = result[0] if isinstance(result, (list, tuple)) else result
        return {"ok": _salvar_txt(Path(path), texto)}

    def exportar_srt(self, path):
        """Gera e salva um arquivo .srt para a transcrição especificada."""
        segs = self.segmentos.get(path, [])
        if not segs:
            return {"ok": False, "msg": "Segmentos não disponíveis para exportar SRT."}
        linhas = []
        for i, seg in enumerate(segs, 1):
            start = _fmt_srt_time(seg["start"])
            end   = _fmt_srt_time(seg["end"])
            linhas.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")
        conteudo = "\n".join(linhas)
        nome_base = Path(path).stem
        result = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=f"{nome_base}.srt",
            file_types=("Legendas SRT (*.srt)",),
        )
        if not result:
            return {"ok": False}
        destino = Path(result[0] if isinstance(result, (list, tuple)) else result)
        return {"ok": _salvar_txt(destino, conteudo)}

    def exportar_todos(self):
        """Abre seletor de pasta e salva todas as transcrições da sessão como .txt."""
        if not self.resultados:
            return {"ok": False, "msg": "Nenhuma transcrição para exportar."}

        resultado = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if not resultado:
            return {"ok": False}

        pasta  = Path(resultado[0] if isinstance(resultado, (list, tuple)) else resultado)
        salvos = []
        erros  = []

        for path, texto in self.resultados.items():
            if not texto:
                continue
            base = Path(path).stem
            destino = pasta / f"{base}.txt"
            if destino.exists():
                i = 2
                while (pasta / f"{base} ({i}).txt").exists():
                    i += 1
                destino = pasta / f"{base} ({i}).txt"
            if _salvar_txt(destino, texto):
                salvos.append(destino.name)
            else:
                erros.append(destino.name)

        return {"ok": True, "salvos": salvos, "erros": erros, "pasta": str(pasta)}

    # ── Notificação ───────────────────────────────────────────────────────

    def _notificar(self, total):
        try:
            arq = "arquivo" if total == 1 else "arquivos"
            msg = f"{total} {arq} transcrito{'s' if total > 1 else ''} com sucesso."
            notificar_sistema("Transcrição", msg)
        except Exception:
            pass

    # ── Diarização ────────────────────────────────────────────────────────

    def diarizacao_disponivel(self):
        return SEG_MODEL.exists() and EMB_MODEL.exists()

    def estado_sistema(self):
        """Checado na abertura: falta de ffmpeg tem que aparecer antes de
        estourar no meio de uma gravação."""
        return {
            "ffmpeg": ffmpeg_ok(),
            "diarizacao": self.diarizacao_disponivel(),
            "plataforma": "macOS" if MACOS else ("Windows" if WINDOWS else "Linux"),
        }

    def iniciar_diarizacao(self, path, n_locutores=0):
        if self.diarizando:
            return {"ok": False, "msg": "Já há uma identificação em andamento."}
        if not ffmpeg_ok():
            return {"ok": False, "msg": "ffmpeg não encontrado — veja o README."}
        if not self.segmentos.get(path):
            return {"ok": False, "msg": "Sem segmentos — transcreva o arquivo primeiro."}
        self.diarizando = True
        threading.Thread(target=self._processar_diarizacao,
                         args=(path, int(n_locutores)), daemon=True).start()
        return {"ok": True}

    def _processar_diarizacao(self, path, n_locutores):
        try:
            import numpy as np
            import sherpa_onnx as so

            if not self.diarizacao_disponivel():
                def baixando(rotulo, frac):
                    self._js("setProgress", frac,
                             f"Primeira vez: baixando {rotulo} — {int(frac * 100)}%")
                self._js("setProgress", 0.0, "Primeira vez: baixando modelos (34 MB)…")
                if not garantir_modelos_diarizacao(baixando):
                    raise RuntimeError("falha ao baixar os modelos de diarização")

            self._js("setProgress", 0.0, "Identificando locutores — carregando modelos…")

            clustering = (so.FastClusteringConfig(num_clusters=n_locutores)
                          if n_locutores > 0
                          else so.FastClusteringConfig(num_clusters=-1, threshold=0.5))
            cfg = so.OfflineSpeakerDiarizationConfig(
                segmentation=so.OfflineSpeakerSegmentationModelConfig(
                    pyannote=so.OfflineSpeakerSegmentationPyannoteModelConfig(
                        model=str(SEG_MODEL))),
                embedding=so.SpeakerEmbeddingExtractorConfig(model=str(EMB_MODEL)),
                clustering=clustering,
                min_duration_on=0.3,
                min_duration_off=0.5,
            )
            if not cfg.validate():
                raise RuntimeError("configuração de diarização inválida")

            with self._diar_lock:
                sd = so.OfflineSpeakerDiarization(cfg)

            self._js("setProgress", 0.02, "Identificando locutores — lendo áudio…")
            raw = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", path,
                 "-f", "f32le", "-ac", "1", "-ar", str(sd.sample_rate), "pipe:1"],
                capture_output=True).stdout
            samples = np.frombuffer(raw, dtype=np.float32)
            if samples.size == 0:
                raise RuntimeError("ffmpeg não extraiu áudio deste arquivo")

            nome = os.path.basename(path)

            def progresso(feitos, total):
                if total:
                    pct = feitos / total
                    self._js("setProgress", pct,
                             f"Identificando locutores — {nome} — {int(pct * 100)}%")
                return 0        # não-zero abortaria

            res = sd.process(samples, callback=progresso).sort_by_start_time()
            turnos = [{"start": s.start, "end": s.end, "speaker": s.speaker} for s in res]
            if not turnos:
                raise RuntimeError("nenhum locutor detectado")

            self.locutores[path] = turnos
            rotulados = _rotular_segmentos(self.segmentos[path], turnos)
            self.segmentos[path] = rotulados
            texto = _texto_com_locutores(rotulados, self.nomes_locutores.get(path))
            self.resultados[path] = texto
            for chave in [c for c in self._salvos_sessao if c[1] == path]:
                self._salvos_sessao.discard(chave)

            self._persistir_video(path)      # atualiza o banco com os locutores
            qtd = len({t["speaker"] for t in turnos})
            self._js("setProgress", 1.0, f"{qtd} locutor(es) identificado(s).")
            self._js("onDiarizacao", path, texto, qtd)

        except Exception as e:
            self._js("setStatus", f"Erro na identificação: {str(e).splitlines()[0][:140]}")
            print(traceback.format_exc())
            self._js("onDiarizacao", path, None, 0)
        finally:
            self.diarizando = False

    def renomear_locutor(self, path, indice, nome):
        """Troca L2 por 'Roberto' em todas as falas de uma vez."""
        nome = (nome or "").strip()
        segs = self.segmentos.get(path)
        if not segs or not nome:
            return {"ok": False}
        if not any("speaker" in s for s in segs):
            return {"ok": False, "msg": "Rode a identificação de locutores antes."}
        indice = int(indice)
        nomes  = self.nomes_locutores.setdefault(path, {})
        antigo = nomes.get(indice, f"L{indice + 1}")
        if antigo == nome:
            return {"ok": True, "texto": self.resultados.get(path, "")}

        # Substituição no texto atual, não regeneração a partir dos segmentos:
        # regenerar descartaria qualquer correção que o usuário tenha feito à mão.
        atual = self.resultados.get(path)
        if atual:
            texto = atual.replace(f"] {antigo}: ", f"] {nome}: ")
        else:
            texto = _texto_com_locutores(segs, {**nomes, indice: nome})
        nomes[indice] = nome
        self.resultados[path] = texto
        for chave in [c for c in self._salvos_sessao if c[1] == path]:
            self._salvos_sessao.discard(chave)
        return {"ok": True, "texto": texto}

    def listar_locutores(self, path):
        turnos = self.locutores.get(path) or []
        nomes  = self.nomes_locutores.get(path, {})
        tempo  = {}
        for t in turnos:
            tempo[t["speaker"]] = tempo.get(t["speaker"], 0.0) + (t["end"] - t["start"])
        return [
            {"indice": sp, "nome": nomes.get(sp, f"L{sp + 1}"), "segundos": round(seg)}
            for sp, seg in sorted(tempo.items(), key=lambda x: -x[1])
        ]

    # ── Cortes ────────────────────────────────────────────────────────────

    def cortes_sugeridos(self, path):
        """Candidatos a corte pela heurística. Não grava nada — é proposta."""
        segs = self.segmentos.get(path)
        if not segs:
            return {"ok": False, "msg": "Transcreva o arquivo primeiro.", "cortes": []}
        nomes = self.nomes_locutores.get(path, {})
        cortes = sugerir_cortes(segs)
        for c in cortes:
            sp = c.get("locutor")
            c["rotulo_locutor"] = nomes.get(sp, f"L{sp + 1}") if sp is not None else ""
            c["inicio_hms"] = _fmt_time(c["inicio"])
            c["fim_hms"]    = _fmt_time(c["fim"])
        return {"ok": True, "cortes": cortes}

    def salvar_corte(self, path, inicio, fim, texto="", locutor="", rotulo=""):
        vid = self.video_ids.get(path) or self._persistir_video(path)
        if not vid:
            return {"ok": False, "msg": "Escolha um cliente antes de salvar cortes."}
        cid = banco.salvar_corte(vid, inicio, fim, texto, locutor, rotulo)
        return {"ok": True, "id": cid, "cortes": self.listar_cortes(path)["cortes"]}

    def listar_cortes(self, path):
        vid = self.video_ids.get(path)
        if not vid:
            return {"ok": True, "cortes": []}
        cortes = banco.listar_cortes(vid)
        for c in cortes:
            c["inicio_hms"] = _fmt_time(c["inicio_seg"])
            c["fim_hms"]    = _fmt_time(c["fim_seg"])
            c["duracao"]    = round(c["fim_seg"] - c["inicio_seg"], 1)
        return {"ok": True, "cortes": cortes}

    def remover_corte(self, path, corte_id):
        banco.remover_corte(int(corte_id))
        return {"ok": True, "cortes": self.listar_cortes(path)["cortes"]}

    def copiar_lista_cortes(self, path):
        cortes = self.listar_cortes(path)["cortes"]
        if not cortes:
            return {"ok": False, "msg": "Nenhum corte marcado."}
        linhas = [f"{os.path.basename(path)} — {len(cortes)} corte(s)", ""]
        for i, c in enumerate(cortes, 1):
            rot = f" [{c['rotulo']}]" if c["rotulo"] else ""
            linhas.append(f"{i}. {c['inicio_hms']} → {c['fim_hms']}  ({c['duracao']}s)"
                          f"{rot}{' · ' + c['locutor'] if c['locutor'] else ''}")
            if c["texto"]:
                linhas.append(f"   {c['texto'][:220]}")
            linhas.append("")
        return {"ok": copiar_clipboard("\n".join(linhas))}

    def exportar_videos_cortes(self, path):
        """
        Recorta de verdade, com ffmpeg. Usa cópia de fluxo: é instantâneo
        mesmo em arquivo de 3 horas, ao custo de o corte cair no keyframe
        mais próximo — o que não atrapalha quem vai reeditar no CapCut.
        """
        cortes = self.listar_cortes(path)["cortes"]
        if not cortes:
            return {"ok": False, "msg": "Nenhum corte marcado."}
        if not ffmpeg_ok():
            return {"ok": False, "msg": "ffmpeg não encontrado."}

        origem = Path(path)
        destino = origem.parent / f"{origem.stem} — cortes"
        destino.mkdir(exist_ok=True)

        feitos, erros = [], []
        for i, c in enumerate(cortes, 1):
            rot = "".join(ch for ch in (c["rotulo"] or "") if ch.isalnum() or ch in " -_").strip()
            nome = f"{i:02d} {rot}".strip() + origem.suffix
            saida = destino / nome
            r = subprocess.run(
                ["ffmpeg", "-v", "error", "-y",
                 "-ss", str(c["inicio_seg"]), "-to", str(c["fim_seg"]),
                 "-i", str(origem), "-c", "copy",
                 "-avoid_negative_ts", "make_zero", str(saida)],
                capture_output=True)
            (feitos if r.returncode == 0 and saida.exists() else erros).append(nome)

        if feitos:
            abrir_no_gerenciador(destino)
        return {"ok": bool(feitos), "feitos": len(feitos), "erros": len(erros),
                "pasta": str(destino)}

    # ── Status de publicação ──────────────────────────────────────────────

    def marcar_publicado(self, path, plataforma="", link=""):
        vid = self.video_ids.get(path) or self._persistir_video(path)
        if not vid:
            return {"ok": False, "msg": "Escolha um cliente primeiro."}
        banco.marcar_publicado(vid, plataforma or None, link or None)
        return {"ok": True}

    def painel_cliente(self, projeto=None):
        """Quantos vídeos em cada estágio — a pergunta 'o que já saiu?'."""
        cid = self._cliente_id(projeto)
        if not cid:
            return {"ok": False}
        return {"ok": True, "resumo": banco.resumo_cliente(cid)}

    # ── Transcrição ───────────────────────────────────────────────────────

    def _processar_fila(self):
        try:
            with self._model_lock:
                if self.whisper_model is None:
                    from faster_whisper import WhisperModel
                    self._js("setStatus", "Carregando modelo… (só na primeira vez)")
                    self.whisper_model = WhisperModel(MODELO, device="cpu", compute_type="int8")

            # Snapshot: gravar durante a transcrição adiciona à self.fila, e
            # iterar a lista enquanto ela cresce quebrava a contagem "[4/3]".
            # O que entrar agora fica para a próxima rodada.
            fila_snapshot    = list(self.fila)
            total            = len(fila_snapshot)
            paths_concluidos = []

            for idx, arquivo in enumerate(fila_snapshot, 1):
                nome = os.path.basename(arquivo)
                self._js("setQueueActive", idx - 1)
                # Avisa antes do VAD (pode demorar minutos em vídeos longos)
                self._js("setProgress", 0.0,
                         f"[{idx}/{total}] {nome} — analisando áudio, aguarde…")
                self._js("prepararTranscricao", arquivo, nome)

                duracao = get_duracao(arquivo)
                segments, _ = self.whisper_model.transcribe(
                    arquivo,
                    language="pt",
                    beam_size=1,
                    temperature=0,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                    condition_on_previous_text=False,
                    word_timestamps=False,
                )

                linhas         = []
                segs_data      = []
                ultimo_enviado = 0     # índice das linhas já enviadas ao JS
                last_ui        = 0.0   # timestamp do último update de UI

                for seg in segments:
                    ts   = _fmt_time(seg.start)
                    text = seg.text.strip()
                    linhas.append(f"[{ts}] {text}")
                    segs_data.append({"start": seg.start, "end": seg.end, "text": text})

                    now = time.time()
                    # Rate-limit: atualiza UI no máximo a cada 2 s
                    if now - last_ui >= 2.0:
                        # Envia apenas as linhas novas (não re-envia o texto inteiro)
                        novas = linhas[ultimo_enviado:]
                        if novas:
                            self._js("appendLinhas", arquivo, "\n".join(novas))
                            ultimo_enviado = len(linhas)
                        if duracao:
                            pct = min(seg.end / duracao, 1.0)
                            pct_total = ((idx - 1) + pct) / total
                            self._js("setProgress", pct_total,
                                     f"[{idx}/{total}] {nome} — {int(pct * 100)}%")
                        else:
                            # ffprobe falhou: sem porcentagem, mas mostra que
                            # está andando em vez de congelar em "aguarde…"
                            self._js("setProgress", (idx - 1) / total,
                                     f"[{idx}/{total}] {nome} — {_fmt_time(seg.end)} transcritos")
                        last_ui = now

                # Envia linhas restantes que ainda não foram ao JS
                restantes = linhas[ultimo_enviado:]
                if restantes:
                    self._js("appendLinhas", arquivo, "\n".join(restantes))

                texto = "\n".join(linhas)
                self.resultados[arquivo] = texto.strip()
                self.segmentos[arquivo]  = segs_data
                paths_concluidos.append(arquivo)
                # Registra no banco na hora: o objetivo do produto é nunca
                # mais perder de vista o que foi transcrito de cada cliente.
                self._persistir_video(arquivo)
                self._js("addResult", arquivo, nome, texto.strip())

            # Remove só o que foi processado — preserva o que entrou na fila
            # durante a transcrição (ex.: uma gravação feita no meio).
            for p in paths_concluidos:
                if p in self.fila:
                    self.fila.remove(p)

            self._notificar(total)
            self._js("setProgress", 1.0, f"Concluído — {total} arquivo(s) processado(s).")
            self._js("onComplete", paths_concluidos,
                     [os.path.basename(p) for p in self.fila])

        except Exception as e:
            tb  = traceback.format_exc()
            msg = str(e).split("\n")[0][:140]
            self._js("setStatus", f"Erro: {msg}")
            print(tb)
        finally:
            self.transcrevendo = False
            self._js("setTranscribing", False)


def sugerir_cortes(segs, min_seg=25.0, max_seg=90.0, gap_max=1.5):
    """
    Propõe trechos postáveis a partir dos segmentos da transcrição.

    Heurística, não IA: um corte bom para Reels é alguém falando sem parar
    por 25 a 90 segundos. Então quebra quando o locutor muda, quando há
    silêncio longo, ou quando o trecho ficaria comprido demais.
    Serve como ponto de partida — quem decide é o social media.
    """
    if not segs:
        return []

    blocos, atual = [], []
    for s in segs:
        if atual:
            ant = atual[-1]
            troca   = s.get("speaker") != ant.get("speaker")
            silencio = s["start"] - ant["end"] > gap_max
            longo    = ant["end"] - atual[0]["start"] >= max_seg
            if troca or silencio or longo:
                blocos.append(atual)
                atual = []
        atual.append(s)
    if atual:
        blocos.append(atual)

    cortes = []
    for bloco in blocos:
        pedaco = []
        for s in bloco:
            if pedaco and (s["end"] - pedaco[0]["start"]) > max_seg:
                cortes.append(pedaco)
                pedaco = []
            pedaco.append(s)
        if pedaco:
            cortes.append(pedaco)

    saida = []
    for c in cortes:
        dur = c[-1]["end"] - c[0]["start"]
        if dur < min_seg:
            continue
        saida.append({
            "inicio":  c[0]["start"],
            "fim":     c[-1]["end"],
            "duracao": round(dur, 1),
            "locutor": c[0].get("speaker"),
            "texto":   " ".join(s["text"] for s in c).strip(),
        })
    return saida


def _rotular_segmentos(segs_whisper, turnos):
    """
    Casa cada segmento do Whisper com o locutor que mais se sobrepõe a ele.
    Os dois modelos cortam o áudio em pontos diferentes, então é sobreposição
    de tempo, não igualdade de fronteira.
    """
    rotulados = []
    ultimo = None
    for seg in segs_whisper:
        melhor, melhor_ov = None, 0.0
        for t in turnos:
            ov = min(seg["end"], t["end"]) - max(seg["start"], t["start"])
            if ov > melhor_ov:
                melhor, melhor_ov = t["speaker"], ov
        if melhor is None:
            melhor = ultimo          # silêncio/música: herda o locutor anterior
        else:
            ultimo = melhor
        rotulados.append({**seg, "speaker": melhor})
    return rotulados


def _texto_com_locutores(segs_rotulados, nomes=None):
    nomes = nomes or {}
    linhas = []
    for s in segs_rotulados:
        sp = s.get("speaker")
        rot = nomes.get(sp, f"L{sp + 1}") if sp is not None else "?"
        linhas.append(f"[{_fmt_time(s['start'])}] {rot}: {s['text']}")
    return "\n".join(linhas)


def main():
    api = API()
    ui  = Path(__file__).parent / "ui" / "index.html"
    window = webview.create_window(
        "Transcrição",
        url=str(ui),
        js_api=api,
        width=860,
        height=660,
        min_size=(720, 540),
        background_color="#F7F5F0",     # papel PLTCA_
    )
    api.window = window
    webview.start(debug=False)


if __name__ == "__main__":
    main()
