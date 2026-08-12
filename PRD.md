# PRD — Ferramenta de Transcrição & Conteúdo

## O que é

Uma ferramenta local que transforma vídeos em conteúdo pronto para redes sociais.
Roda 100% no Mac, sem depender de serviços pagos de transcrição.

---

## ✅ App base — concluído

- [x] Transcrição local com faster-whisper (modelo medium)
- [x] Interface visual estilo macOS (CustomTkinter)
- [x] Barra de progresso em tempo real por segmento
- [x] Texto aparecendo conforme transcreve
- [x] Fila de arquivos — vários vídeos em sequência
- [x] Painel de resultados por vídeo — coluna lateral com seleção individual
- [x] Copiar transcrição de vídeo específico com um clique
- [x] Salvar .txt com nome do vídeo sugerido automaticamente
- [x] Thread safety — zero risco de crash na UI
- [x] Algoritmo otimizado: beam_size=1, vad_filter, sem alucinação
- [x] Notificação sonora ao concluir
- [x] Limpar fila com feedback correto durante transcrição

---

## Próximo passo — Módulo de conteúdo (assessorados)

### Problema
Produzir conteúdo para o feed de um assessorado exige:
1. Transcrever o vídeo ← **já resolvido**
2. Criar headline de capa (frase curta e impactante) ← **próximo**
3. Escrever a legenda do post ← **próximo**

### Solução
Após a transcrição, acionar a Claude API para entregar:

```
Vídeo
  └─→ Transcrição (Whisper local) ✅
        └─→ Claude API
              ├─→ 3 opções de headline de capa
              └─→ Legenda pronta para Instagram
```

Tudo salvo em banco SQLite local com histórico por vídeo e por assessorado.

### O que precisa pra começar
- Chave da API do Claude (Anthropic) — **pendente com o Davi**

---

## Multi-cliente

Cada assessorado é um "projeto" separado com:
- Seu próprio banco de exemplos de estilo
- Histórico de vídeos processados
- Configurações de tom e formato de legenda

---

## Aprendizado de estilo (few-shot prompting)

Não é machine learning — não treina nenhum modelo.

**Como funciona:**
1. Você roda a transcrição de um vídeo do Francisco
2. Gera as sugestões de headline e legenda
3. Aprova ou edita o resultado final
4. O app salva o par: `transcrição → headline aprovada + legenda aprovada`
5. Na próxima geração, esses exemplos vão junto no prompt para o Claude
6. O Claude replica o estilo automaticamente

Quanto mais exemplos salvos, mais afinado fica o resultado.

### Banco de exemplos (por assessorado)
| campo          | descrição                         |
|----------------|-----------------------------------|
| transcricao    | texto do vídeo                    |
| headline_final | headline aprovada para a capa     |
| legenda_final  | legenda aprovada para o Instagram |
| data           | data de aprovação                 |

---

## Clipping automático

Para vídeos com mais de 3 minutos:
- Identificar trechos mais relevantes pelos segmentos da transcrição
- Sugerir cortes para Reels (30s–90s)
- Destacar frases mais impactantes com timestamp

Usa os timestamps que o faster-whisper já retorna — sem libs extras de IA.

---

## Banco de dados (SQLite)

**Tabela `assessorados`**
| campo  | descrição                |
|--------|--------------------------|
| id     | chave primária           |
| nome   | nome do assessorado      |
| estilo | notas sobre o tom/estilo |

**Tabela `videos`**
| campo          | descrição                             |
|----------------|---------------------------------------|
| id             | chave primária                        |
| assessorado_id | vínculo com o assessorado             |
| nome_arquivo   | nome original do vídeo                |
| data           | data de processamento                 |
| transcricao    | texto completo                        |
| headlines      | JSON com as 3 opções geradas          |
| headline_final | headline aprovada (alimenta o estilo) |
| legenda_post   | legenda do Instagram gerada           |
| legenda_final  | legenda aprovada (alimenta o estilo)  |
| clipes         | JSON com sugestões de corte           |

---

## Referências de estilo

Padrão típico das capas que funcionam:
- 3 a 6 palavras, diretas e impactantes
- Verbo de ação ou número concreto quando possível
- Tom: autoridade + resultado + pertencimento à categoria

Os exemplos reais de cada cliente ficam no banco local, na tabela
`legendas` com `aprovada = 1`. Não entram no repositório.

---

## Frontend — decisão

Migrar de CustomTkinter para **pywebview** após o módulo de conteúdo estar estável.

- Fonte SF Pro (nativa do macOS/iOS)
- Cor de destaque `#007AFF` (azul iOS)
- Blur de vidro fosco (backdrop-filter)
- Cantos arredondados generosos (16–20px)
- Animações suaves de transição

---

## Dependências

| dependência    | uso                              | status     |
|----------------|----------------------------------|------------|
| faster-whisper | transcrição local                | instalado  |
| customtkinter  | interface atual (será migrada)   | instalado  |
| pywebview      | nova interface visual estilo iOS | pendente   |
| anthropic SDK  | gerar headlines e legendas       | pendente   |
| sqlite3        | banco local (já vem no Python)   | disponível |
