from __future__ import annotations


def piecewise_linear_score(
    value: float | int | None,
    breakpoints: tuple[tuple[float, float], ...] | list[tuple[float, float]],
) -> float:
    if value is None or not breakpoints:
        return 0.0
    x = float(value)
    points = sorted((float(px), float(py)) for px, py in breakpoints)
    if x <= points[0][0]:
        return _clamp_score(points[0][1])
    if x >= points[-1][0]:
        return _clamp_score(points[-1][1])
    for index in range(1, len(points)):
        left_x, left_y = points[index - 1]
        right_x, right_y = points[index]
        if left_x <= x <= right_x:
            if right_x == left_x:
                return _clamp_score(right_y)
            ratio = (x - left_x) / (right_x - left_x)
            return _clamp_score(left_y + (right_y - left_y) * ratio)
    return _clamp_score(points[-1][1])


def composite_score(scores_with_weights: dict[str, tuple[float, float]]) -> float:
    total_weight = 0.0
    weighted_sum = 0.0
    for score, weight in scores_with_weights.values():
        weight_value = float(weight)
        if weight_value <= 0.0:
            continue
        total_weight += weight_value
        weighted_sum += _clamp_score(score) * weight_value
    if total_weight <= 0.0:
        return 0.0
    return _clamp_score(weighted_sum / total_weight)


def _clamp_score(value: float | int) -> float:
    return max(0.0, min(100.0, float(value)))
