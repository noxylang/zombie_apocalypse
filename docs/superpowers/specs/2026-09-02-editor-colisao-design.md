# Editor de colisão — Design

Data: 2026-09-02
Projeto: Deadrail (`my_noxy_game`)
Engine: `github.com/estevaofon/noxy_game_engine` v0.3.1 sobre Noxy v0.23.0 (Windows, onde a janela abre) e v0.23.2 (WSL, testes)

## 1. O que é

Uma ferramenta para traçar os retângulos de colisão sobre o mapa com o
mouse: arrastar para criar, arrastar o corpo para mover, arrastar as alças
para redimensionar, apagar, duplicar, desfazer e salvar. O que ela salva é
o que o jogo carrega — não existe mais um literal de retângulos no código.

Motivação: os retângulos de `src/level.nx` foram traçados à mão e muitos não
batem com o desenho; ajustar números e reabrir o jogo é lento demais.

## 2. Decisões

**O editor vive dentro do jogo**, num segundo ponto de entrada,
`editor.nx`, sobre a mesma engine, o mesmo `images/background.jpg` em
1:1 e a mesma câmera. Não há Python nem navegador: o que se vê no editor é
exatamente o que o jogo desenha, com o mesmo raio do jogador. Descartado:
uma página HTML (precisa exportar/colar; escala e câmera divergem do jogo)
e um script Pillow/tkinter (mais uma toolchain para um problema que a
engine já resolve).

**Os obstáculos viram dados em `data/obstacles.txt`**, um retângulo por
linha, `x y w h` em pixels inteiros do mapa, linhas em branco e `#`
ignoradas. O editor lê e escreve esse arquivo; `deadrail.nx` e
`tests/smoke.nx` o carregam com `level.load`. Sem literal em código,
há uma única fonte de verdade e nada para o editor gerar como fonte.
Comentários do arquivo não sobrevivem a um salvamento — o editor escreve
só um cabeçalho.

**Lógica do editor sem engine**, em `src/editor.nx`: seleção, alças,
arrastar, criar, apagar, duplicar, empurrar, desfazer, limite da arena e a
flag de "não salvo" operam sobre um struct `Editor` passado por `ref`, e
por isso entram em `tests/run.nx` como o resto da simulação. `editor.nx`
só traduz mouse e teclado em chamadas a esse módulo, e `src/render.nx`
ganha `editor_frame` — continua sendo o único módulo que desenha.

**Sem zoom.** A engine não escala retângulos pela câmera; um zoom obrigaria
a transformar cada coordenada à mão. A arena tem três telas de largura e
duas e meia de altura: WASD e o botão direito percorrem isso rápido.

## 3. Interação

| Entrada | Ação |
|---|---|
| Arrastar em área vazia | cria um retângulo (arrastes menores que 4 px são descartados) |
| Clique num retângulo | seleciona (o menor que contém o ponto, para alcançar os aninhados) |
| Arrastar o corpo do selecionado | move |
| Arrastar uma alça (4 cantos + 4 lados) | redimensiona; passar do lado oposto inverte, nunca fica negativo |
| Setas | empurram o selecionado 1 px (Shift: 10 px); sem seleção, movem a câmera |
| Delete / Backspace | apaga o selecionado |
| Ctrl+D | duplica o selecionado, deslocado 16 px |
| Ctrl+Z | desfaz (pilha de até 100 estados) |
| Ctrl+S | salva em `data/obstacles.txt` |
| W A S D / botão direito arrastando | câmera (Shift acelera) |
| Escape | sai; com alteração não salva, avisa e pede um segundo Escape |

Todo retângulo fica com coordenadas inteiras e dentro da arena
(`world.ARENA_W` × `world.ARENA_H`); o ponto de partida `world.START` é
desenhado com o raio do jogador para não ser coberto.

## 4. Componentes

| Arquivo | Responsabilidade |
|---|---|
| `data/obstacles.txt` | Os retângulos. Gerado uma vez a partir do literal antigo (comentários viraram `#`). |
| `src/level.nx` | Geometria (como antes) + `PATH`, `parse`, `format`, `load`, `save`. Sem `OBSTACLES`. |
| `src/editor.nx` | Struct `Editor` e a máquina de estados do mouse; sem engine. |
| `src/render.nx` | `clamp_camera` (extraído de `camera_base`) e `editor_frame`. |
| `editor.nx` | Janela, input, câmera, aviso de saída, mensagem de status. |
| `deadrail.nx`, `tests/smoke.nx` | Carregam o mapa com `level.load`; o smoke também desenha quadros do editor. |
| `tests/run.nx` | `test_level_file` (parse/format, arquivo real cabe na arena, partida livre) e `test_editor`. |
| `README.md` | Seção "Mapa e colisão" descreve o arquivo e o editor. |

## 5. Erros

`level.load` devolve `Loaded{rects, ok, error}`: arquivo ausente ou linha
malformada dão `ok=false` com a linha no erro, e `deadrail.nx`/`editor.nx`
imprimem e saem com código 1 — carregar um mapa pela metade e salvá-lo em
cima seria perder retângulos. `level.save` devolve `bool`; o editor mostra
"não consegui salvar" em vez de marcar como salvo.

## 6. Testes

`tests/run.nx` sem janela: parse aceita espaços extras, comentários e
linhas vazias; rejeita linha com três números ou texto; `format` e `parse`
fazem ida e volta; o arquivo real tem retângulos, todos cabem na arena e a
partida fica livre. Editor: pick escolhe o menor; alças nos oito pontos;
criar por arraste e descartar arraste pequeno; mover; redimensionar com
inversão; limite da arena; apagar; duplicar; empurrar; desfazer; dirty.
`tests/smoke.nx` desenha 20 quadros de `editor_frame`. Teste manual no
Windows: `noxy editor.nx`, ajustar um retângulo, Ctrl+S, abrir o jogo e
conferir com F1.
