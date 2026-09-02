"""tools/pack_sheet.py — empacota as sheets do Gemini em grades regulares.

O Gemini entrega images/shooter.png e images/enemies.png como grades de 14 x 8
celulas de tamanho fracionario, com frames de larguras diferentes, o flash do
cano invadindo a celula vizinha, fumacinhas soltas e varias linhas misturando
vista frontal e lateral. Este script recorta so as linhas coerentes e escreve
images/shooter_sheet.png e images/enemies_sheet.png: uma animacao por linha,
celulas de CELL_W x CELL_H, corpo sempre na mesma posicao da celula.
src/anim.nx conhece esse layout.

Cada frame e um componente conexo do canal alpha, associado a celula da grade
que contem o seu centroide. Componentes que atravessam linhas (uma fumaca
liga um frame ao de baixo) sao cortados na linha de menor espessura entre
cada par de centros; componentes pequenos sao fumaca e ficam de fora.

    python tools/pack_sheet.py          # a partir da raiz do projeto
"""
import math
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent

GRID_COLS, GRID_ROWS = 14, 8
CELL_W, CELL_H = 80, 64
ALPHA_MIN = 20          # abaixo disso e fundo
MIN_AREA = 120          # menor que isso e fumaca ou ponto solto

# Cada animacao: (nome, linha na grade de origem, colunas na grade, espelhar).
# Toda linha de lado sai virada para a direita.
PLAYER = [
    # A caminhada lateral usa so os tres frames de vista lateral da linha 7 da
    # direita (o 5 repetido fecha o ciclo passo largo / pernas juntas): as
    # outras caminhadas misturam tronco de costas e de frente em 3/4, e a
    # alternancia parecia um giro. O idle lateral e o frame parado da
    # caminhada da esquerda, espelhado.
    ("idle_down",  0, range(0, 4),      False),
    ("walk_down",  1, range(0, 6),      False),
    ("walk_up",    1, range(7, 14),     False),
    ("walk_side",  6, [11, 12, 13, 12], False),
    ("shoot_side", 2, range(7, 14),     False),
    ("death",      7, range(7, 14),     False),
    ("idle_side",  4, [0],              True),
]

ENEMIES = [
    # Inimigos so olham para os lados, entao cada visual e uma caminhada
    # lateral. A linha e o kind: 0 chaser, 1 rusher, 2 tank.
    ("zombie_walk",         6, [10, 11, 12, 13], False),   # zumbi comum, bracos estendidos
    ("soldier_walk",        3, [2, 3, 4, 5],     False),   # soldado mascarado correndo
    ("zombie_soldier_walk", 0, [10, 11, 12, 13], False),   # zumbi soldado, postura de fuzil
]

SHEETS = [
    ("images/shooter.png", "images/shooter_sheet.png", PLAYER),
    ("images/enemies.png", "images/enemies_sheet.png", ENEMIES),
]


def components(alpha, w, h):
    """Componentes conexos (8-vizinhanca) do alpha: lista de sets de (x, y)."""
    seen = bytearray(w * h)
    out = []
    for y in range(h):
        for x in range(w):
            if alpha[x, y] <= ALPHA_MIN or seen[y * w + x]:
                continue
            seen[y * w + x] = 1
            q = deque([(x, y)])
            pts = set()
            while q:
                cx, cy = q.popleft()
                pts.add((cx, cy))
                for nx in (cx - 1, cx, cx + 1):
                    for ny in (cy - 1, cy, cy + 1):
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and alpha[nx, ny] > ALPHA_MIN:
                            seen[ny * w + nx] = 1
                            q.append((nx, ny))
            if len(pts) >= MIN_AREA:
                out.append(pts)
    return out


def split_rows(pts, pitch_y):
    """Se o componente atravessa linhas da grade, corta-o na linha (y) mais
    fina entre cada par de centros vizinhos; senao devolve-o inteiro."""
    ys = [p[1] for p in pts]
    if max(ys) - min(ys) < 1.2 * pitch_y:
        return [pts]    # um frame normal, mesmo que encoste na celula vizinha
    r0, r1 = int(min(ys) // pitch_y), int(max(ys) // pitch_y)
    cuts = []
    for r in range(r0, r1):
        lo, hi = int((r + 0.5) * pitch_y), int((r + 1.5) * pitch_y)
        thickness = {y: 0 for y in range(lo, hi + 1)}
        for _, y in pts:
            if lo <= y <= hi:
                thickness[y] += 1
        cuts.append(min(thickness, key=thickness.get))
    bounds = [min(ys)] + cuts + [max(ys) + 1]
    parts = [{p for p in pts if a <= p[1] < b} for a, b in zip(bounds, bounds[1:])]
    return [part for part in parts if len(part) >= MIN_AREA]


SMOKE_LUM = 130         # linha mais clara que isto, em media, e fumaca (capacete e cabeca ficam abaixo de 115)
SMOKE_ROWS = 12         # a fumaca presa ao corpo mora nas primeiras/ultimas linhas
SMOKE_ROWS_MIN = 3      # menos linhas claras que isto e so um brilho
SMOKE_MAX = 300         # pixels; fumaca presa ao corpo nunca passa disto


def strip_smoke(pts, pixels):
    """Tira a fumaca cinza que o Gemini deixa colada acima da cabeca ou abaixo
    dos pes. Ela nao tem pescoco fino para cortar, mas e clara: nas SMOKE_ROWS
    linhas de cima (e de baixo), se SMOKE_ROWS_MIN ou mais tem luminancia
    media acima de SMOKE_LUM, tudo ate a ultima delas e fumaca e sai."""
    rows = {}
    for x, y in pts:
        rows.setdefault(y, []).append((x, y))

    def lum(y):
        ps = rows[y]
        return sum(0.3 * pixels[x, yy][0] + 0.59 * pixels[x, yy][1] + 0.11 * pixels[x, yy][2] for x, yy in ps) / len(ps)

    ys = sorted(rows)
    for edge in (ys[:SMOKE_ROWS], list(reversed(ys))[:SMOKE_ROWS]):
        bright = [i for i, y in enumerate(edge) if lum(y) > SMOKE_LUM]
        if len(bright) >= SMOKE_ROWS_MIN:
            smoke = {p for y in edge[:max(bright) + 1] for p in rows[y]}
            if len(smoke) < SMOKE_MAX:
                pts = pts - smoke
    return pts


def row_centers(cells):
    """Centro vertical de cada linha: mediana, entre as celulas da linha, do
    centro vertical do frame. Ancorar nisso deixa o corpo centrado na celula
    em toda linha, e a mediana ignora a fumaca presa a um ou outro frame."""
    centers = {}
    for r in range(GRID_ROWS):
        mids = []
        for (row, _), pts in cells.items():
            if row == r:
                ys = [p[1] for p in pts]
                mids.append((min(ys) + max(ys)) / 2.0)
        if mids:
            mids.sort()
            centers[r] = mids[len(mids) // 2]
    return centers


def pack(src_rel, dst_rel, animations):
    src = Image.open(ROOT / src_rel).convert("RGBA")
    w, h = src.size
    pitch_x, pitch_y = w / GRID_COLS, h / GRID_ROWS
    alpha = src.split()[3].load()
    pixels = src.load()

    cells = {}
    for comp in components(alpha, w, h):
        for part in split_rows(comp, pitch_y):
            part = strip_smoke(part, pixels)
            cx = sum(p[0] for p in part) / len(part)
            cy = sum(p[1] for p in part) / len(part)
            key = (int(cy // pitch_y), int(cx // pitch_x))
            cells.setdefault(key, set()).update(part)

    centers = row_centers(cells)
    max_frames = max(len(cols) for _, _, cols, _ in animations)
    dst = Image.new("RGBA", (max_frames * CELL_W, len(animations) * CELL_H), (0, 0, 0, 0))
    out = dst.load()

    print(src_rel)
    for out_row, (name, grid_row, cols, mirror) in enumerate(animations):
        for out_col, grid_col in enumerate(cols):
            pts = cells.get((grid_row, grid_col))
            if not pts:
                raise SystemExit(f"{name}: nenhum frame na celula ({grid_row}, {grid_col})")
            ax = (grid_col + 0.5) * pitch_x
            ay = centers[grid_row]
            # floor(v + 0.5), e nao round(): com o centro em meio pixel,
            # round() arredonda para o par e funde linhas vizinhas.
            dx = int(math.floor(-ax + 0.5))
            dxm = int(math.floor(ax + 0.5))      # espelhado em volta do centro
            dy = int(math.floor(-ay + 0.5))
            for x, y in pts:
                ox = out_col * CELL_W + CELL_W // 2 + (dxm - x if mirror else x + dx)
                oy = out_row * CELL_H + CELL_H // 2 + y + dy
                if not (out_col * CELL_W <= ox < (out_col + 1) * CELL_W and out_row * CELL_H <= oy < (out_row + 1) * CELL_H):
                    raise SystemExit(f"{name} frame {out_col}: pixel ({x}, {y}) nao cabe na celula")
                out[ox, oy] = pixels[x, y]
        print(f"  linha {out_row}: {name:<20} {len(cols)} frames" + (" (espelhada)" if mirror else ""))

    dst.save(ROOT / dst_rel)
    print(f"  -> {dst_rel}: {dst.size[0]}x{dst.size[1]}, celulas {CELL_W}x{CELL_H}")


def main():
    for src, dst, animations in SHEETS:
        pack(src, dst, animations)


if __name__ == "__main__":
    main()
