"""Preview geometry: edge snapping, aspect-locked resizing and overlap removal.

All rectangles are ``(x, y, w, h)`` tuples in Cocoa screen coordinates
(origin at the bottom-left).
"""


def _near(a0, a1, b0, b1, dist):
    """Return whether intervals [a0, a1] and [b0, b1] overlap or are within ``dist``."""
    return a0 < b1 + dist and b0 < a1 + dist


def _targets(rect, others, screens, dist):
    """Collect the x and y edges ``rect`` may snap to.

    Other previews only count when they are close on the perpendicular axis;
    screen edges always count.
    """
    x, y, w, h = rect
    xs, ys = [], []
    for ox, oy, ow, oh in others:
        if _near(y, y + h, oy, oy + oh, dist):
            xs += [ox, ox + ow]
        if _near(x, x + w, ox, ox + ow, dist):
            ys += [oy, oy + oh]
    for sx, sy, sw, sh in screens:
        xs += [sx, sx + sw]
        ys += [sy, sy + sh]
    return xs, ys


def _best_delta(edges, targets, dist):
    """Return the smallest offset (within ``dist``) that aligns any edge to any target, or 0."""
    best, best_abs = 0, dist + 1
    for edge in edges:
        for target in targets:
            d = target - edge
            if abs(d) <= dist and abs(d) < best_abs:
                best, best_abs = d, abs(d)
    return best


def snap_move(rect, others, screens, dist):
    """Snap a moved rectangle to nearby preview and screen edges.

    :param rect: the rectangle after the raw mouse movement.
    :param others: rectangles of the other visible previews.
    :param screens: visible frames of all screens.
    :param dist: snap distance in points; 0 disables snapping.
    :return: the snapped rectangle.
    """
    if dist <= 0:
        return rect
    x, y, w, h = rect
    xs, ys = _targets(rect, others, screens, dist)
    return (x + _best_delta([x, x + w], xs, dist),
            y + _best_delta([y, y + h], ys, dist), w, h)


def _anchor(start, edges, new_w, aspect):
    """Resize ``start`` to ``new_w`` keeping the edges opposite to the dragged ones fixed."""
    x, y, w, h = start
    new_h = new_w * aspect
    nx = x + w - new_w if "l" in edges else x
    ny = y if "t" in edges else y + h - new_h
    return nx, ny, new_w, new_h


def resize_rect(start, edges, dx, dy, aspect, others, screens, dist, min_w, max_w):
    """Resize a preview by dragging one edge or corner, keeping its aspect ratio.

    :param start: rectangle at the beginning of the drag.
    :param edges: set of dragged edges, a subset of ``{"l", "r", "t", "b"}``.
    :param dx: horizontal mouse movement since the drag started.
    :param dy: vertical mouse movement since the drag started.
    :param aspect: height / width ratio to keep.
    :param others: rectangles of the other visible previews.
    :param screens: visible frames of all screens.
    :param dist: snap distance in points; 0 disables snapping.
    :param min_w: minimum width.
    :param max_w: maximum width.
    :return: the new rectangle, rounded to whole points.
    """
    x, y, w, h = start
    horizontal = "l" in edges or "r" in edges

    def clamp(value):
        return max(min_w, min(max_w, value))

    if horizontal:
        new_w = w + (dx if "r" in edges else -dx)
    else:
        new_w = (h + (dy if "t" in edges else -dy)) / aspect
    new_w = clamp(new_w)
    rect = _anchor(start, edges, new_w, aspect)

    if dist > 0:
        rx, ry, rw, rh = rect
        xs, ys = _targets(rect, others, screens, dist)
        if horizontal:
            edge = rx + rw if "r" in edges else rx
            d = _best_delta([edge], xs, dist)
            new_w += d if "r" in edges else -d
        else:
            edge = ry + rh if "t" in edges else ry
            d = _best_delta([edge], ys, dist)
            new_w = (rh + (d if "t" in edges else -d)) / aspect
        rect = _anchor(start, edges, clamp(new_w), aspect)

    return tuple(round(v) for v in rect)


def _overlaps(a, b):
    """Return whether two rectangles overlap by more than half a point."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (min(ax + aw, bx + bw) - max(ax, bx) > 0.5
            and min(ay + ah, by + bh) - max(ay, by) > 0.5)


def resolve_overlaps(rect, others, max_steps=20):
    """Push ``rect`` the minimum distance needed to stop covering other previews.

    :param rect: the rectangle to fix.
    :param others: rectangles of the other visible previews.
    :param max_steps: safety limit on the number of push iterations.
    :return: the adjusted rectangle.
    """
    x, y, w, h = rect
    for _ in range(max_steps):
        hit = next((o for o in others if _overlaps((x, y, w, h), o)), None)
        if hit is None:
            break
        ox, oy, ow, oh = hit
        moves = [(ox - (x + w), 0), (ox + ow - x, 0), (0, oy - (y + h)), (0, oy + oh - y)]
        dx, dy = min(moves, key=lambda m: abs(m[0]) + abs(m[1]))
        x += dx
        y += dy
    return x, y, w, h