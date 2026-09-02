# Noxy Arena

Um arena shooter top-down de oito ondas, escrito em [Noxy](https://github.com/estevaofon/noxy)
sobre o [noxy_game_engine](https://github.com/estevaofon/noxy_game_engine).

O chão é um mapa desenhado (veja "Mapa e colisão"); jogador e inimigos são
sprites animados (veja "Sprites"); balas, partículas e HUD são linhas,
círculos e retângulos.

## Jogar

    noxy arena.nx

A partir da raiz do projeto — os módulos são resolvidos a partir do diretório
de trabalho, não do arquivo.

## Controles

| Tecla | Ação |
|---|---|
| W A S D | mover |
| Mouse | mirar |
| Botão esquerdo (segurar) | atirar |
| 1 / 2 / 3 | escolher o upgrade entre ondas |
| R | recomeçar depois do fim |
| F1 | mostrar os retângulos de colisão |
| Escape | sair |

## O jogo

Oito ondas num pátio industrial de 2816×1536, com a câmera seguindo o
jogador. A onda `n` traz `4 + 3n` inimigos, que entram pelas bordas:

| Inimigo | Sprite | Velocidade | Vida | Contato |
|---|---|---|---|---|
| Chaser | zumbi de braços estendidos | 90 | 20 | 10 |
| Rusher | soldado mascarado correndo | 170 | 10 | 8 |
| Tank | zumbi soldado, maior | 55 | 60 | 20 |

Chasers vêm sozinhos na onda 1, rushers entram na 2, tanks na 4. Ao limpar
uma onda você escolhe um de três upgrades sorteados entre cadência, dano,
velocidade, blindagem, leque triplo e perfuração. Sobreviver às oito é a
vitória.

## Como está organizado

A simulação — `src/vec`, `src/rng`, `src/world`, `src/level`, `src/combat`,
`src/waves`, `src/upgrades`, `src/flow` — é aritmética pura sobre um struct
`World` e não conhece a engine. `src/anim` lê o `World` e escolhe o frame do jogador (linha,
coluna e espelhamento), também sem engine. `src/render` é o único módulo que
desenha, e `arena.nx` só traduz teclado e mouse em vetores e entrega para
`flow.advance`.

Essa separação é o que permite testar o jogo inteiro sem abrir janela:

    noxy tests/run.nx        # 240 asserts sobre a simulação, o mapa e a animação, sem janela
    noxy tests/smoke.nx      # abre a janela, percorre as 4 telas, sai sozinho

`run.nx` cobre a lógica; `smoke.nx` existe porque erro de comando de desenho
só aparece quando há uma janela para recusá-lo.

## Mapa e colisão

`images/background.jpg` é o mapa, gerado no Gemini, desenhado em escala 1:1:
a arena tem exatamente o tamanho da imagem. Noxy não lê pixels, então os
obstáculos são dados: `src/level.nx` lista retângulos (x, y, largura, altura)
traçados à mão sobre a imagem — galpões, prédios, vagões, contêineres,
veículos, muros e silos. Cercas, portões e a tubulação elevada ficam
passáveis de propósito: os inimigos perseguem em linha reta e só deslizam em
parede, e um pátio cercado com um portão viraria uma armadilha onde eles
encalham. Miudezas como caixotes, barris e pneus também ficam de fora.

Jogador e inimigos são empurrados para fora dos retângulos depois de andar
(`level.push_out`), o que dá o deslize ao longo das paredes; balas morrem ao
entrar num retângulo; o spawn na borda re-sorteia até cair em ponto livre.
`World.obstacles` começa vazio — `arena.nx` instala `level.OBSTACLES`, e os
testes usam retângulos próprios. O ponto de partida é `world.START`.

Aperte F1 no jogo para ver os retângulos sobre o mapa. Para ajustar um, mude
os números em `src/level.nx`; o teste `test_map` confere que todos cabem na
arena e que a partida fica livre.

## Sprites

`images/shooter.png` e `images/enemies.png` são as sheets originais, geradas
no Gemini. Elas não vêm numa grade regular — frames de larguras diferentes,
o flash do cano invadindo a célula vizinha, fumacinhas soltas e várias linhas
misturando vista frontal e lateral — então o jogo não as usa direto.
`tools/pack_sheet.py` (Python com Pillow) recorta só as linhas coerentes e
escreve `images/shooter_sheet.png` e `images/enemies_sheet.png`, uma animação
por linha em células de 80×64 com o corpo sempre no centro.

Jogador (`shooter_sheet.png`):

| Linha | Animação | Frames |
|---|---|---|
| 0 | parado, de frente | 4 |
| 1 | andando para baixo | 6 |
| 2 | andando para cima | 7 |
| 3 | andando de lado | 4 |
| 4 | atirando de lado | 7 |
| 5 | morte | 7 |
| 6 | parado, de lado | 1 |

Toda linha de lado fica virada para a direita. As caminhadas laterais da
sheet original misturam tronco de costas e de frente em 3/4, e alternar entre
eles a 10 fps parecia o soldado girando a cada ciclo; por isso o andar de lado
usa só os três frames de vista lateral limpa da sheet (um repetido para fechar
o ciclo passo largo, pernas juntas), e o parado de lado é um frame à parte,
espelhado da caminhada que olha para a esquerda.

Parado ou atirando, o sprite olha para a mira; andando sem atirar, olha para
onde anda (seguir a mira faria o jogador virar para trás ao passar pelo
cursor, o que acontece fácil onde a câmera trava nas bordas). A direção é
quantizada em quatro; para a esquerda o render espelha as linhas de lado. Não
há linha de tiro para cima ou para baixo, então ali o tiro usa o andar ou o
idle.

Inimigos (`enemies_sheet.png`), uma caminhada lateral por tipo, na ordem do
`kind`: zumbi comum, soldado mascarado, zumbi soldado. Inimigo só olha para a
esquerda ou para a direita, pelo sinal da velocidade; a passada anda a
`speed / 10` frames por segundo, com uma fase própria por inimigo derivada da
posição de spawn, para a horda não marchar em sincronia. Enquanto o `flash` de
acerto dura, o sprite some. A escala de desenho varia por tipo (rusher menor,
tank maior); os raios de colisão continuam em `combat.make_enemy`.

Ao regenerar uma sheet no Gemini, ajuste `PLAYER` ou `ENEMIES` no script se a
posição das linhas mudar, rode-o a partir da raiz e confira `FRAMES` e
`ENEMY_FRAMES` em `src/anim.nx`.

## Nota de implementação

Noxy não tem módulo `math` — nem `sqrt`, nem `sin`, `cos` ou `atan2`. Duas
consequências moldaram o código:

- `src/vec.nx` traz um `sqrt` por Newton-Raphson, com a semente dobrando até
  passar do valor para manter poucas iterações.
- Nenhuma rotação usa ângulo. Direção é sempre vetor unitário, e as formas se
  montam a partir dela e da sua perpendicular `perp(v) = V(-v.y, v.x)`. O
  leque de tiros gira por uma matriz com seno e cosseno pré-computados.

Outras armadilhas da linguagem, para quem for mexer: retorno de função de
módulo não infere tipo (`let v: int = rand.random_int(...)`), array literal
vazio não infere o elemento, variáveis de módulo são somente-leitura de fora,
e não há remoção de elemento de array — filtrar é reconstruir.

O desenho e o design completos estão em `docs/superpowers/`.
