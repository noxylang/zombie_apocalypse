# Arena Shooter Top-Down — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um arena shooter top-down de oito ondas, com upgrades entre ondas, escrito em Noxy sobre o `noxy_game_engine`, rodando com `noxy arena.nx`.

**Architecture:** A simulação (`vec`, `rng`, `world`, `combat`, `waves`, `upgrades`) é aritmética pura sobre um único struct `World` passado por `ref`, e não toca na engine — é isso que a torna testável sem abrir janela. `render` é o único módulo que desenha. `arena.nx` só lê input, escolhe a função de simulação pela tela atual, desenha e dá `flip`.

**Tech Stack:** Noxy v0.23.2, `github.com/estevaofon/noxy_game_engine` v0.3.1 (Ebitengine). Nenhuma dependência nova, nenhum asset externo.

**Spec:** `docs/superpowers/specs/2026-08-31-arena-shooter-design.md`

## Global Constraints

Estas valem para **toda** tarefa. Foram verificadas empiricamente; violá-las dá erro de compilação ou bug silencioso.

- **Não existe módulo `math`.** Sem `sqrt`, `sin`, `cos`, `atan2`. Use `vec.sqrt` (Task 1). Nenhuma rotação por ângulo: direção é vetor unitário, e a perpendicular é `perp(v) = V(-v.y, v.x)`.
- **Retorno de função de módulo não infere tipo.** `let v = rand.random_int(0, 9)` é erro de compilação. Sempre `let v: int = ...`. Vale para `rand.*`, `game.*` e para os módulos deste projeto. Dentro do mesmo módulo a inferência funciona, mas anote mesmo assim — é o padrão do projeto.
- **Array literal vazio não infere o elemento.** `World([], 0)` falha com `expected Enemy[], got object`. Declare antes, tipado: `let es: Enemy[] = []`.
- **Variáveis de módulo são somente-leitura de fora.** `wld.ARENA_W` lê; `wld.ARENA_W = 10.0` é erro de compilação. Todo estado mutável vive no `World` local de `arena.nx`.
- **Não há remoção de elemento de array.** Filtrar é reconstruir num array novo e reatribuir.
- **`rand.random()` retorna sempre `0`** (divisão inteira no stdlib). Todo aleatório passa por `src/rng.nx`.
- **Ordem de declaração importa** para globais usadas dentro de funções: declare constantes de módulo no topo do arquivo.
- **Sintaxe:** `if c then … elif c then … else … end`, `while c do … end`, `for i in range(n) do … end`, `func f(a: T) -> R … end`. Negação é `!`, e/ou são `&&`/`||`.
- **Rodar sempre a partir da raiz do projeto** (`C:\Users\sandr\Documents\noxy_projects\my_noxy_game`): `use src.vec` resolve relativo ao diretório de trabalho, não ao arquivo.
- **Git:** o projeto ainda não é um repositório. Se `git init` não tiver sido feito, **pule os passos de commit** — não rode `git init` sem o usuário pedir.

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `src/vec.nx` | `V`, `sqrt`, e a álgebra vetorial. Não depende de nada. |
| `src/rng.nx` | Aleatoriedade utilizável (`rand` do stdlib é insuficiente). |
| `src/world.nx` | Os structs de dados, as constantes da arena, `new_world`. Depende de `vec`. |
| `src/combat.nx` | Simulação de um quadro: jogador, tiro, balas, inimigos, dano, partículas. |
| `src/waves.nx` | Tabela de ondas, escolha de tipo, spawn nas bordas, fim de onda. |
| `src/upgrades.nx` | Catálogo de seis, sorteio de três, aplicação no jogador. |
| `src/render.nx` | Paleta, câmera, desenho do mundo, HUD e telas. Único módulo que usa a engine além de `arena.nx`. |
| `arena.nx` | Janela, loop, máquina de telas, input. Sem regra de jogo. |
| `tests/run.nx` | Suíte da simulação, sem janela. Uma `func test_*` por módulo. |

---

### Task 1: Álgebra vetorial e o arnês de testes

**Files:**
- Create: `src/vec.nx`
- Create: `tests/run.nx`

**Interfaces:**
- Consumes: nada.
- Produces: `vec.V(x: float, y: float)`; `vec.sqrt(v: float) -> float`; `vec.len(a: V) -> float`; `vec.norm(a: V) -> V`; `vec.add(a: V, b: V) -> V`; `vec.sub(a: V, b: V) -> V`; `vec.scale(a: V, k: float) -> V`; `vec.perp(a: V) -> V`; `vec.dist(a: V, b: V) -> float`. E o arnês: `check(name: string, cond: bool)`, `near(a: float, b: float, tol: float) -> bool`, `report()`.

- [ ] **Step 1: Escrever o teste que falha**

Crie `tests/run.nx`:

```noxy
// tests/run.nx — suíte da simulação. Roda sem abrir janela:
//     noxy tests/run.nx      (a partir da raiz do projeto)
use sys
use src.vec as vec

let fails = 0
let total = 0

func check(name: string, cond: bool) -> void
    total = total + 1
    if cond then
        print(f"  ok   {name}")
    else
        print(f"FAIL   {name}")
        fails = fails + 1
    end
end

func near(a: float, b: float, tol: float) -> bool
    let d = a - b
    if d < 0.0 then
        d = -d
    end
    return d <= tol
end

func report() -> void
    print("")
    print(f"{total - fails}/{total} passaram")
    if fails > 0 then
        sys.exit(1)
    end
end

func test_vec() -> void
    print("vec")
    check("sqrt(0) = 0", near(vec.sqrt(0.0), 0.0, 0.0001))
    check("sqrt(1) = 1", near(vec.sqrt(1.0), 1.0, 0.0001))
    check("sqrt(2) = 1.4142", near(vec.sqrt(2.0), 1.41421356, 0.0001))
    check("sqrt(0.25) = 0.5", near(vec.sqrt(0.25), 0.5, 0.0001))
    check("sqrt(1e6) = 1000", near(vec.sqrt(1000000.0), 1000.0, 0.001))
    check("sqrt de negativo nao explode", near(vec.sqrt(-4.0), 0.0, 0.0001))

    let n: vec.V = vec.norm(vec.V(3.0, 4.0))
    check("norm(3,4).x = 0.6", near(n.x, 0.6, 0.0001))
    check("norm(3,4).y = 0.8", near(n.y, 0.8, 0.0001))

    let z: vec.V = vec.norm(vec.V(0.0, 0.0))
    check("norm do vetor zero nao divide por zero", z.x == 0.0 && z.y == 0.0)

    let p: vec.V = vec.perp(vec.V(2.0, 5.0))
    check("perp e ortogonal", near(p.x * 2.0 + p.y * 5.0, 0.0, 0.0001))
    check("perp preserva o comprimento", near(vec.len(p), vec.len(vec.V(2.0, 5.0)), 0.0001))

    check("len(3,4) = 5", near(vec.len(vec.V(3.0, 4.0)), 5.0, 0.0001))
    check("dist((1,1),(4,5)) = 5", near(vec.dist(vec.V(1.0, 1.0), vec.V(4.0, 5.0)), 5.0, 0.0001))

    let s: vec.V = vec.scale(vec.V(2.0, -3.0), 2.5)
    check("scale multiplica os dois eixos", s.x == 5.0 && s.y == -7.5)

    let a: vec.V = vec.add(vec.V(1.0, 2.0), vec.V(10.0, 20.0))
    check("add soma", a.x == 11.0 && a.y == 22.0)

    let b: vec.V = vec.sub(vec.V(10.0, 20.0), vec.V(1.0, 2.0))
    check("sub subtrai", b.x == 9.0 && b.y == 18.0)
end

test_vec()
report()
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `noxy tests/run.nx`
Expected: FALHA de compilação, algo como `module 'src.vec' not found` — `src/vec.nx` ainda não existe.

- [ ] **Step 3: Implementar `src/vec.nx`**

```noxy
// src/vec.nx — algebra vetorial. Noxy nao tem modulo math, entao sqrt e
// implementado aqui e nenhuma rotacao usa angulo: direcao e vetor unitario,
// giro de 90 graus e perp().

struct V
    x: float,
    y: float
end

let EPS = 0.000001

// sqrt por Newton-Raphson. A semente dobra ate passar de v, o que mantem o
// numero de iteracoes pequeno mesmo para valores grandes.
func sqrt(v: float) -> float
    if v <= 0.0 then
        return 0.0
    end
    let g = 1.0
    while g * g < v do
        g = g * 2.0
    end
    for i in range(8) do
        g = 0.5 * (g + v / g)
    end
    return g
end

func add(a: V, b: V) -> V
    return V(a.x + b.x, a.y + b.y)
end

func sub(a: V, b: V) -> V
    return V(a.x - b.x, a.y - b.y)
end

func scale(a: V, k: float) -> V
    return V(a.x * k, a.y * k)
end

func len(a: V) -> float
    return sqrt(a.x * a.x + a.y * a.y)
end

func norm(a: V) -> V
    let l: float = len(a)
    if l < EPS then
        return V(0.0, 0.0)
    end
    return V(a.x / l, a.y / l)
end

// perp gira 90 graus no sentido horario na tela (y cresce para baixo).
func perp(a: V) -> V
    return V(-a.y, a.x)
end

func dist(a: V, b: V) -> float
    return len(sub(a, b))
end
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `noxy tests/run.nx`
Expected: 16 linhas `ok` e `16/16 passaram`, código de saída 0.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add src/vec.nx tests/run.nx
git commit -m "feat: algebra vetorial com sqrt proprio e arnes de testes"
```

---

### Task 2: Aleatoriedade

**Files:**
- Create: `src/rng.nx`
- Modify: `tests/run.nx` (adicionar `test_rng` e sua chamada)

**Interfaces:**
- Consumes: nada.
- Produces: `rng.rand_int(lo: int, hi: int) -> int` (inclusivo nas duas pontas); `rng.rand_float(lo: float, hi: float) -> float`; `rng.rand_dir() -> vec.V` (unitário, direção uniforme o bastante para estilhaços).

- [ ] **Step 1: Escrever o teste que falha**

Em `tests/run.nx`, adicione `use src.rng as rng` no topo (junto dos outros `use`) e a função abaixo antes da linha `test_vec()`:

```noxy
func test_rng() -> void
    print("rng")
    let fora = 0
    let viu_lo = false
    let viu_hi = false
    for i in range(1000) do
        let v: int = rng.rand_int(3, 7)
        if v < 3 || v > 7 then
            fora = fora + 1
        end
        if v == 3 then
            viu_lo = true
        end
        if v == 7 then
            viu_hi = true
        end
    end
    check("rand_int fica no intervalo em 1000 sorteios", fora == 0)
    check("rand_int alcanca o limite inferior", viu_lo)
    check("rand_int alcanca o limite superior (inclusivo)", viu_hi)
    check("rand_int com lo == hi devolve lo", rng.rand_int(4, 4) == 4)
    check("rand_int com hi < lo devolve lo", rng.rand_int(9, 2) == 9)

    let ffora = 0
    for i in range(500) do
        let f: float = rng.rand_float(-2.0, 5.0)
        if f < -2.0 || f > 5.0 then
            ffora = ffora + 1
        end
    end
    check("rand_float fica no intervalo", ffora == 0)

    let mau = 0
    for i in range(200) do
        let d: vec.V = rng.rand_dir()
        if !near(vec.len(d), 1.0, 0.0001) then
            mau = mau + 1
        end
    end
    check("rand_dir e sempre unitario", mau == 0)
end
```

E acrescente a chamada, de modo que o fim do arquivo fique:

```noxy
test_vec()
test_rng()
report()
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `noxy tests/run.nx`
Expected: FALHA de compilação — `module 'src.rng' not found`.

- [ ] **Step 3: Implementar `src/rng.nx`**

```noxy
// src/rng.nx — o stdlib rand nao serve sozinho: rand.random() faz uma divisao
// inteira e retorna sempre 0. Tudo passa por rand_int, e os floats saem de
// uma divisao explicita.
use rand
use src.vec as vec

let SCALE = 10000

func rand_int(lo: int, hi: int) -> int
    if hi <= lo then
        return lo
    end
    let v: int = rand.random_int(lo, hi)
    return v
end

func rand_float(lo: float, hi: float) -> float
    let v: int = rand.random_int(0, SCALE)
    return lo + (hi - lo) * (to_float(v) / to_float(SCALE))
end

// rand_dir sorteia um ponto no quadrado e normaliza. Concentra levemente nas
// diagonais, o que e irrelevante para estilhacos, e evita trigonometria.
func rand_dir() -> vec.V
    for i in range(8) do
        let x: float = rand_float(-1.0, 1.0)
        let y: float = rand_float(-1.0, 1.0)
        let l: float = vec.len(vec.V(x, y))
        if l > 0.1 then
            return vec.V(x / l, y / l)
        end
    end
    return vec.V(1.0, 0.0)
end
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `noxy tests/run.nx`
Expected: `23/23 passaram`.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add src/rng.nx tests/run.nx
git commit -m "feat: aleatoriedade utilizavel sobre o rand do stdlib"
```

---

### Task 3: Os dados do mundo

**Files:**
- Create: `src/world.nx`
- Modify: `tests/run.nx`

**Interfaces:**
- Consumes: `vec.V`.
- Produces: as constantes `wld.ARENA_W = 1600.0`, `wld.ARENA_H = 1200.0`, `wld.VIEW_W = 960.0`, `wld.VIEW_H = 640.0`, `wld.PLAYER_R = 12.0`; os structs `wld.Player`, `wld.Enemy`, `wld.Bullet`, `wld.Particle`, `wld.World`; e `wld.new_world() -> World`.

Ordem dos campos de cada struct — os construtores são posicionais, então tarefas seguintes dependem disto exatamente:

- `Player(pos, hp, hp_max, speed, fire_rate, fire_cd, damage, bullet_speed, pierce, shots, invuln, aim)`
- `Enemy(pos, vel, kind, hp, radius, speed, touch, flash)`
- `Bullet(pos, vel, life, damage, hits)`
- `Particle(pos, vel, life, life_max, color)`
- `World(player, enemies, bullets, particles, wave, to_spawn, spawn_cd, kills, screen, offers, shake, time)`

- [ ] **Step 1: Escrever o teste que falha**

Adicione `use src.world as wld` ao topo de `tests/run.nx` e esta função:

```noxy
func test_world() -> void
    print("world")
    let w: wld.World = wld.new_world()
    check("jogador comeca no centro da arena", w.player.pos.x == wld.ARENA_W / 2.0 && w.player.pos.y == wld.ARENA_H / 2.0)
    check("vida cheia", w.player.hp == 100.0 && w.player.hp_max == 100.0)
    check("um tiro por vez no comeco", w.player.shots == 1)
    check("sem perfuracao no comeco", w.player.pierce == 0)
    check("pronto para atirar", w.player.fire_cd == 0.0)
    check("sem invencibilidade no comeco", w.player.invuln == 0.0)
    check("mira inicial nao e o vetor zero", vec.len(w.player.aim) > 0.5)
    check("mundo comeca vazio", length(w.enemies) == 0 && length(w.bullets) == 0 && length(w.particles) == 0)
    check("comeca na tela de jogo", w.screen == 0)
    check("placar zerado", w.kills == 0 && w.wave == 0 && w.time == 0.0)
    check("arena e maior que a janela", wld.ARENA_W > wld.VIEW_W && wld.ARENA_H > wld.VIEW_H)

    // new_world nao pode devolver dois mundos que compartilham arrays
    let a: wld.World = wld.new_world()
    let b: wld.World = wld.new_world()
    append(ref a.enemies, wld.Enemy(vec.V(0.0, 0.0), vec.V(0.0, 0.0), 0, 1.0, 1.0, 1.0, 1.0, 0.0))
    check("mundos novos sao independentes", length(b.enemies) == 0)
end
```

Chamada: `test_world()` depois de `test_rng()`.

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `noxy tests/run.nx`
Expected: FALHA — `module 'src.world' not found`.

- [ ] **Step 3: Implementar `src/world.nx`**

```noxy
// src/world.nx — os dados e nada mais. Nenhuma funcao daqui simula ou desenha,
// e o modulo nao conhece a engine: Particle.color e um indice de paleta que so
// o render resolve.
use src.vec as vec

let ARENA_W = 1600.0
let ARENA_H = 1200.0
let VIEW_W = 960.0
let VIEW_H = 640.0
let PLAYER_R = 12.0

struct Player
    pos: vec.V,
    hp: float,
    hp_max: float,
    speed: float,
    fire_rate: float,      // tiros por segundo
    fire_cd: float,        // segundos ate poder atirar de novo
    damage: float,
    bullet_speed: float,
    pierce: int,           // inimigos atravessados alem do primeiro
    shots: int,            // 1 = simples, 3 = leque
    invuln: float,         // segundos restantes de invencibilidade
    aim: vec.V             // unitario; guardado para o desenho
end

struct Enemy
    pos: vec.V,
    vel: vec.V,            // perseguicao, aplicada depois da separacao
    kind: int,             // 0 chaser, 1 rusher, 2 tank
    hp: float,
    radius: float,
    speed: float,
    touch: float,          // dano de contato
    flash: float           // segundos restantes de flash branco
end

struct Bullet
    pos: vec.V,
    vel: vec.V,
    life: float,
    damage: float,
    hits: int              // inimigos ja atravessados
end

struct Particle
    pos: vec.V,
    vel: vec.V,
    life: float,
    life_max: float,
    color: int             // indice de paleta, resolvido no render
end

struct World
    player: Player,
    enemies: Enemy[],
    bullets: Bullet[],
    particles: Particle[],
    wave: int,
    to_spawn: int,         // inimigos da onda ainda nao postos em campo
    spawn_cd: float,
    kills: int,
    screen: int,           // 0 jogando, 1 upgrade, 2 game over, 3 vitoria
    offers: int[],         // indices dos tres upgrades ofertados
    shake: float,          // intensidade restante da tremida
    time: float            // segundos de partida
end

func new_player() -> Player
    return Player(vec.V(ARENA_W / 2.0, ARENA_H / 2.0), 100.0, 100.0, 220.0, 5.0, 0.0, 10.0, 600.0, 0, 1, 0.0, vec.V(1.0, 0.0))
end

func new_world() -> World
    let es: Enemy[] = []
    let bs: Bullet[] = []
    let ps: Particle[] = []
    let of: int[] = []
    return World(new_player(), es, bs, ps, 0, 0, 0.0, 0, 0, of, 0.0, 0.0)
end
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `noxy tests/run.nx`
Expected: `35/35 passaram`.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add src/world.nx tests/run.nx
git commit -m "feat: structs do mundo e estado inicial"
```

---

### Task 4: Movimento do jogador

**Files:**
- Create: `src/combat.nx`
- Modify: `tests/run.nx`

**Interfaces:**
- Consumes: `vec.*`, `wld.*`.
- Produces: `combat.move_player(w: ref wld.World, mv: vec.V, aim: vec.V, dt: float) -> void` e `combat.clamp_player(w: ref wld.World) -> void`.

`mv` chega cru do teclado (componentes −1, 0 ou 1) e é normalizado aqui, para a diagonal não ser mais rápida. `aim` é o vetor do jogador até o mouse, já em coordenadas de mundo; se for praticamente zero, a mira anterior é preservada para o triângulo não degenerar.

- [ ] **Step 1: Escrever o teste que falha**

Adicione `use src.combat as combat` ao topo de `tests/run.nx` e:

```noxy
func test_move() -> void
    print("combat: movimento")
    let w: wld.World = wld.new_world()
    let x0 = w.player.pos.x
    combat.move_player(ref w, vec.V(1.0, 0.0), vec.V(1.0, 0.0), 1.0)
    check("anda a speed px por segundo", near(w.player.pos.x, x0 + 220.0, 0.001))

    // a diagonal nao pode ser mais rapida que a reta
    let d: wld.World = wld.new_world()
    combat.move_player(ref d, vec.V(1.0, 1.0), vec.V(1.0, 0.0), 1.0)
    let andou: float = vec.dist(d.player.pos, vec.V(wld.ARENA_W / 2.0, wld.ARENA_H / 2.0))
    check("diagonal anda o mesmo que a reta", near(andou, 220.0, 0.001))

    // parado e parado
    let s: wld.World = wld.new_world()
    combat.move_player(ref s, vec.V(0.0, 0.0), vec.V(1.0, 0.0), 1.0)
    check("sem input nao anda", s.player.pos.x == wld.ARENA_W / 2.0 && s.player.pos.y == wld.ARENA_H / 2.0)

    // paredes
    let p: wld.World = wld.new_world()
    for i in range(60) do
        combat.move_player(ref p, vec.V(-1.0, -1.0), vec.V(1.0, 0.0), 1.0)
    end
    check("nao sai pela borda esquerda", p.player.pos.x >= wld.PLAYER_R)
    check("nao sai pela borda de cima", p.player.pos.y >= wld.PLAYER_R)
    for i in range(120) do
        combat.move_player(ref p, vec.V(1.0, 1.0), vec.V(1.0, 0.0), 1.0)
    end
    check("nao sai pela borda direita", p.player.pos.x <= wld.ARENA_W - wld.PLAYER_R)
    check("nao sai pela borda de baixo", p.player.pos.y <= wld.ARENA_H - wld.PLAYER_R)

    // mira
    let m: wld.World = wld.new_world()
    combat.move_player(ref m, vec.V(0.0, 0.0), vec.V(0.0, 30.0), 0.016)
    check("mira normaliza", near(vec.len(m.player.aim), 1.0, 0.0001))
    check("mira aponta para o alvo", near(m.player.aim.y, 1.0, 0.0001))
    combat.move_player(ref m, vec.V(0.0, 0.0), vec.V(0.0, 0.0), 0.016)
    check("mira nula preserva a anterior", near(m.player.aim.y, 1.0, 0.0001))

    // temporizadores
    let t: wld.World = wld.new_world()
    t.player.fire_cd = 0.5
    t.player.invuln = 0.5
    t.shake = 10.0
    combat.move_player(ref t, vec.V(0.0, 0.0), vec.V(1.0, 0.0), 0.25)
    check("fire_cd decai com dt", near(t.player.fire_cd, 0.25, 0.0001))
    check("invuln decai com dt", near(t.player.invuln, 0.25, 0.0001))
    check("tempo de partida acumula", near(t.time, 0.25, 0.0001))
    check("tremida decai", t.shake < 10.0)
    combat.move_player(ref t, vec.V(0.0, 0.0), vec.V(1.0, 0.0), 5.0)
    check("fire_cd nao fica negativo", t.player.fire_cd >= 0.0)
    check("invuln nao fica negativo", t.player.invuln >= 0.0)
    check("tremida nao fica negativa", t.shake >= 0.0)
end
```

Chamada: `test_move()` depois de `test_world()`.

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `noxy tests/run.nx`
Expected: FALHA — `module 'src.combat' not found`.

- [ ] **Step 3: Implementar `src/combat.nx`**

```noxy
// src/combat.nx — a simulacao de um quadro. Nao conhece a engine: recebe o
// input ja traduzido em vetores e devolve tudo escrito no World.
use src.vec as vec
use src.world as wld
use src.rng as rng

let SHAKE_DECAY = 30.0

func clamp_player(w: ref wld.World) -> void
    let r: float = wld.PLAYER_R
    if w.player.pos.x < r then
        w.player.pos.x = r
    end
    if w.player.pos.y < r then
        w.player.pos.y = r
    end
    if w.player.pos.x > wld.ARENA_W - r then
        w.player.pos.x = wld.ARENA_W - r
    end
    if w.player.pos.y > wld.ARENA_H - r then
        w.player.pos.y = wld.ARENA_H - r
    end
end

// move_player normaliza mv (a diagonal nao pode ser mais rapida que a reta),
// atualiza a mira e faz decair os temporizadores do quadro.
func move_player(w: ref wld.World, mv: vec.V, aim: vec.V, dt: float) -> void
    let d: vec.V = vec.norm(mv)
    w.player.pos.x = w.player.pos.x + d.x * w.player.speed * dt
    w.player.pos.y = w.player.pos.y + d.y * w.player.speed * dt
    clamp_player(w)

    let a: vec.V = vec.norm(aim)
    if a.x != 0.0 || a.y != 0.0 then
        w.player.aim = a
    end

    if w.player.fire_cd > 0.0 then
        w.player.fire_cd = w.player.fire_cd - dt
        if w.player.fire_cd < 0.0 then
            w.player.fire_cd = 0.0
        end
    end
    if w.player.invuln > 0.0 then
        w.player.invuln = w.player.invuln - dt
        if w.player.invuln < 0.0 then
            w.player.invuln = 0.0
        end
    end
    if w.shake > 0.0 then
        w.shake = w.shake - dt * SHAKE_DECAY
        if w.shake < 0.0 then
            w.shake = 0.0
        end
    end
    w.time = w.time + dt
end
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `noxy tests/run.nx`
Expected: `52/52 passaram`.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add src/combat.nx tests/run.nx
git commit -m "feat: movimento do jogador, mira e temporizadores"
```

---

### Task 5: Tiro e balas

**Files:**
- Modify: `src/combat.nx`
- Modify: `tests/run.nx`

**Interfaces:**
- Consumes: o de Task 4.
- Produces: `combat.fire(w: ref wld.World) -> void` (respeita `fire_cd`, dispara 1 ou 3 balas conforme `shots`); `combat.move_bullets(w: ref wld.World, dt: float) -> void` (move e envelhece; **não** remove — quem remove é `reap`, na Task 7).

O leque de ±12° gira o vetor de mira por uma matriz com seno e cosseno **constantes pré-computados**, nunca por trigonometria em runtime.

- [ ] **Step 1: Escrever o teste que falha**

```noxy
func test_fire() -> void
    print("combat: tiro")
    let w: wld.World = wld.new_world()
    w.player.aim = vec.V(1.0, 0.0)
    combat.fire(ref w)
    check("um tiro sai uma bala", length(w.bullets) == 1)
    check("a bala herda o dano do jogador", w.bullets[0].damage == 10.0)
    check("a bala sai a bullet_speed", near(vec.len(w.bullets[0].vel), 600.0, 0.001))
    check("a bala nasce a frente do jogador", w.bullets[0].pos.x > w.player.pos.x)
    check("a bala nasce sem acertos", w.bullets[0].hits == 0)
    check("atirar poe a arma em recarga", near(w.player.fire_cd, 0.2, 0.0001))

    combat.fire(ref w)
    check("nao atira durante a recarga", length(w.bullets) == 1)

    w.player.fire_cd = 0.0
    combat.fire(ref w)
    check("atira de novo quando a recarga acaba", length(w.bullets) == 2)

    // leque
    let l: wld.World = wld.new_world()
    l.player.aim = vec.V(1.0, 0.0)
    l.player.shots = 3
    combat.fire(ref l)
    check("leque sai com tres balas", length(l.bullets) == 3)
    check("a bala do meio segue a mira", near(l.bullets[0].vel.y, 0.0, 0.001))
    check("as laterais abrem para os dois lados", l.bullets[1].vel.y * l.bullets[2].vel.y < 0.0)
    check("as tres saem na mesma velocidade", near(vec.len(l.bullets[1].vel), 600.0, 0.001) && near(vec.len(l.bullets[2].vel), 600.0, 0.001))

    // cadencia alta encurta a recarga
    let c: wld.World = wld.new_world()
    c.player.aim = vec.V(1.0, 0.0)
    c.player.fire_rate = 10.0
    combat.fire(ref c)
    check("cadencia maior encurta a recarga", near(c.player.fire_cd, 0.1, 0.0001))

    // movimento das balas
    let m: wld.World = wld.new_world()
    m.player.aim = vec.V(1.0, 0.0)
    combat.fire(ref m)
    let x0 = m.bullets[0].pos.x
    combat.move_bullets(ref m, 0.1)
    check("a bala anda vel * dt", near(m.bullets[0].pos.x, x0 + 60.0, 0.001))
    check("a bala envelhece", near(m.bullets[0].life, 1.1, 0.0001))

    // fim da vida util e saida da arena marcam a bala, sem remove-la
    m.bullets[0].life = 0.05
    combat.move_bullets(ref m, 0.1)
    check("a bala expira zerando a vida", m.bullets[0].life <= 0.0)
    check("move_bullets nao remove nada", length(m.bullets) == 1)

    let o: wld.World = wld.new_world()
    o.player.aim = vec.V(1.0, 0.0)
    combat.fire(ref o)
    o.bullets[0].pos.x = wld.ARENA_W + 5.0
    combat.move_bullets(ref o, 0.016)
    check("bala fora da arena morre", o.bullets[0].life <= 0.0)
end
```

Chamada: `test_fire()` depois de `test_move()`.

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `noxy tests/run.nx`
Expected: FALHA de compilação — `undefined` para `combat.fire`.

- [ ] **Step 3: Implementar em `src/combat.nx`**

Acrescente as constantes logo abaixo de `let SHAKE_DECAY = 30.0`:

```noxy
let COS12 = 0.97814760
let SIN12 = 0.20791169
let MUZZLE = 16.0
let BULLET_LIFE = 1.2
```

E as funções ao fim do arquivo:

```noxy
// rotate gira v pelo angulo cujo cosseno e seno foram passados. Os valores sao
// constantes pre-computadas: Noxy nao tem sin/cos.
func rotate(v: vec.V, c: float, s: float) -> vec.V
    return vec.V(v.x * c - v.y * s, v.x * s + v.y * c)
end

func spawn_bullet(w: ref wld.World, d: vec.V) -> void
    let pos: vec.V = vec.V(w.player.pos.x + d.x * MUZZLE, w.player.pos.y + d.y * MUZZLE)
    let vel: vec.V = vec.scale(d, w.player.bullet_speed)
    append(ref w.bullets, wld.Bullet(pos, vel, BULLET_LIFE, w.player.damage, 0))
end

func fire(w: ref wld.World) -> void
    if w.player.fire_cd > 0.0 then
        return
    end
    w.player.fire_cd = 1.0 / w.player.fire_rate
    let d: vec.V = w.player.aim
    spawn_bullet(w, d)
    if w.player.shots >= 3 then
        spawn_bullet(w, rotate(d, COS12, SIN12))
        spawn_bullet(w, rotate(d, COS12, -SIN12))
    end
end

// move_bullets so move e envelhece; a remocao acontece em reap, depois que as
// colisoes tiveram chance de zerar a vida de quem acertou.
func move_bullets(w: ref wld.World, dt: float) -> void
    for i in range(length(w.bullets)) do
        w.bullets[i].pos.x = w.bullets[i].pos.x + w.bullets[i].vel.x * dt
        w.bullets[i].pos.y = w.bullets[i].pos.y + w.bullets[i].vel.y * dt
        w.bullets[i].life = w.bullets[i].life - dt
        if w.bullets[i].pos.x < 0.0 || w.bullets[i].pos.x > wld.ARENA_W then
            w.bullets[i].life = 0.0
        end
        if w.bullets[i].pos.y < 0.0 || w.bullets[i].pos.y > wld.ARENA_H then
            w.bullets[i].life = 0.0
        end
    end
end
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `noxy tests/run.nx`
Expected: `70/70 passaram`.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add src/combat.nx tests/run.nx
git commit -m "feat: tiro com cadencia, leque triplo e movimento das balas"
```

---

### Task 6: Inimigos — perseguição, separação e contato

**Files:**
- Modify: `src/combat.nx`
- Modify: `tests/run.nx`

**Interfaces:**
- Consumes: o de Task 5.
- Produces: `combat.make_enemy(kind: int, at: vec.V) -> wld.Enemy`; `combat.update_enemies(w: ref wld.World, dt: float) -> void`; `combat.resolve_contact(w: ref wld.World) -> void`.

Tabela de inimigos (`make_enemy` é a fonte única desses números; `waves.nx` a consome na Task 8):

| kind | Tipo   | Vel | HP | Raio | Contato |
|---|--------|-----|----|------|---------|
| 0 | Chaser | 90  | 20 | 14   | 10      |
| 1 | Rusher | 170 | 10 | 11   | 8       |
| 2 | Tank   | 55  | 60 | 20   | 20      |

- [ ] **Step 1: Escrever o teste que falha**

```noxy
func test_enemies() -> void
    print("combat: inimigos")
    let w: wld.World = wld.new_world()
    let alvo: vec.V = w.player.pos

    let c: wld.Enemy = combat.make_enemy(0, vec.V(10.0, 10.0))
    check("chaser tem 20 de vida", c.hp == 20.0)
    check("chaser anda a 90", c.speed == 90.0)
    let r: wld.Enemy = combat.make_enemy(1, vec.V(10.0, 10.0))
    check("rusher e rapido e fragil", r.speed == 170.0 && r.hp == 10.0)
    let t: wld.Enemy = combat.make_enemy(2, vec.V(10.0, 10.0))
    check("tank e lento e duro", t.speed == 55.0 && t.hp == 60.0)
    check("tank machuca mais no contato", t.touch > c.touch)
    check("kind desconhecido vira chaser", combat.make_enemy(99, vec.V(0.0, 0.0)).kind == 0)

    // perseguicao
    append(ref w.enemies, combat.make_enemy(0, vec.V(alvo.x - 400.0, alvo.y)))
    let antes: float = vec.dist(w.enemies[0].pos, alvo)
    combat.update_enemies(ref w, 1.0)
    let depois: float = vec.dist(w.enemies[0].pos, alvo)
    check("o inimigo se aproxima do jogador", depois < antes)
    check("anda speed * dt", near(antes - depois, 90.0, 0.01))

    // flash decai
    w.enemies[0].flash = 0.1
    combat.update_enemies(ref w, 0.05)
    check("o flash de acerto decai", near(w.enemies[0].flash, 0.05, 0.0001))
    combat.update_enemies(ref w, 1.0)
    check("o flash nao fica negativo", w.enemies[0].flash >= 0.0)

    // separacao: dois inimigos exatamente em cima um do outro se afastam
    let s: wld.World = wld.new_world()
    append(ref s.enemies, combat.make_enemy(0, vec.V(300.0, 300.0)))
    append(ref s.enemies, combat.make_enemy(0, vec.V(302.0, 300.0)))
    combat.update_enemies(ref s, 0.016)
    check("inimigos sobrepostos se separam", vec.dist(s.enemies[0].pos, s.enemies[1].pos) > 2.0)

    // contato
    let k: wld.World = wld.new_world()
    append(ref k.enemies, combat.make_enemy(0, vec.V(k.player.pos.x, k.player.pos.y)))
    combat.resolve_contact(ref k)
    check("contato tira vida", k.player.hp == 90.0)
    check("contato liga a invencibilidade", k.player.invuln > 0.0)
    check("contato sacode a tela", k.shake > 0.0)

    let hp1 = k.player.hp
    combat.resolve_contact(ref k)
    check("invencibilidade impede dano em sequencia", k.player.hp == hp1)

    // morte
    let m: wld.World = wld.new_world()
    m.player.hp = 5.0
    append(ref m.enemies, combat.make_enemy(0, vec.V(m.player.pos.x, m.player.pos.y)))
    combat.resolve_contact(ref m)
    check("vida nao fica negativa", m.player.hp == 0.0)
    check("morrer leva a tela de game over", m.screen == 2)
end
```

Chamada: `test_enemies()` depois de `test_fire()`.

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `noxy tests/run.nx`
Expected: FALHA — `combat.make_enemy` indefinida.

- [ ] **Step 3: Implementar em `src/combat.nx`**

Acrescente às constantes do topo:

```noxy
let INVULN = 0.6
let KNOCKBACK = 26.0
let HIT_SHAKE = 12.0
```

E ao fim do arquivo:

```noxy
// make_enemy e a fonte unica dos numeros de cada tipo; waves.nx so escolhe o
// kind e a posicao.
func make_enemy(kind: int, at: vec.V) -> wld.Enemy
    let zero: vec.V = vec.V(0.0, 0.0)
    if kind == 1 then
        return wld.Enemy(at, zero, 1, 10.0, 11.0, 170.0, 8.0, 0.0)
    end
    if kind == 2 then
        return wld.Enemy(at, zero, 2, 60.0, 20.0, 55.0, 20.0, 0.0)
    end
    return wld.Enemy(at, zero, 0, 20.0, 14.0, 90.0, 10.0, 0.0)
end

// update_enemies faz tres passadas: mira, separa e so entao anda. Separar
// antes de andar evita que dois inimigos troquem de lado num quadro.
func update_enemies(w: ref wld.World, dt: float) -> void
    let n = length(w.enemies)
    for i in range(n) do
        let dir: vec.V = vec.norm(vec.sub(w.player.pos, w.enemies[i].pos))
        w.enemies[i].vel = vec.scale(dir, w.enemies[i].speed)
        if w.enemies[i].flash > 0.0 then
            w.enemies[i].flash = w.enemies[i].flash - dt
            if w.enemies[i].flash < 0.0 then
                w.enemies[i].flash = 0.0
            end
        end
    end

    for i in range(n) do
        for j in range(i + 1, n) do
            let dx = w.enemies[j].pos.x - w.enemies[i].pos.x
            let dy = w.enemies[j].pos.y - w.enemies[i].pos.y
            let minr = w.enemies[i].radius + w.enemies[j].radius
            let d2 = dx * dx + dy * dy
            if d2 < minr * minr then
                let ux = 1.0
                let uy = 0.0
                let push = minr * 0.5
                if d2 > 0.0001 then
                    let d: float = vec.sqrt(d2)
                    ux = dx / d
                    uy = dy / d
                    push = (minr - d) * 0.5
                end
                w.enemies[i].pos.x = w.enemies[i].pos.x - ux * push
                w.enemies[i].pos.y = w.enemies[i].pos.y - uy * push
                w.enemies[j].pos.x = w.enemies[j].pos.x + ux * push
                w.enemies[j].pos.y = w.enemies[j].pos.y + uy * push
            end
        end
    end

    for i in range(n) do
        w.enemies[i].pos.x = w.enemies[i].pos.x + w.enemies[i].vel.x * dt
        w.enemies[i].pos.y = w.enemies[i].pos.y + w.enemies[i].vel.y * dt
    end
end

// resolve_contact para no primeiro inimigo que encosta: a invencibilidade
// existe justamente para o dano nao ser cobrado varias vezes no mesmo quadro.
func resolve_contact(w: ref wld.World) -> void
    if w.player.invuln > 0.0 then
        return
    end
    for i in range(length(w.enemies)) do
        let dx = w.player.pos.x - w.enemies[i].pos.x
        let dy = w.player.pos.y - w.enemies[i].pos.y
        let rr = wld.PLAYER_R + w.enemies[i].radius
        if dx * dx + dy * dy <= rr * rr then
            w.player.hp = w.player.hp - w.enemies[i].touch
            w.player.invuln = INVULN
            w.shake = HIT_SHAKE

            let away: vec.V = vec.norm(vec.V(dx, dy))
            if away.x == 0.0 && away.y == 0.0 then
                away = vec.V(1.0, 0.0)
            end
            w.player.pos.x = w.player.pos.x + away.x * KNOCKBACK
            w.player.pos.y = w.player.pos.y + away.y * KNOCKBACK
            clamp_player(w)

            if w.player.hp <= 0.0 then
                w.player.hp = 0.0
                w.screen = 2
            end
            return
        end
    end
end
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `noxy tests/run.nx`
Expected: `87/87 passaram`.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add src/combat.nx tests/run.nx
git commit -m "feat: inimigos perseguem, se separam e machucam no contato"
```

---

### Task 7: Acertos, mortes, partículas e o passo do quadro

**Files:**
- Modify: `src/combat.nx`
- Modify: `tests/run.nx`

**Interfaces:**
- Consumes: o de Task 6.
- Produces: `combat.resolve_hits(w: ref wld.World) -> void`; `combat.update_particles(w: ref wld.World, dt: float) -> void`; `combat.reap(w: ref wld.World) -> void`; e `combat.step(w: ref wld.World, mv: vec.V, aim: vec.V, shooting: bool, dt: float) -> void`, a **única** função que `arena.nx` chama enquanto se joga.

Ordem do quadro, fixada por `step`: mover jogador → atirar → mover balas → mover inimigos → resolver acertos → resolver contato → colher os mortos → mover partículas.

- [ ] **Step 1: Escrever o teste que falha**

```noxy
func test_hits() -> void
    print("combat: acertos e mortes")
    let w: wld.World = wld.new_world()
    append(ref w.enemies, combat.make_enemy(0, vec.V(500.0, 500.0)))
    append(ref w.bullets, wld.Bullet(vec.V(500.0, 500.0), vec.V(600.0, 0.0), 1.0, 10.0, 0))
    combat.resolve_hits(ref w)
    check("a bala tira o dano da vida do inimigo", w.enemies[0].hp == 10.0)
    check("o inimigo atingido pisca", w.enemies[0].flash > 0.0)
    check("a bala sem perfuracao morre no acerto", w.bullets[0].life <= 0.0)

    // longe nao acerta
    let f: wld.World = wld.new_world()
    append(ref f.enemies, combat.make_enemy(0, vec.V(500.0, 500.0)))
    append(ref f.bullets, wld.Bullet(vec.V(900.0, 500.0), vec.V(600.0, 0.0), 1.0, 10.0, 0))
    combat.resolve_hits(ref f)
    check("bala longe nao acerta", f.enemies[0].hp == 20.0 && f.bullets[0].life > 0.0)

    // perfuracao
    let p: wld.World = wld.new_world()
    p.player.pierce = 1
    append(ref p.enemies, combat.make_enemy(0, vec.V(500.0, 500.0)))
    append(ref p.enemies, combat.make_enemy(0, vec.V(500.0, 506.0)))
    append(ref p.bullets, wld.Bullet(vec.V(500.0, 503.0), vec.V(600.0, 0.0), 1.0, 10.0, 0))
    combat.resolve_hits(ref p)
    check("com perfuracao a bala acerta os dois", p.enemies[0].hp == 10.0 && p.enemies[1].hp == 10.0)
    check("mas morre no segundo", p.bullets[0].life <= 0.0)

    // colheita
    let k: wld.World = wld.new_world()
    append(ref k.enemies, combat.make_enemy(0, vec.V(500.0, 500.0)))
    append(ref k.enemies, combat.make_enemy(1, vec.V(700.0, 500.0)))
    append(ref k.bullets, wld.Bullet(vec.V(0.0, 0.0), vec.V(0.0, 0.0), 0.0, 10.0, 0))
    append(ref k.bullets, wld.Bullet(vec.V(0.0, 0.0), vec.V(0.0, 0.0), 1.0, 10.0, 0))
    k.enemies[0].hp = 0.0
    combat.reap(ref k)
    check("inimigo morto sai do array", length(k.enemies) == 1)
    check("o sobrevivente e o certo", k.enemies[0].kind == 1)
    check("a morte conta como abate", k.kills == 1)
    check("a morte gera estilhacos", length(k.particles) == 8)
    check("os estilhacos herdam a cor do tipo", k.particles[0].color == 0)
    check("bala sem vida sai do array", length(k.bullets) == 1)
    check("a bala viva fica", k.bullets[0].life == 1.0)

    // particulas
    let q: wld.World = wld.new_world()
    append(ref q.particles, wld.Particle(vec.V(100.0, 100.0), vec.V(100.0, 0.0), 0.5, 0.5, 0))
    combat.update_particles(ref q, 0.1)
    check("a particula anda", q.particles[0].pos.x > 100.0)
    check("a particula desacelera", vec.len(q.particles[0].vel) < 100.0)
    check("a particula envelhece", near(q.particles[0].life, 0.4, 0.0001))
    combat.update_particles(ref q, 1.0)
    check("a particula morta some", length(q.particles) == 0)

    // o passo completo
    let s: wld.World = wld.new_world()
    s.player.aim = vec.V(1.0, 0.0)
    append(ref s.enemies, combat.make_enemy(0, vec.V(s.player.pos.x + 300.0, s.player.pos.y)))
    combat.step(ref s, vec.V(0.0, 0.0), vec.V(1.0, 0.0), true, 0.016)
    check("step atirando cria bala", length(s.bullets) == 1)
    check("step move o inimigo", s.enemies[0].pos.x < s.player.pos.x + 300.0)
    check("step conta o tempo", s.time > 0.0)

    let ns: wld.World = wld.new_world()
    combat.step(ref ns, vec.V(0.0, 0.0), vec.V(1.0, 0.0), false, 0.016)
    check("step sem atirar nao cria bala", length(ns.bullets) == 0)
end
```

Chamada: `test_hits()` depois de `test_enemies()`.

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `noxy tests/run.nx`
Expected: FALHA — `combat.resolve_hits` indefinida.

- [ ] **Step 3: Implementar em `src/combat.nx`**

Acrescente às constantes do topo:

```noxy
let BULLET_R = 3.0
let FLASH = 0.06
let SHARDS = 8
let SHARD_LIFE = 0.5
let SHARD_DRAG = 0.90
```

E ao fim do arquivo:

```noxy
func resolve_hits(w: ref wld.World) -> void
    for bi in range(length(w.bullets)) do
        if w.bullets[bi].life <= 0.0 then
            continue
        end
        for ei in range(length(w.enemies)) do
            if w.enemies[ei].hp <= 0.0 then
                continue
            end
            let dx = w.enemies[ei].pos.x - w.bullets[bi].pos.x
            let dy = w.enemies[ei].pos.y - w.bullets[bi].pos.y
            let rr = w.enemies[ei].radius + BULLET_R
            if dx * dx + dy * dy > rr * rr then
                continue
            end
            w.enemies[ei].hp = w.enemies[ei].hp - w.bullets[bi].damage
            w.enemies[ei].flash = FLASH
            w.bullets[bi].hits = w.bullets[bi].hits + 1
            if w.bullets[bi].hits > w.player.pierce then
                w.bullets[bi].life = 0.0
                break
            end
        end
    end
end

func burst(w: ref wld.World, at: vec.V, kind: int) -> void
    for i in range(SHARDS) do
        let d: vec.V = rng.rand_dir()
        let sp: float = rng.rand_float(60.0, 200.0)
        append(ref w.particles, wld.Particle(at, vec.scale(d, sp), SHARD_LIFE, SHARD_LIFE, kind))
    end
end

// reap e o unico lugar que remove: Noxy nao apaga elemento de array, entao
// filtrar e reconstruir.
func reap(w: ref wld.World) -> void
    let kb: wld.Bullet[] = []
    for i in range(length(w.bullets)) do
        if w.bullets[i].life > 0.0 then
            append(ref kb, w.bullets[i])
        end
    end
    w.bullets = kb

    let ke: wld.Enemy[] = []
    for i in range(length(w.enemies)) do
        if w.enemies[i].hp > 0.0 then
            append(ref ke, w.enemies[i])
        else
            w.kills = w.kills + 1
            burst(w, w.enemies[i].pos, w.enemies[i].kind)
        end
    end
    w.enemies = ke
end

// O arrasto e por quadro, nao por segundo: o jogo roda travado em 60 fps
// (set_fps), e estilhacos vivem meio segundo.
func update_particles(w: ref wld.World, dt: float) -> void
    let keep: wld.Particle[] = []
    for i in range(length(w.particles)) do
        w.particles[i].pos.x = w.particles[i].pos.x + w.particles[i].vel.x * dt
        w.particles[i].pos.y = w.particles[i].pos.y + w.particles[i].vel.y * dt
        w.particles[i].vel = vec.scale(w.particles[i].vel, SHARD_DRAG)
        w.particles[i].life = w.particles[i].life - dt
        if w.particles[i].life > 0.0 then
            append(ref keep, w.particles[i])
        end
    end
    w.particles = keep
end

// step fixa a ordem do quadro. arena.nx nao chama mais nada enquanto se joga.
func step(w: ref wld.World, mv: vec.V, aim: vec.V, shooting: bool, dt: float) -> void
    move_player(w, mv, aim, dt)
    if shooting then
        fire(w)
    end
    move_bullets(w, dt)
    update_enemies(w, dt)
    resolve_hits(w)
    resolve_contact(w)
    reap(w)
    update_particles(w, dt)
end
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `noxy tests/run.nx`
Expected: `108/108 passaram`.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add src/combat.nx tests/run.nx
git commit -m "feat: colisao com perfuracao, mortes com estilhacos e o passo do quadro"
```

---

### Task 8: Ondas

**Files:**
- Create: `src/waves.nx`
- Modify: `tests/run.nx`

**Interfaces:**
- Consumes: `combat.make_enemy`, `wld.*`, `rng.*`.
- Produces: `waves.TOTAL = 8`; `waves.wave_size(n: int) -> int`; `waves.start_wave(w: ref wld.World, n: int) -> void`; `waves.pick_kind(n: int) -> int`; `waves.edge_point() -> vec.V`; `waves.update(w: ref wld.World, dt: float) -> void`; `waves.done(w: wld.World) -> bool`.

- [ ] **Step 1: Escrever o teste que falha**

```noxy
func test_waves() -> void
    print("waves")
    check("oito ondas", waves.TOTAL == 8)
    check("onda 1 tem 7 inimigos", waves.wave_size(1) == 7)
    check("onda 8 tem 28 inimigos", waves.wave_size(8) == 28)

    let w: wld.World = wld.new_world()
    waves.start_wave(ref w, 3)
    check("start_wave anota a onda", w.wave == 3)
    check("start_wave enfileira o tamanho certo", w.to_spawn == waves.wave_size(3))
    check("start_wave libera o primeiro spawn na hora", w.spawn_cd <= 0.0)

    // mistura por onda
    let so_chaser = true
    for i in range(200) do
        if waves.pick_kind(1) != 0 then
            so_chaser = false
        end
    end
    check("onda 1 so tem chasers", so_chaser)

    let sem_tank = true
    for i in range(400) do
        if waves.pick_kind(3) == 2 then
            sem_tank = false
        end
    end
    check("tanks so aparecem da onda 4 em diante", sem_tank)

    let viu_rusher = false
    for i in range(400) do
        if waves.pick_kind(3) == 1 then
            viu_rusher = true
        end
    end
    check("rushers aparecem na onda 3", viu_rusher)

    let viu_tank = false
    for i in range(400) do
        if waves.pick_kind(6) == 2 then
            viu_tank = true
        end
    end
    check("tanks aparecem na onda 6", viu_tank)

    // spawn nas bordas, sempre dentro da arena
    let fora = 0
    for i in range(300) do
        let p: vec.V = waves.edge_point()
        if p.x < 0.0 || p.x > wld.ARENA_W || p.y < 0.0 || p.y > wld.ARENA_H then
            fora = fora + 1
        end
    end
    check("spawn cai dentro da arena", fora == 0)

    // liberacao ao longo do tempo
    let s: wld.World = wld.new_world()
    waves.start_wave(ref s, 1)
    waves.update(ref s, 0.016)
    check("o primeiro inimigo entra logo", length(s.enemies) == 1)
    check("e sai da fila", s.to_spawn == waves.wave_size(1) - 1)
    waves.update(ref s, 0.016)
    check("o segundo espera o intervalo", length(s.enemies) == 1)
    waves.update(ref s, 1.0)
    check("passado o intervalo, entra o segundo", length(s.enemies) == 2)

    // fim de onda
    let d: wld.World = wld.new_world()
    waves.start_wave(ref d, 1)
    check("onda recem-comecada nao terminou", !waves.done(d))
    d.to_spawn = 0
    append(ref d.enemies, combat.make_enemy(0, vec.V(100.0, 100.0)))
    check("com inimigo vivo a onda nao terminou", !waves.done(d))
    let vazio: wld.Enemy[] = []
    d.enemies = vazio
    check("fila vazia e campo limpo terminam a onda", waves.done(d))

    // a fila esvazia por completo
    let f: wld.World = wld.new_world()
    waves.start_wave(ref f, 2)
    for i in range(200) do
        waves.update(ref f, 0.5)
    end
    check("a onda inteira e liberada", f.to_spawn == 0)
    check("e todos entraram em campo", length(f.enemies) == waves.wave_size(2))
end
```

Chamada: `test_waves()` depois de `test_hits()`.

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `noxy tests/run.nx`
Expected: FALHA — `module 'src.waves' not found`.

- [ ] **Step 3: Implementar `src/waves.nx`**

```noxy
// src/waves.nx — quantos inimigos, de que tipo e por onde entram. Os numeros
// de cada tipo moram em combat.make_enemy; aqui so se escolhe kind e posicao.
use src.vec as vec
use src.world as wld
use src.rng as rng
use src.combat as combat

let TOTAL = 8
let SPAWN_GAP = 0.35
let MARGIN = 40.0

func wave_size(n: int) -> int
    return 4 + 3 * n
end

func start_wave(w: ref wld.World, n: int) -> void
    w.wave = n
    w.to_spawn = wave_size(n)
    w.spawn_cd = 0.0
end

// pick_kind abre o leque conforme a onda: chasers sozinhos na 1, rushers da 2
// em diante, tanks da 4, com a fatia de chaser encolhendo.
func pick_kind(n: int) -> int
    if n <= 1 then
        return 0
    end
    let r: int = rng.rand_int(0, 99)
    if n <= 3 then
        if r < 60 then
            return 0
        end
        return 1
    end
    if r < 45 then
        return 0
    end
    if r < 75 then
        return 1
    end
    return 2
end

// edge_point sorteia um dos quatro lados e um ponto nele, recuado pela margem
// para o inimigo nascer dentro da arena.
func edge_point() -> vec.V
    let side: int = rng.rand_int(0, 3)
    if side == 0 then
        return vec.V(rng.rand_float(MARGIN, wld.ARENA_W - MARGIN), MARGIN)
    end
    if side == 1 then
        return vec.V(wld.ARENA_W - MARGIN, rng.rand_float(MARGIN, wld.ARENA_H - MARGIN))
    end
    if side == 2 then
        return vec.V(rng.rand_float(MARGIN, wld.ARENA_W - MARGIN), wld.ARENA_H - MARGIN)
    end
    return vec.V(MARGIN, rng.rand_float(MARGIN, wld.ARENA_H - MARGIN))
end

func update(w: ref wld.World, dt: float) -> void
    if w.to_spawn <= 0 then
        return
    end
    w.spawn_cd = w.spawn_cd - dt
    if w.spawn_cd > 0.0 then
        return
    end
    w.spawn_cd = SPAWN_GAP
    append(ref w.enemies, combat.make_enemy(pick_kind(w.wave), edge_point()))
    w.to_spawn = w.to_spawn - 1
end

func done(w: wld.World) -> bool
    return w.to_spawn <= 0 && length(w.enemies) == 0
end
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `noxy tests/run.nx`
Expected: `128/128 passaram`.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add src/waves.nx tests/run.nx
git commit -m "feat: oito ondas com mistura progressiva e spawn nas bordas"
```

---

### Task 9: Upgrades

**Files:**
- Create: `src/upgrades.nx`
- Modify: `tests/run.nx`

**Interfaces:**
- Consumes: `wld.World`.
- Produces: `up.COUNT = 6`; `up.name(i: int) -> string`; `up.describe(i: int) -> string`; `up.offer() -> int[]` (três índices distintos); `up.apply(w: ref wld.World, i: int) -> void`.

| i | Nome | Efeito |
|---|---|---|
| 0 | Cadência | `fire_rate * 1.35` |
| 1 | Dano | `damage + 6` |
| 2 | Botas | `speed * 1.15` |
| 3 | Blindagem | `hp_max + 30` e cura 30 (limitada ao novo máximo) |
| 4 | Leque triplo | `shots = 3`; se já for 3, `damage + 6` |
| 5 | Perfuração | `pierce + 1` |

- [ ] **Step 1: Escrever o teste que falha**

```noxy
func test_upgrades() -> void
    print("upgrades")
    check("seis upgrades", up.COUNT == 6)

    let sem_nome = 0
    for i in range(up.COUNT) do
        if length(up.name(i)) == 0 || length(up.describe(i)) == 0 then
            sem_nome = sem_nome + 1
        end
    end
    check("todo upgrade tem nome e descricao", sem_nome == 0)

    let ruim = 0
    for k in range(200) do
        let o: int[] = up.offer()
        if length(o) != 3 then
            ruim = ruim + 1
        elif o[0] == o[1] || o[1] == o[2] || o[0] == o[2] then
            ruim = ruim + 1
        elif o[0] < 0 || o[0] >= up.COUNT || o[1] < 0 || o[1] >= up.COUNT || o[2] < 0 || o[2] >= up.COUNT then
            ruim = ruim + 1
        end
    end
    check("offer da tres indices distintos e validos", ruim == 0)

    let a: wld.World = wld.new_world()
    up.apply(ref a, 0)
    check("cadencia sobe 35%", near(a.player.fire_rate, 6.75, 0.0001))
    check("cadencia nao mexe no dano", a.player.damage == 10.0)

    let b: wld.World = wld.new_world()
    up.apply(ref b, 1)
    check("dano sobe 6", b.player.damage == 16.0)

    let c: wld.World = wld.new_world()
    up.apply(ref c, 2)
    check("botas sobem 15%", near(c.player.speed, 253.0, 0.0001))

    let d: wld.World = wld.new_world()
    d.player.hp = 40.0
    up.apply(ref d, 3)
    check("blindagem sobe o maximo", d.player.hp_max == 130.0)
    check("blindagem cura 30", d.player.hp == 70.0)

    let e: wld.World = wld.new_world()
    up.apply(ref e, 3)
    check("blindagem nao cura acima do maximo", e.player.hp == e.player.hp_max && e.player.hp == 130.0)

    let f: wld.World = wld.new_world()
    up.apply(ref f, 4)
    check("leque liga o tiro triplo", f.player.shots == 3)
    check("leque nao mexe no dano na primeira vez", f.player.damage == 10.0)
    up.apply(ref f, 4)
    check("leque repetido vira dano", f.player.damage == 16.0)
    check("leque repetido nao passa de tres tiros", f.player.shots == 3)

    let g: wld.World = wld.new_world()
    up.apply(ref g, 5)
    check("perfuracao sobe 1", g.player.pierce == 1)
    up.apply(ref g, 5)
    check("perfuracao empilha", g.player.pierce == 2)

    let h: wld.World = wld.new_world()
    up.apply(ref h, 1)
    check("dano nao mexe na velocidade nem na cadencia", h.player.speed == 220.0 && h.player.fire_rate == 5.0)
    check("dano nao mexe na vida", h.player.hp == 100.0 && h.player.hp_max == 100.0)
end
```

Chamada: `test_upgrades()` depois de `test_waves()`.

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `noxy tests/run.nx`
Expected: FALHA — `module 'src.upgrades' not found`.

- [ ] **Step 3: Implementar `src/upgrades.nx`**

```noxy
// src/upgrades.nx — catalogo de seis, sorteio de tres sem repetir, aplicacao.
// O unico com teto e o leque: pego duas vezes, vira dano, para que nenhuma
// escolha seja desperdicada.
use src.world as wld
use src.rng as rng

let COUNT = 6

func name(i: int) -> string
    if i == 0 then
        return "Cadencia"
    end
    if i == 1 then
        return "Dano"
    end
    if i == 2 then
        return "Botas"
    end
    if i == 3 then
        return "Blindagem"
    end
    if i == 4 then
        return "Leque triplo"
    end
    return "Perfuracao"
end

func describe(i: int) -> string
    if i == 0 then
        return "+35% de tiros por segundo"
    end
    if i == 1 then
        return "+6 de dano por bala"
    end
    if i == 2 then
        return "+15% de velocidade"
    end
    if i == 3 then
        return "+30 de vida maxima, e cura 30"
    end
    if i == 4 then
        return "atira tres balas em leque"
    end
    return "a bala atravessa mais um inimigo"
end

func offer() -> int[]
    let out: int[] = []
    while length(out) < 3 do
        let c: int = rng.rand_int(0, COUNT - 1)
        let dup = false
        for k in range(length(out)) do
            if out[k] == c then
                dup = true
            end
        end
        if !dup then
            append(ref out, c)
        end
    end
    return out
end

func apply(w: ref wld.World, i: int) -> void
    if i == 0 then
        w.player.fire_rate = w.player.fire_rate * 1.35
    elif i == 1 then
        w.player.damage = w.player.damage + 6.0
    elif i == 2 then
        w.player.speed = w.player.speed * 1.15
    elif i == 3 then
        w.player.hp_max = w.player.hp_max + 30.0
        w.player.hp = w.player.hp + 30.0
        if w.player.hp > w.player.hp_max then
            w.player.hp = w.player.hp_max
        end
    elif i == 4 then
        if w.player.shots >= 3 then
            w.player.damage = w.player.damage + 6.0
        else
            w.player.shots = 3
        end
    else
        w.player.pierce = w.player.pierce + 1
    end
end
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `noxy tests/run.nx`
Expected: `146/146 passaram`.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add src/upgrades.nx tests/run.nx
git commit -m "feat: catalogo de upgrades, sorteio e aplicacao"
```

---

### Task 10: Primeiro marco jogável — janela, câmera e o jogador na tela

**Files:**
- Create: `src/render.nx`
- Create: `arena.nx`

**Interfaces:**
- Consumes: tudo até aqui.
- Produces: `render.camera_base(w: wld.World) -> vec.V` (sem tremida — é a que converte o mouse para o mundo); `render.camera_shaken(w: wld.World) -> vec.V`; `render.world(w: wld.World) -> void` (limpa, aplica a câmera e desenha grade, paredes, partículas, balas, inimigos e jogador, terminando com `camera_reset()`).

A separação entre as duas câmeras é essencial: se a mira usasse a câmera com tremida, o tiro tremeria junto com a tela.

**Formas, todas montadas com `d` (direção) e `perp(d)` — nenhum ângulo:**
- Jogador: triângulo `pos + aim*18`, `pos - aim*8 + perp(aim)*11`, `pos - aim*8 - perp(aim)*11`.
- Chaser (kind 0): losango `c ± d*r`, `c ± perp(d)*r*0.65`.
- Rusher (kind 1): triângulo `c + d*r`, `c - d*r*0.6 ± perp(d)*r*0.75`.
- Tank (kind 2): quadrado `c ± d*r ± perp(d)*r` nos quatro cantos.

- [ ] **Step 1: Escrever `src/render.nx`**

```noxy
// src/render.nx — o unico modulo que desenha. Nenhuma forma usa angulo: cada
// uma e montada a partir da direcao do movimento e da sua perpendicular.
use github_com.estevaofon.noxy_game_engine as game
use src.vec as vec
use src.world as wld
use src.rng as rng

let BG: game.Color = game.rgb(10, 12, 20)
let GRID: game.Color = game.rgb(24, 30, 52)
let WALL: game.Color = game.rgb(70, 84, 130)
let PLAYER_C: game.Color = game.rgb(90, 220, 255)
let PLAYER_HURT: game.Color = game.rgb(255, 255, 255)
let BULLET_C: game.Color = game.rgb(255, 244, 180)
let GRID_STEP = 80.0

func kind_color(k: int) -> game.Color
    if k == 1 then
        return game.rgb(255, 160, 40)
    end
    if k == 2 then
        return game.rgb(180, 100, 255)
    end
    return game.rgb(255, 70, 90)
end

// camera_base e a camera de verdade: centrada no jogador e travada na arena.
// arena.nx usa esta para converter o mouse em coordenadas de mundo.
func camera_base(w: wld.World) -> vec.V
    let cx = w.player.pos.x - wld.VIEW_W / 2.0
    let cy = w.player.pos.y - wld.VIEW_H / 2.0
    if cx < 0.0 then
        cx = 0.0
    end
    if cy < 0.0 then
        cy = 0.0
    end
    if cx > wld.ARENA_W - wld.VIEW_W then
        cx = wld.ARENA_W - wld.VIEW_W
    end
    if cy > wld.ARENA_H - wld.VIEW_H then
        cy = wld.ARENA_H - wld.VIEW_H
    end
    return vec.V(cx, cy)
end

// camera_shaken e so para desenhar. Se a mira usasse esta, o tiro tremeria
// junto com a tela.
func camera_shaken(w: wld.World) -> vec.V
    let c: vec.V = camera_base(w)
    if w.shake <= 0.0 then
        return c
    end
    return vec.V(c.x + rng.rand_float(-w.shake, w.shake), c.y + rng.rand_float(-w.shake, w.shake))
end

func draw_grid(cam: vec.V) -> void
    let x0 = to_float(to_int(cam.x / GRID_STEP)) * GRID_STEP
    let x = x0
    while x < cam.x + wld.VIEW_W + GRID_STEP do
        game.draw_line(x, cam.y, x, cam.y + wld.VIEW_H, GRID, 1.0)
        x = x + GRID_STEP
    end
    let y0 = to_float(to_int(cam.y / GRID_STEP)) * GRID_STEP
    let y = y0
    while y < cam.y + wld.VIEW_H + GRID_STEP do
        game.draw_line(cam.x, y, cam.x + wld.VIEW_W, y, GRID, 1.0)
        y = y + GRID_STEP
    end
end

func draw_player(w: wld.World) -> void
    let d: vec.V = w.player.aim
    let p: vec.V = vec.perp(d)
    let c: vec.V = w.player.pos
    let pts: float[] = [
        c.x + d.x * 18.0, c.y + d.y * 18.0,
        c.x - d.x * 8.0 + p.x * 11.0, c.y - d.y * 8.0 + p.y * 11.0,
        c.x - d.x * 8.0 - p.x * 11.0, c.y - d.y * 8.0 - p.y * 11.0
    ]
    let col: game.Color = PLAYER_C
    if w.player.invuln > 0.0 then
        col = PLAYER_HURT
    end
    game.draw_polygon(pts, col)
end

func draw_enemy(e: wld.Enemy) -> void
    let d: vec.V = vec.norm(e.vel)
    if d.x == 0.0 && d.y == 0.0 then
        d = vec.V(1.0, 0.0)
    end
    let p: vec.V = vec.perp(d)
    let c: vec.V = e.pos
    let r = e.radius
    let col: game.Color = kind_color(e.kind)
    if e.flash > 0.0 then
        col = game.WHITE
    end

    if e.kind == 1 then
        let tri: float[] = [
            c.x + d.x * r, c.y + d.y * r,
            c.x - d.x * r * 0.6 + p.x * r * 0.75, c.y - d.y * r * 0.6 + p.y * r * 0.75,
            c.x - d.x * r * 0.6 - p.x * r * 0.75, c.y - d.y * r * 0.6 - p.y * r * 0.75
        ]
        game.draw_polygon(tri, col)
        return
    end

    if e.kind == 2 then
        let sq: float[] = [
            c.x + d.x * r + p.x * r, c.y + d.y * r + p.y * r,
            c.x + d.x * r - p.x * r, c.y + d.y * r - p.y * r,
            c.x - d.x * r - p.x * r, c.y - d.y * r - p.y * r,
            c.x - d.x * r + p.x * r, c.y - d.y * r + p.y * r
        ]
        game.draw_polygon(sq, col)
        return
    end

    let dia: float[] = [
        c.x + d.x * r, c.y + d.y * r,
        c.x + p.x * r * 0.65, c.y + p.y * r * 0.65,
        c.x - d.x * r, c.y - d.y * r,
        c.x - p.x * r * 0.65, c.y - p.y * r * 0.65
    ]
    game.draw_polygon(dia, col)
end

func world(w: wld.World) -> void
    game.clear(BG)
    let cam: vec.V = camera_shaken(w)
    game.camera_set(cam.x, cam.y)

    draw_grid(cam)
    game.draw_rect_outline(0.0, 0.0, wld.ARENA_W, wld.ARENA_H, WALL, 4.0)

    for i in range(length(w.particles)) do
        let pt: wld.Particle = w.particles[i]
        let a = pt.life / pt.life_max
        let base: game.Color = kind_color(pt.color)
        game.draw_circle(pt.pos.x, pt.pos.y, 3.0 * a + 1.0, game.rgba(base.r, base.g, base.b, to_int(220.0 * a)))
    end

    for i in range(length(w.bullets)) do
        let b: wld.Bullet = w.bullets[i]
        game.draw_line(b.pos.x, b.pos.y, b.pos.x - b.vel.x * 0.02, b.pos.y - b.vel.y * 0.02, BULLET_C, 3.0)
    end

    for i in range(length(w.enemies)) do
        draw_enemy(w.enemies[i])
    end

    draw_player(w)
    game.camera_reset()
end
```

**Nota:** `game.Color` é um struct de campos públicos `r, g, b, a` (todos `int`), verificado no wrapper da engine — por isso `game.rgba(base.r, base.g, base.b, …)` na partícula é válido e reaproveita a cor do tipo com alfa calculado.

- [ ] **Step 2: Escrever `arena.nx` mínimo**

```noxy
// arena.nx — janela, loop e input. Nenhuma regra de jogo mora aqui.
use github_com.estevaofon.noxy_game_engine as game
use src.vec as vec
use src.world as wld
use src.combat as combat
use src.render as render

game.init(960, 640, "Noxy Arena")
game.set_fps(60)

let world: wld.World = wld.new_world()

while game.running() do
    if game.key_pressed("escape") then
        game.stop()
    end

    let dt: float = game.delta()
    if dt > 0.05 then
        dt = 0.05
    end

    let mvx = 0.0
    let mvy = 0.0
    if game.key_down("a") then
        mvx = mvx - 1.0
    end
    if game.key_down("d") then
        mvx = mvx + 1.0
    end
    if game.key_down("w") then
        mvy = mvy - 1.0
    end
    if game.key_down("s") then
        mvy = mvy + 1.0
    end

    let cam: vec.V = render.camera_base(world)
    let m: game.Point = game.mouse_pos()
    let aim: vec.V = vec.V(to_float(m.x) + cam.x - world.player.pos.x, to_float(m.y) + cam.y - world.player.pos.y)

    combat.step(ref world, vec.V(mvx, mvy), aim, game.mouse_down("left"), dt)

    render.world(world)
    game.flip()
end
game.quit()
```

- [ ] **Step 3: Rodar o jogo**

Run: `noxy arena.nx`
Expected: uma janela de 960×640 abre com fundo escuro e grade. Um triângulo ciano no meio anda com WASD e aponta para o cursor. Segurar o botão esquerdo cospe traços amarelos. A câmera segue o jogador e trava nas bordas da arena, onde aparece o contorno azul da parede. Escape fecha.

Verifique à mão: a diagonal não é mais rápida; o jogador não atravessa a parede; a mira não treme.

- [ ] **Step 4: Rodar os testes para confirmar que nada quebrou**

Run: `noxy tests/run.nx`
Expected: `146/146 passaram`.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add src/render.nx arena.nx
git commit -m "feat: janela, camera com trava, desenho do mundo e jogador jogavel"
```

---

### Task 11: Ligar ondas e o ciclo completo de combate

**Files:**
- Modify: `arena.nx`

**Interfaces:**
- Consumes: `waves.*`, `up.*`.
- Produces: nada novo — a máquina de telas passa a existir em `arena.nx`.

- [ ] **Step 1: Acrescentar os `use` e iniciar a primeira onda**

Em `arena.nx`, junte aos imports:

```noxy
use src.waves as waves
use src.upgrades as up
```

E logo após `let world: wld.World = wld.new_world()`:

```noxy
waves.start_wave(ref world, 1)
```

- [ ] **Step 2: Trocar a chamada única de `combat.step` pela máquina de telas**

Substitua a linha `combat.step(ref world, vec.V(mvx, mvy), aim, game.mouse_down("left"), dt)` por:

```noxy
    if world.screen == 0 then
        combat.step(ref world, vec.V(mvx, mvy), aim, game.mouse_down("left"), dt)
        waves.update(ref world, dt)
        if waves.done(world) then
            if world.wave >= waves.TOTAL then
                world.screen = 3
            else
                world.offers = up.offer()
                world.screen = 1
            end
        end
    elif world.screen == 1 then
        let pick = -1
        if game.key_pressed("1") then
            pick = 0
        end
        if game.key_pressed("2") then
            pick = 1
        end
        if game.key_pressed("3") then
            pick = 2
        end
        if pick >= 0 then
            up.apply(ref world, world.offers[pick])
            waves.start_wave(ref world, world.wave + 1)
            world.screen = 0
        end
    else
        if game.key_pressed("r") then
            world = wld.new_world()
            waves.start_wave(ref world, 1)
        end
    end
```

- [ ] **Step 3: Rodar o jogo**

Run: `noxy arena.nx`
Expected: inimigos vermelhos entram pelas bordas e perseguem. Tiros os matam e eles explodem em estilhaços. Encostar num inimigo empurra o jogador e a tela treme. Limpar a onda 1 congela a ação (a tela de upgrade ainda não desenha nada — as teclas 1/2/3 já funcionam e a onda 2 começa). Morrer congela também, e R reinicia.

Este passo tem um buraco visual conhecido e esperado: as telas 1, 2 e 3 não desenham nada ainda. A Task 12 fecha isso.

- [ ] **Step 4: Rodar os testes**

Run: `noxy tests/run.nx`
Expected: `146/146 passaram`.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add arena.nx
git commit -m "feat: ondas, escolha de upgrade e reinicio ligados ao loop"
```

---

### Task 12: HUD e telas

**Files:**
- Modify: `src/render.nx`
- Modify: `arena.nx`

**Interfaces:**
- Consumes: `up.name`, `up.describe`, `waves.TOTAL`.
- Produces: `render.frame(w: wld.World) -> void` — desenha o mundo, o HUD e, conforme `w.screen`, o painel de upgrade, de game over ou de vitória. `arena.nx` passa a chamar só esta.

- [ ] **Step 1: Acrescentar HUD e telas a `src/render.nx`**

Junte aos imports do módulo:

```noxy
use src.upgrades as up
use src.waves as waves
```

E acrescente ao fim do arquivo:

```noxy
let DIM: game.Color = game.rgba(0, 0, 0, 190)
let INK: game.Color = game.rgb(230, 236, 255)
let FADE: game.Color = game.rgb(150, 160, 190)

func centered(s: string, y: float, size: int, c: game.Color) -> void
    let wpx: float = game.text_width(s, size)
    game.draw_text(s, (wld.VIEW_W - wpx) / 2.0, y, size, c)
end

func draw_hud(w: wld.World) -> void
    // barra de vida
    let frac = w.player.hp / w.player.hp_max
    if frac < 0.0 then
        frac = 0.0
    end
    game.draw_rect(16.0, 16.0, 240.0, 18.0, game.rgba(0, 0, 0, 150))
    game.draw_rect(16.0, 16.0, 240.0 * frac, 18.0, game.rgb(90, 230, 130))
    game.draw_rect_outline(16.0, 16.0, 240.0, 18.0, WALL, 2.0)
    game.draw_text(f"{to_int(w.player.hp)} / {to_int(w.player.hp_max)}", 22.0, 17.0, 14, game.BLACK)

    game.draw_text(f"Onda {w.wave} / {waves.TOTAL}", 16.0, 44.0, 18, INK)
    game.draw_text(f"Abates {w.kills}", 16.0, 68.0, 16, FADE)
    game.draw_text(f"Tempo {to_int(w.time)}s", 16.0, 88.0, 16, FADE)

    let restam = w.to_spawn + length(w.enemies)
    game.draw_text(f"Restam {restam}", wld.VIEW_W - 120.0, 16.0, 16, FADE)
end

func draw_upgrade(w: wld.World) -> void
    game.draw_rect(0.0, 0.0, wld.VIEW_W, wld.VIEW_H, DIM)
    centered(f"Onda {w.wave} limpa", 120.0, 34, game.rgb(120, 240, 180))
    centered("Escolha um upgrade", 166.0, 20, INK)
    for i in range(length(w.offers)) do
        let idx = w.offers[i]
        let y = 230.0 + to_float(i) * 84.0
        game.draw_rect(160.0, y, 640.0, 68.0, game.rgba(255, 255, 255, 18))
        game.draw_rect_outline(160.0, y, 640.0, 68.0, WALL, 2.0)
        game.draw_text(f"{i + 1}", 180.0, y + 18.0, 30, game.rgb(120, 240, 180))
        game.draw_text(up.name(idx), 224.0, y + 12.0, 22, INK)
        game.draw_text(up.describe(idx), 224.0, y + 40.0, 16, FADE)
    end
    centered("1, 2 ou 3 para escolher", wld.VIEW_H - 56.0, 16, FADE)
end

func draw_end(w: wld.World) -> void
    game.draw_rect(0.0, 0.0, wld.VIEW_W, wld.VIEW_H, DIM)
    if w.screen == 3 then
        centered("Vitoria", 190.0, 48, game.rgb(120, 240, 180))
        centered("As oito ondas caíram", 252.0, 20, INK)
    else
        centered("Voce morreu", 190.0, 48, game.rgb(255, 90, 110))
        centered(f"na onda {w.wave} de {waves.TOTAL}", 252.0, 20, INK)
    end
    centered(f"{w.kills} abates em {to_int(w.time)} segundos", 300.0, 20, FADE)
    centered("R para jogar de novo    Escape para sair", 380.0, 18, FADE)
end

func frame(w: wld.World) -> void
    world(w)
    draw_hud(w)
    if w.screen == 1 then
        draw_upgrade(w)
    elif w.screen >= 2 then
        draw_end(w)
    end
end
```

- [ ] **Step 2: Apontar `arena.nx` para `render.frame`**

Troque `render.world(world)` por:

```noxy
    render.frame(world)
```

- [ ] **Step 3: Rodar o jogo e percorrer as três telas**

Run: `noxy arena.nx`
Expected:
- Durante o jogo: barra de vida verde no canto, onda, abates, tempo, e a contagem de inimigos restantes à direita.
- Ao limpar uma onda: painel escurecido com três cartas numeradas, nome e descrição de cada upgrade; 1/2/3 escolhe, o efeito é visível na onda seguinte (mais cadência, mais dano, leque triplo…).
- Ao morrer: painel de game over com onda, abates e tempo; R reinicia do zero com o jogador de novo em 100 de vida e sem upgrades.
- Ao vencer a onda 8: painel de vitória.

- [ ] **Step 4: Rodar os testes**

Run: `noxy tests/run.nx`
Expected: `146/146 passaram`.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add src/render.nx arena.nx
git commit -m "feat: HUD, tela de upgrade, game over e vitoria"
```

---

### Task 13: Balanceamento e verificação final

**Files:**
- Modify: `src/world.nx`, `src/waves.nx`, `src/combat.nx` (só constantes, se necessário)
- Create: `README.md`

**Interfaces:**
- Consumes: tudo.
- Produces: nada novo. Esta tarefa ajusta números e documenta.

- [ ] **Step 1: Jogar uma partida inteira e anotar**

Run: `noxy arena.nx`

Jogue até vencer ou morrer e responda, por escrito, antes de mexer em qualquer número:
- A onda 1 é fácil o bastante para aprender os controles?
- Alguma onda vira parede intransponível? Qual?
- O leque triplo e a perfuração parecem valer a escolha ao lado de dano e cadência?
- A arena é grande demais (você passa tempo demais correndo atrás de inimigo) ou pequena demais (não dá para escapar)?

- [ ] **Step 2: Ajustar só as constantes que a partida acusou**

As alavancas, todas em um lugar cada:
- Ritmo da onda: `waves.SPAWN_GAP` (0.35) e `waves.wave_size` (`4 + 3 * n`).
- Dificuldade dos inimigos: os números em `combat.make_enemy`.
- Poder do jogador: os argumentos de `wld.new_player()`.
- Mistura de tipos: os cortes de `waves.pick_kind`.
- Tamanho da arena: `wld.ARENA_W` / `wld.ARENA_H`.

Se `wave_size` mudar, **atualize os testes `onda 1 tem 7 inimigos` e `onda 8 tem 28 inimigos`** em `tests/run.nx` para os novos valores. Mesma coisa para qualquer constante que um teste fixe.

- [ ] **Step 3: Escrever o `README.md`**

```markdown
# Noxy Arena

Um arena shooter top-down de oito ondas, escrito em Noxy sobre o
[noxy_game_engine](https://github.com/estevaofon/noxy_game_engine).

## Jogar

    noxy arena.nx

A partir da raiz do projeto — os módulos são resolvidos a partir do
diretório de trabalho.

## Controles

| Tecla | Ação |
|---|---|
| W A S D | mover |
| Mouse | mirar |
| Botão esquerdo (segurar) | atirar |
| 1 / 2 / 3 | escolher o upgrade entre ondas |
| R | recomeçar depois do fim |
| Escape | sair |

## Como está organizado

A simulação (`src/vec`, `src/rng`, `src/world`, `src/combat`, `src/waves`,
`src/upgrades`) é aritmética pura sobre um struct `World` e não conhece a
engine. `src/render` é o único módulo que desenha. `arena.nx` só lê input,
chama a simulação e desenha.

Essa separação é o que permite testar o jogo sem abrir janela:

    noxy tests/run.nx

## Nota de implementação

Noxy não tem módulo `math`. `src/vec.nx` traz um `sqrt` por Newton-Raphson, e
nenhuma rotação usa ângulo: as formas são montadas a partir de um vetor de
direção e da sua perpendicular, e o leque de tiros gira por uma matriz com
seno e cosseno pré-computados.
```

- [ ] **Step 4: Verificação final**

Run: `noxy tests/run.nx`
Expected: todos passam, código de saída 0.

Run: `noxy arena.nx`
Expected: uma partida inteira do começo ao fim sem travar, sem erro de runtime, e com as três telas de fim aparecendo quando devem.

- [ ] **Step 5: Commit** (pule se não houver repositório git)

```bash
git add README.md src tests arena.nx
git commit -m "docs: README e ajuste de balanceamento"
```

---

## Desvios na execução

Registrados aqui porque o código diverge do plano acima nestes três pontos.

**1. `src/flow.nx` foi extraído (novo módulo, não previsto).** O plano punha a
máquina de telas dentro de `arena.nx` (Task 11), mas ali estão a condição de
vitória (`wave >= TOTAL`), a geração das ofertas e o reinício — regra de jogo
num arquivo que o próprio spec diz não conter regra, e impossível de testar
porque `arena.nx` só roda abrindo janela. Foi movida para `src/flow.nx`, com
`begin`, `reset` e `advance`, e ganhou 17 asserts (`test_flow`). `arena.nx`
ficou só com a tradução de input.

**2. `waves.done` passou a receber `ref wld.World`.** `flow.advance` só tem um
`ref` em mãos e Noxy não converte `ref T` para `T` no argumento. Alternativa
seria duplicar a condição de fim de onda dentro de `flow`; receber `ref`
mantém a regra num lugar só.

**3. `tests/smoke.nx` foi criado (não previsto).** Os passos "rode o jogo e
confira" do plano não são verificáveis por um agente: a janela é interativa.
`smoke.nx` abre a janela, percorre as quatro telas por 20 quadros cada com o
`render` de verdade e sai sozinho — é o que pega erro de comando de desenho,
que os testes sem janela não alcançam.

Além disso, `let r = wld.PLAYER_R` (Task 4) precisou virar
`let r: float = wld.PLAYER_R`: ler membro de módulo não infere tipo, como a
própria seção de constraints avisava. Corrigido no plano acima.

**Não executado:** Task 13, passos 1 e 2 (jogar uma partida inteira e ajustar
o balanceamento). Depende de jogar de verdade, o que só o usuário pode fazer.
Os números continuam nos valores do spec.
