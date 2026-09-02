# Noxy Arena

Um arena shooter top-down de oito ondas, escrito em [Noxy](https://github.com/estevaofon/noxy)
sobre o [noxy_game_engine](https://github.com/estevaofon/noxy_game_engine).

Inimigos, balas e cenário são polígonos, círculos e linhas; o jogador é um
sprite animado (veja "Sprite do jogador").

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
| Escape | sair |

## O jogo

Oito ondas numa arena de 1600×1200, com a câmera seguindo o jogador. A onda
`n` traz `4 + 3n` inimigos, que entram pelas bordas:

| Inimigo | Forma | Velocidade | Vida | Contato |
|---|---|---|---|---|
| Chaser | losango vermelho | 90 | 20 | 10 |
| Rusher | triângulo laranja | 170 | 10 | 8 |
| Tank | quadrado roxo | 55 | 60 | 20 |

Chasers vêm sozinhos na onda 1, rushers entram na 2, tanks na 4. Ao limpar
uma onda você escolhe um de três upgrades sorteados entre cadência, dano,
velocidade, blindagem, leque triplo e perfuração. Sobreviver às oito é a
vitória.

## Como está organizado

A simulação — `src/vec`, `src/rng`, `src/world`, `src/combat`, `src/waves`,
`src/upgrades`, `src/flow` — é aritmética pura sobre um struct `World` e não
conhece a engine. `src/anim` lê o `World` e escolhe o frame do jogador (linha,
coluna e espelhamento), também sem engine. `src/render` é o único módulo que
desenha, e `arena.nx` só traduz teclado e mouse em vetores e entrega para
`flow.advance`.

Essa separação é o que permite testar o jogo inteiro sem abrir janela:

    noxy tests/run.nx        # 196 asserts sobre a simulação e a animação, sem janela
    noxy tests/smoke.nx      # abre a janela, percorre as 4 telas, sai sozinho

`run.nx` cobre a lógica; `smoke.nx` existe porque erro de comando de desenho
só aparece quando há uma janela para recusá-lo.

## Sprite do jogador

`images/shooter.png` é a sheet original, gerada no Gemini. Ela não vem numa
grade regular — frames de larguras diferentes, o flash do cano invadindo a
célula vizinha e várias linhas misturando vista frontal e lateral — então o
jogo não a usa direto. `tools/pack_sheet.py` (Python com Pillow) recorta as
seis linhas coerentes e escreve `images/shooter_sheet.png`, uma animação por
linha em células de 80×64 com o corpo sempre no centro:

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
espelhado da caminhada que olha para a esquerda. Parado ou atirando, o sprite olha para a mira; andando sem atirar, olha
para onde anda (seguir a mira faria o jogador virar para trás ao passar pelo
cursor, o que acontece fácil onde a câmera trava nas bordas). A direção é
quantizada em quatro; para a esquerda o render espelha as linhas de lado. Não há linha de tiro para cima ou para
baixo, então ali o tiro usa o andar ou o idle. Ao regenerar a sheet no Gemini,
ajuste `ANIMATIONS` no script se a posição das linhas mudar, rode-o a partir
da raiz e confira `FRAMES` em `src/anim.nx`.

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
