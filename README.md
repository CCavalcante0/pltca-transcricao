# Transcrição PLTCA_

Transcreve vídeo e áudio no seu próprio computador e identifica quem falou o quê.
Nada sai da máquina: não há servidor, não há mensalidade, não há limite de minutos.

- Transcrição local com Whisper (`large-v3-turbo`)
- Identificação de locutor — separa quem é quem numa entrevista ou debate
- Fila de arquivos, organização por projeto e gravação direto do microfone
- Exporta `.txt` e legenda `.srt`
- Roda em **macOS, Windows e Linux**

---

## Instalação

Você faz isso **uma vez por computador**. Leva de 5 a 15 minutos, quase tudo é download.

### O que precisa ter antes

- **Python 3.10 ou mais novo**
- **ffmpeg**
- **~4 GB de espaço livre** (modelos + dependências)

O instalador tenta resolver os dois primeiros sozinho. Se não conseguir, ele diz exatamente o que fazer.

### macOS

Abra o **Terminal** e cole, uma linha de cada vez:

```bash
git clone https://github.com/CCavalcante0/pltca-transcricao.git
```

```bash
cd pltca-transcricao && chmod +x instalar.sh abrir.sh && ./instalar.sh
```

Para abrir o app depois:

```bash
./abrir.sh
```

### Windows

Abra o **PowerShell** e cole, uma linha de cada vez:

```powershell
git clone https://github.com/CCavalcante0/pltca-transcricao.git
```

```powershell
cd pltca-transcricao; powershell -ExecutionPolicy Bypass -File .\instalar.ps1
```

Se ele instalar o ffmpeg, vai pedir para **fechar e reabrir o PowerShell** e rodar de novo. É normal, e só acontece nessa primeira vez.

Para abrir o app depois: clique duas vezes em **`Transcricao.bat`**.

### Linux

```bash
git clone https://github.com/CCavalcante0/pltca-transcricao.git
```

```bash
cd pltca-transcricao && chmod +x instalar.sh abrir.sh && ./instalar.sh
```

---

## A primeira transcrição é lenta — e depois não é mais

Na primeira vez que você mandar transcrever, o app baixa o modelo do Whisper: **1,5 GB**. A barra fica parada em "Carregando modelo…" durante esse download.

Isso acontece **uma vez só**. Da segunda transcrição em diante ele carrega em uns 4 segundos.

---

## Como usar

1. **Arraste** os vídeos ou áudios para a janela (ou clique em *Adicionar arquivos*)
2. Clique em **Transcrever**
3. O texto aparece conforme vai transcrevendo, com o tempo de cada fala

Para saber **quem falou**, clique em **🗣 Locutores**. Se você souber quantas pessoas falam no arquivo, escreva o número — o resultado fica bem melhor do que deixar no automático. Depois é só clicar no nome de cada locutor e trocar `L1` por `Roberto`, que ele renomeia em todas as falas de uma vez.

Para guardar, escolha um **projeto** no canto superior esquerdo antes de salvar. Cada projeto é uma pasta, e o app ainda deixa uma cópia do `.txt` ao lado do vídeo original.

---

## Quanto tempo demora

Medido num **MacBook Air M1 de 8 GB**, que é a máquina mais fraca em que rodamos:

| tarefa | velocidade | 1 hora de áudio vira |
|---|---|---|
| transcrição | ~3x tempo real | ~20 min |
| identificação de locutor | ~4x tempo real | ~15 min |

Máquina melhor faz mais rápido. Máquina com placa de vídeo NVIDIA vai ficar bem mais rápida quando a detecção automática de hardware entrar.

---

## Quando der problema

**"ffmpeg não encontrado"** — o instalador não conseguiu instalar sozinho.
No macOS: `brew install ffmpeg`. No Windows: baixe em [gyan.dev](https://www.gyan.dev/ffmpeg/builds/), extraia e adicione a pasta `bin` ao PATH.

**"Python não encontrado" no Windows** — você instalou o Python sem marcar *Add Python to PATH*. Reinstale marcando essa caixa.

**A janela abre em branco (Windows)** — falta o WebView2. Baixe o *Evergreen Bootstrapper* em [developer.microsoft.com/microsoft-edge/webview2](https://developer.microsoft.com/microsoft-edge/webview2/). No Windows 11 já vem instalado.

**Travou em "analisando áudio, aguarde…"** — normal em arquivo longo. O Whisper analisa o áudio inteiro antes de soltar a primeira linha; num arquivo de 2 horas isso leva alguns minutos.

**Gravação sem som** — o app precisa de permissão de microfone.
No macOS: Ajustes do Sistema → Privacidade e Segurança → Microfone.

---

## Atualizando

```bash
git pull
```

Se o `requirements.txt` tiver mudado, rode o instalador de novo — ele reaproveita o que já está instalado.

---

## O que não vai para o repositório

`projetos/` e `gravacoes/` estão no `.gitignore`. São material de cliente e **não devem ser commitados nunca**. O mesmo vale para `venv/` e `modelos/`, que cada máquina monta sozinha.

---

Produto **PLTCA_** · uso interno
