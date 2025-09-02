"""Spatial grid for efficient neighbor queries in XZ-plane."""

def _cell_index(x, z, cell):
    try:
        ix = int(x // cell)
        iz = int(z // cell)
        return ix, iz
    except Exception:
        return 0, 0


def build_grid(state, cell_size_m):
    grid = {"_cell": float(cell_size_m)}
    n = state.car_count()
    for i in range(n):
        p = state.pos(i)
        if p is None:
            continue
        ix, iz = _cell_index(p[0], p[2], cell_size_m)
        key = (ix, iz)
        bucket = grid.get(key)
        if bucket is None:
            bucket = []
            grid[key] = bucket
        bucket.append(i)
    return grid


def neighbors_of(car_id, pos, grid):
    if pos is None:
        return []
    # own cell + 8 adjacent
    cell = grid.get("_cell", 1.0)
    ix, iz = _cell_index(pos[0], pos[2], cell)
    out = []
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            bucket = grid.get((ix + dx, iz + dz))
            if bucket:
                for j in bucket:
                    if j != car_id:
                        out.append(j)
    return out
