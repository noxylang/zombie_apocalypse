"""tools/pack_sheet.py — empacota a sheet do Gemini numa grade regular.

O Gemini entrega images/shooter.png como uma grade de 14 x 8 celulas de
tamanho fracionario, com frames de larguras diferentes, o flash do cano
invadindo a celula vizinha e varias linhas misturando vista frontal e
lateral. Este script recorta so as linhas coerentes e escreve
images/shooter_sheet.png: uma animacao por linha, celulas de CELL_W x CELL_H,
corpo sempre na mesma posicao da celula. src/anim.nx conhece esse layout.

Cada frame e um componente conexo do canal alpha, associado a celula da grade
que contem o seu centroide. O unico componente que atravessa duas linhas (uma
fumaca liga um frame ao de baixo) e cortado na linha de menor espessura.

    python tools/pack_sheet.py          # a partir da raiz do projeto
"""
import math
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "images" / "shooter.png"
DST = ROOT / "images" / "shooter_sheet.png"

GRID_COLS, GRID_ROWS = 14, 8
CELL_W, CELL_H = 80, 64
ALPHA_MIN = 20          # abaixo disso e fundo
MIN_AREA = 6            # pontos soltos menores que isso sao lixo

# (nome, linha na grade de origem, colunas na grade de origem, espelhar)
# Toda linha de lado sai virada para a direita. A caminhada lateral usa so os
# tres frames de vista lateral da linha 7 da direita (o 5 repetido fecha o
# ciclo passo largo / pernas juntas): as outras caminhadas da sheet misturam
# tronco de costas e de frente em 3/4, e a alternancia parecia um giro. O idle
# lateral e o frame parado da caminhada da esquerda, espelhado.
ANIMATIONS = [
    ("idle_down",  0, range(0, 4),      False),
    ("walk_down",  1, range(0, 6),      False),
    ("walk_up",    1, range(7, 14),     False),
    ("walk_side",  6, [11, 12, 13, 12], False),
    ("shoot_side", 2, range(7, 14),     False),
    ("death",      7, range(7, 14),     False),
    ("idle_side",  4, [0],              True),
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
    """Se o componente atravessa duas linhas da grade, corta-o na linha (y)
    mais fina entre os dois centros; senao devolve-o inteiro."""
    ys = [p[1] for p in pts]
    r0, r1 = int(min(ys) // pitch_y), int(max(ys) // pitch_y)
    if max(ys) - min(ys) < 1.2 * pitch_y:
        return [pts]    # um frame normal, mesmo que encoste na celula vizinha
    lo, hi = int((r0 + 0.5) * pitch_y), int((r1 + 0.5) * pitch_y)
    thickness = {y: 0 for y in range(lo, hi + 1)}
    for _, y in pts:
        if lo <= y <= hi:
            thickness[y] += 1
    cut = min(thickness, key=thickness.get)
    halves = [{p for p in pts if p[1] < cut}, {p for p in pts if p[1] >= cut}]
    return [half for half in halves if half]


def row_centers(alpha, w, h, pitch_y):
    """Centro vertical real de cada linha: a faixa de pixels opacos em volta do
    centro da celula, medida so na metade esquerda, onde as linhas nao se
    tocam. Anchorar nisso deixa o corpo centrado na celula em toda linha."""
    def opaque_row(y):
        return 0 <= y < h and any(alpha[x, y] > ALPHA_MIN for x in range(0, w // 2))

    centers = []
    for r in range(GRID_ROWS):
        top = bottom = int((r + 0.5) * pitch_y)
        while opaque_row(top - 1):
            top -= 1
        while opaque_row(bottom + 1):
            bottom += 1
        centers.append((top + bottom) / 2.0)
    return centers


def main():
    src = Image.open(SRC).convert("RGBA")
    w, h = src.size
    pitch_x, pitch_y = w / GRID_COLS, h / GRID_ROWS
    alpha = src.split()[3].load()
    pixels = src.load()

    cells = {}
    for comp in components(alpha, w, h):
        for part in split_rows(comp, pitch_y):
            cx = sum(p[0] for p in part) / len(part)
            cy = sum(p[1] for p in part) / len(part)
            key = (int(cy // pitch_y), int(cx // pitch_x))
            cells.setdefault(key, set()).update(part)

    centers = row_centers(alpha, w, h, pitch_y)
    max_frames = max(len(cols) for _, _, cols, _ in ANIMATIONS)
    dst = Image.new("RGBA", (max_frames * CELL_W, len(ANIMATIONS) * CELL_H), (0, 0, 0, 0))
    out = dst.load()

    for out_row, (name, grid_row, cols, mirror) in enumerate(ANIMATIONS):
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
        print(f"linha {out_row}: {name:<10} {len(cols)} frames" + (" (espelhada)" if mirror else ""))

    dst.save(DST)
    print(f"{DST.relative_to(ROOT)}: {dst.size[0]}x{dst.size[1]}, celulas {CELL_W}x{CELL_H}")


if __name__ == "__main__":
    main()
