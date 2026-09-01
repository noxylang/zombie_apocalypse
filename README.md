# Noxy Arena

Um arena shooter top-down de oito ondas, escrito em [Noxy](https://github.com/estevaofon/noxy)
sobre o [noxy_game_engine](https://github.com/estevaofon/noxy_game_engine).

Sem assets: tudo na tela é polígono, círculo e linha.

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
conhece a engine. `src/render` é o único módulo que desenha, e `arena.nx` só
traduz teclado e mouse em vetores e entrega para `flow.advance`.

Essa separação é o que permite testar o jogo inteiro sem abrir janela:

    noxy tests/run.nx        # 164 asserts sobre a simulação, sem janela
    noxy tests/smoke.nx      # abre a janela, percorre as 4 telas, sai sozinho

`run.nx` cobre a lógica; `smoke.nx` existe porque erro de comando de desenho
só aparece quando há uma janela para recusá-lo.

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
