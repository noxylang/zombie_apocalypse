# Arena Shooter Top-Down — Design

Data: 2026-08-31
Projeto: `my_noxy_game`
Engine: `github.com/estevaofon/noxy_game_engine` v0.3.1 sobre Noxy v0.23.2

## 1. O que é

Um arena shooter top-down de ondas. O jogador anda com WASD, mira com o
mouse e atira segurando o botão esquerdo. Inimigos surgem nas bordas de uma
arena maior que a tela e perseguem o jogador. A cada onda vencida o jogador
escolhe um de três upgrades sorteados. Oito ondas; sobreviver a todas é a
vitória, morrer devolve à tela de game over.

Visual vetorial: polígonos e círculos coloridos sobre fundo escuro. Nenhum
asset externo — o jogo roda com `noxy arena.nx` sem baixar nada além da
engine que o projeto já tem.

## 2. Restrições da plataforma

Estas moldaram o design e foram verificadas empiricamente antes de escrevê-lo.

**Não existe módulo `math`.** Sem `sqrt`, `sin`, `cos`, `atan2`. Duas
consequências:

- `sqrt` é implementado por Newton-Raphson em `src/vec.nx`, com semente por
  duplicação (`while g * g < v do g = g * 2.0 end`) seguida de 8 iterações.
  Verificado: `sqrt(2.0)` = 1.414214.
- Nenhuma rotação usa ângulo. A orientação do jogador é o vetor unitário
  `dir` da posição até o mouse; o triângulo é montado com `dir` e sua
  perpendicular `perp(v) = V(-v.y, v.x)`. Os inimigos são desenhados com a
  mesma técnica. `draw_polygon` recebe a lista plana de pontos, então nunca
  precisamos de `draw_image_ex` nem de graus.

**Variáveis de módulo são somente-leitura de fora do módulo.** Por isso o
estado mutável não mora nos módulos: mora num único struct `World`, criado em
`arena.nx` e passado por `ref` para as funções de simulação. Verificado:
`func f(w: ref World)` em outro módulo consegue dar `append` em `w.enemies`
e escrever `w.enemies[i].hp`, e a mutação é visível no chamador.

**Arrays de struct mutam in-place.** `enemies[i].hp = x` funciona, inclusive
através de um `ref`. Então usamos entidades de verdade, não arrays paralelos
como faz `flappy_bird.nx`.

**Não há remoção de elemento de array.** Filtrar é reconstruir: percorrer,
dar `append` num array novo com quem sobrevive, e reatribuir.

**`rand.random()` é inútil.** Ele faz `new_random(ref rng) / rng.m` em
aritmética inteira e retorna sempre 0. Todo aleatório sai de
`rand.random_int(min, max)`; floats vêm de `random_int(0, 10000) / 10000.0`.
`random_int` foi verificado como sempre não-negativo (o estado do LCG cabe
folgado em int64, sem estouro).

**Retorno de função de módulo não infere tipo.** `let v = rand.random_int(0,
9)` é erro de compilação; `let v: int = ...` compila. Vale para `rand.*`,
`game.*` e para os nossos próprios módulos. Toda ligação desse tipo leva
anotação explícita.

**Array literal vazio não infere o tipo do elemento.** `World([], 0)` falha
com `expected Enemy[], got object`. Arrays vazios iniciais são declarados
antes, tipados: `let e: Enemy[] = []`.

## 3. Arquitetura

```
arena.nx           entrada: janela, loop, máquina de telas, input
src/vec.nx         V, sqrt, len, norm, scale, add, sub, perp, dist
src/rng.nx         aleatoriedade: rand_int, rand_float, rand_range
src/world.nx       structs World/Player/Enemy/Bullet/Particle, new_world
src/combat.nx      movimento, tiro, colisão, dano, partículas, tremida
src/waves.nx       tabela de ondas, spawn nas bordas, fim de onda
src/upgrades.nx    catálogo, sorteio de três, aplicação
src/render.nx      desenho do mundo, do HUD e das telas
tests/run.nx       asserts sobre a lógica pura, sem abrir janela
```

A divisão que importa é entre **simulação** (`combat`, `waves`, `upgrades`,
`vec`, `rng`) e **desenho** (`render`). A simulação é aritmética sobre o
`World` e não chama a engine em lugar nenhum, e é exatamente isso que
permite testá-la sem janela. `render` é o único módulo além de `arena.nx`
que dá `use` na engine.

`arena.nx` não contém regra de jogo: lê input, chama uma função de
simulação por tela e uma de desenho, e dá `flip`.

## 4. Dados

```noxy
struct V
    x: float,
    y: float
end

struct Player
    pos: V,
    hp: float,
    hp_max: float,
    speed: float,
    fire_rate: float,      // tiros por segundo
    fire_cd: float,        // segundos até poder atirar de novo
    damage: float,
    bullet_speed: float,
    pierce: int,           // quantos inimigos a bala atravessa além do 1º
    shots: int,            // 1 = simples, 3 = leque
    invuln: float,         // segundos restantes de invencibilidade
    aim: V                 // unitário; guardado para o desenho
end

struct Enemy
    pos: V,
    vel: V,                // perseguição + empurrão da separação
    kind: int,             // 0 chaser, 1 rusher, 2 tank
    hp: float,
    radius: float,
    speed: float,
    touch: float,          // dano de contato
    flash: float           // segundos restantes de flash branco
end

struct Bullet
    pos: V,
    vel: V,
    life: float,
    damage: float,
    hits: int              // inimigos já atravessados
end

struct Particle
    pos: V,
    vel: V,
    life: float,
    life_max: float,
    color: int             // índice na paleta, resolvido no render
end

struct World
    player: Player,
    enemies: Enemy[],
    bullets: Bullet[],
    particles: Particle[],
    wave: int,
    to_spawn: int,         // inimigos da onda ainda não postos em campo
    spawn_cd: float,
    kills: int,
    screen: int,           // 0 jogando, 1 upgrade, 2 game over, 3 vitória
    offers: int[],         // índices dos três upgrades ofertados
    shake: float,          // intensidade restante da tremida
    time: float            // segundos de partida
end
```

`Particle.color` é um índice, não uma `game.Color`, para que `world.nx` não
precise dar `use` na engine — a paleta vive em `render.nx`.

## 5. Regras

**Arena e câmera.** Mundo de 1600×1200, janela de 960×640. A câmera centra
no jogador e é travada nas bordas, de modo que nunca se vê fora da arena. A
tremida soma um deslocamento aleatório decrescente ao `camera_set`. O mouse
em coordenadas de mundo é `mouse_pos()` mais o deslocamento da câmera.

**Jogador.** Raio 12, 100 de vida, 220 px/s. O movimento diagonal é
normalizado para não ser mais rápido que o reto. Colide com as paredes da
arena por travamento de coordenada.

**Tiro.** Segurar o botão esquerdo atira à cadência `fire_rate` (base 5/s).
A bala nasce na ponta do triângulo, viaja a `bullet_speed` (base 600 px/s),
vive 1.2 s, causa `damage` (base 10) e some ao acertar, salvo se `pierce`
permitir atravessar. Com `shots = 3` saem três balas em leque de ±12° —
obtido girando `dir` por uma matriz de rotação com seno e cosseno
constantes pré-computados, não por trigonometria em runtime.

**Inimigos.** Todos perseguem em linha reta o jogador; a dificuldade vem do
número e da mistura.

| Tipo   | Forma            | Vel | HP | Raio | Contato |
|--------|------------------|-----|----|------|---------|
| Chaser | losango vermelho | 90  | 20 | 14   | 10      |
| Rusher | triângulo laranja| 170 | 10 | 11   | 8       |
| Tank   | quadrado roxo    | 55  | 60 | 20   | 20      |

Contato aplica dano e empurra o jogador para trás; há 0.6 s de invencibilidade
depois de cada acerto para não drenar a vida em um quadro. Inimigos se
separam suavemente uns dos outros para não empilharem — varredura O(n²)
sobre menos de 60 inimigos.

**Ondas.** Oito. A onda `n` tem `4 + 3 * n` inimigos, liberados aos poucos
(um a cada 0.35 s) pelas bordas da arena, fora do campo de visão. A mistura
muda com a onda: só chasers no começo, rushers a partir da 2ª, tanks a
partir da 4ª, com a proporção de chasers caindo conforme avança. Quando
`to_spawn` chega a zero e o array de inimigos esvazia, a onda acabou.

**Upgrades.** Ao fim de cada onda (menos a última) a tela vai para o modo
upgrade e três dos seis são sorteados sem repetição. Escolhe-se com 1, 2 ou 3.

| Upgrade      | Efeito                                  |
|--------------|-----------------------------------------|
| Cadência     | `fire_rate * 1.35`                      |
| Dano         | `damage + 6`                            |
| Botas        | `speed * 1.15`                          |
| Blindagem    | `hp_max + 30` e cura 30                 |
| Leque triplo | `shots = 3` (se já tem, vira dano)      |
| Perfuração   | `pierce + 1`                            |

O único upgrade com teto é o leque triplo: pego uma segunda vez ele aplica
`damage + 6` no lugar, para que nenhuma escolha seja desperdiçada. Os outros
cinco empilham sem limite e por isso não precisam de substituto.

**Fim.** Vida ≤ 0 → tela de game over com onda alcançada, abates e tempo; R
reinicia. Vencer a oitava onda → tela de vitória com as mesmas estatísticas;
R reinicia. Escape sai em qualquer tela.

## 6. Sensação

Sem áudio nesta versão — o projeto não tem arquivos de som, e a engine já
oferece `load_sound`/`play` para acrescentar depois sem mexer na estrutura.
O retorno é todo visual:

- **Estilhaços.** A morte de um inimigo gera 8 partículas na cor dele, com
  velocidade radial aleatória e vida de 0.5 s, desaparecendo por alfa.
- **Flash.** Um inimigo atingido fica branco por 0.06 s (`Enemy.flash`).
- **Tremida.** Dano no jogador seta `shake`, que decai e sacode a câmera.
- **Rastro de bala.** A bala é um traço de `pos` a `pos - vel * 0.02`, o que
  a faz parecer veloz sem custo nenhum.
- **Grade de fundo.** Linhas a cada 80 px em azul bem escuro, para que o
  movimento da câmera seja perceptível numa arena vazia.

## 7. Testes

`tests/run.nx` roda com `noxy tests/run.nx`, sem abrir janela, e imprime uma
linha por caso mais um resumo; sai com contagem de falhas. É possível
justamente porque a simulação não toca na engine.

Casos:

- `vec`: `sqrt` de 0, 1, 2, 1e6 dentro de tolerância; `norm` de (3,4) é
  (0.6,0.8); `norm` do vetor zero não divide por zero; `perp` é ortogonal.
- `rng`: `rand_int(lo,hi)` fica no intervalo em 1000 sorteios; `rand_float`
  fica em [0,1).
- `combat`: uma bala sobre um inimigo tira `damage` do hp e a bala some;
  com `pierce = 1` ela sobrevive ao primeiro acerto e morre no segundo; um
  inimigo com hp ≤ 0 sai do array e deixa 8 partículas; contato com o
  jogador tira vida e respeita a invencibilidade; a bala expira ao fim da
  vida útil.
- `waves`: a onda `n` declara `4 + 3n` inimigos; os spawns caem dentro da
  arena; a onda só termina com `to_spawn` zerado e sem inimigos vivos.
- `upgrades`: o sorteio devolve três índices distintos; cada upgrade altera
  exatamente os campos que promete (blindagem mexe em `hp` e `hp_max`, os
  demais num campo só) e deixa os outros intactos; o leque pego duas vezes
  aumenta o dano em vez de não fazer nada.

A implementação segue TDD: cada função de simulação ganha seu caso antes do
corpo.

## 8. Desempenho

Um quadro cheio (60 inimigos, 40 balas, 100 partículas, grade e HUD) fica em
torno de 250 comandos de desenho, que viajam num único `flip` — bem abaixo
do milissegundo de transporte que o README da engine descreve. A separação
O(n²) entre inimigos são menos de 1800 comparações por quadro. Nenhum I/O em
runtime, portanto nenhum caminho de erro a tratar além dos que a própria
engine levanta.

## 9. Fora de escopo

Chefes, armas alternativas, salvamento de recorde em disco, menu inicial,
suporte a gamepad, áudio. Cada um cabe na estrutura depois; nenhum é
necessário para o jogo ser um jogo.
