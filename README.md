# Transcrição PLTCA_

Mesa de produção local para quem cuida de redes sociais de terceiros.
Você joga o vídeo bruto, ele devolve transcrição, quem falou o quê, e os
cortes já recortados em arquivo separado.

Roda inteiro no seu computador: sem nuvem, sem mensalidade, sem limite de minutos.

- Transcrição local com Whisper (`large-v3-turbo`)
- **Link do YouTube** — cola a URL e ele baixa só o áudio direto para a fila
- Identificação de locutor — separa entrevistado, adversário e mediador
- **Sugestão de cortes** de 25 a 90s, com exportação dos vídeos via ffmpeg
- Organização por cliente, com status de publicação por vídeo
- Exporta `.txt` e legenda `.srt`
- macOS, Windows e Linux

---

## Instalar (e atualizar) — uma linha

O mesmo comando serve para as duas coisas: se ainda não existe, clona; se já existe, atualiza.

**macOS e Linux** — cole no Terminal:

```bash
git clone https://github.com/CCavalcante0/pltca-transcricao.git 2>/dev/null || git -C pltca-transcricao pull; cd pltca-transcricao && ./instalar.sh
```

**Windows** — cole no PowerShell:

```powershell
git clone https://github.com/CCavalcante0/pltca-transcricao.git 2>$null; cd pltca-transcricao; git pull; powershell -ExecutionPolicy Bypass -File .\instalar.ps1
```

O instalador acha o Python, resolve o ffmpeg, monta o ambiente e baixa os modelos
de locutor. Rodar de novo é seguro: ele reaproveita o que já está instalado.

Se no Windows ele instalar o ffmpeg, vai pedir para **fechar e reabrir o PowerShell**
e rodar de novo. Só acontece nessa primeira vez.

### Abrir

- **macOS:** clique duas vezes no ícone **Transcrição** na sua Mesa
  (o instalador põe ele lá). Pelo Terminal também vale: `./abrir.sh`
- **Linux:** `./abrir.sh`
- **Windows:** clique duas vezes em `Transcricao.bat`

### Requisitos

Python 3.10+, ffmpeg e ~4 GB livres. O instalador tenta resolver os dois primeiros
sozinho; se não conseguir, diz o que fazer.

---

## A primeira transcrição é lenta — e depois não é mais

Na primeira vez que você mandar transcrever, o app baixa o modelo do Whisper: **1,5 GB**.
A barra fica parada em "Carregando modelo…" durante esse download.

Acontece **uma vez só**. Da segunda em diante ele carrega em uns 4 segundos.

---

## Como usar

### 1. Escolha o cliente

No canto superior esquerdo. Cada cliente é separado: seus vídeos, seu histórico,
o que já foi publicado. **Escolha antes de transcrever** — é o cliente ativo que
determina onde o vídeo vai ser registrado, e cortes só podem ser salvos com um
cliente selecionado.

### 2. Traga o material

Arraste os arquivos para a janela, ou **cole um link do YouTube** no campo da
barra lateral e dê Enter. Ele baixa **só o áudio** — uma entrevista de 75 minutos
dá ~140 MB em vez de vários GB — e o título do vídeo já vira o nome no seu histórico.

Depois clique em **Transcrever**. O texto aparece conforme vai saindo, com o tempo
de cada fala.

### 3. Identifique quem falou — 🗣 Locutores

**Se você sabe quantas pessoas falam no arquivo, escreva o número.** No automático
ele erra para mais, principalmente em material com vinheta e comercial — num debate
de TV chegou a achar 10 locutores onde havia 4.

Depois clique nos nomes e troque `L1` por `Roberto` — ele renomeia em todas as falas
de uma vez, e preserva as correções que você tiver feito no texto à mão.

### 4. Ache os cortes — ✂ Cortes

**Sugerir trechos** procura pedaços de 25 a 90 segundos em que uma pessoa fala sem
parar. É heurística, não IA: serve para você não garimpar três horas na mão. Quem
decide o que presta é você.

Clique num trecho para marcar. Depois:

- **Copiar lista** — os timecodes com o texto, para colar onde quiser
- **Exportar vídeos** — recorta de verdade e abre a pasta com os arquivos prontos

O recorte usa cópia de fluxo: é instantâneo mesmo num arquivo de 3 horas. Em troca,
o corte cai no keyframe mais próximo, o que pode dar alguns quadros de diferença —
irrelevante se você vai reeditar no CapCut.

### 5. Marque o que foi publicado

Cada vídeo tem um estágio: `transcrito` → `legenda_gerada` → `aprovado` → `publicado`.
É isso que responde "esse eu já postei?" sem depender de nome de pasta.

---

## Onde ficam suas coisas

Tudo em `transcricoes.db`, um banco SQLite na pasta do app. Fica **fora do
repositório** — atualizar com `git pull` não encosta nele.

Guarde um backup se o material for importante: é um arquivo só, dá para copiar
para qualquer lugar.

Ao salvar num cliente, o app também deixa um `.txt` ao lado do vídeo original,
por conveniência. Se já existir um `.txt` seu com o mesmo nome, ele **não sobrescreve** —
escreve `nome.transcricao.txt`.

---

## Quanto tempo demora

Medido num **MacBook Air M1 de 8 GB**, a máquina mais fraca em que rodamos:

| tarefa | velocidade | 1 hora de áudio vira |
|---|---|---|
| transcrição | ~3x tempo real | ~20 min |
| identificação de locutor | ~4x tempo real | ~15 min |
| exportar os cortes | instantâneo | segundos |

Máquina melhor faz mais rápido.

---

## Quando der problema

**"ffmpeg não encontrado"** — o instalador não conseguiu sozinho.
macOS: `brew install ffmpeg`. Windows: baixe em [gyan.dev](https://www.gyan.dev/ffmpeg/builds/),
extraia e adicione a pasta `bin` ao PATH.

**"Python não encontrado" no Windows** — você instalou sem marcar *Add Python to PATH*.
Reinstale marcando a caixa.

**Janela abre em branco no Windows** — falta o WebView2. Baixe o *Evergreen Bootstrapper*
em [developer.microsoft.com/microsoft-edge/webview2](https://developer.microsoft.com/microsoft-edge/webview2/).
No Windows 11 já vem.

**"Escolha um cliente antes de salvar cortes"** — nenhum cliente selecionado no canto
superior esquerdo.

**Travou em "analisando áudio, aguarde…"** — normal em arquivo longo. O Whisper analisa
o áudio inteiro antes da primeira linha; num arquivo de 2 horas leva alguns minutos.

**Gravação sem som** — falta permissão de microfone.
macOS: Ajustes do Sistema → Privacidade e Segurança → Microfone.

---

## Para quem for mexer no código

`projetos/`, `gravacoes/` e `*.db` estão no `.gitignore`. São material de cliente e
**não entram em commit nunca**. `venv/` e `modelos/` também ficam de fora — cada
máquina monta os seus.

---

Produto **PLTCA_** · uso interno
