from typing import Any


def compute_deltas(times: list[int]) -> list[int]:
    if len(times) < 2:
        return [0] * len(times)

    deltas: list[int] = []
    for i in range(len(times)):
        if i == 0:
            delta = times[1] - times[0]
        else:
            delta = times[i] - times[i - 1]

        if delta < 0:
            delta = 0

        deltas.append(delta)

    return deltas


def rolling_mean(values: list[float], window: int) -> list[float]:
    if not values:
        return []

    result: list[float] = []
    running_sum = 0.0

    for i, value in enumerate(values):
        running_sum += value

        if i >= window:
            running_sum -= values[i - window]

        current_window = min(i + 1, window)
        result.append(running_sum / current_window)

    return result


def compute_power_metrics(
    watts_stream: list[Any],
    avg_power: float | None,
    ftp_watts: float | None,
    elapsed_time_s: int | None,
) -> dict[str, float | None]:
    normalized_power = None
    intensity_factor = None
    variability_index = None
    tss = None

    if watts_stream and ftp_watts and ftp_watts > 0:
        watts_values = [float(v) if v is not None else 0.0 for v in watts_stream]
        rolling_30s = rolling_mean(watts_values, 30)

        if rolling_30s:
            fourth_power_mean = sum(v ** 4 for v in rolling_30s) / len(rolling_30s)
            normalized_power = fourth_power_mean ** 0.25

            if avg_power and avg_power > 0:
                variability_index = normalized_power / avg_power

            intensity_factor = normalized_power / ftp_watts

            if elapsed_time_s and elapsed_time_s > 0:
                tss = (elapsed_time_s * normalized_power * intensity_factor) / (ftp_watts * 3600) * 100

    return {
        "normalized_power": normalized_power,
        "intensity_factor": intensity_factor,
        "variability_index": variability_index,
        "tss": tss,
    }


def compute_power_zones(
    watts_stream: list[Any],
    deltas: list[int],
    power_z1_upper: float,
    power_z2_upper: float,
    power_z3_upper: float,
    power_z4_upper: float,
    power_z5_upper: float,
    power_z6_upper: float,
) -> dict[str, int]:
    power_zones = {
        "z1": 0,
        "z2": 0,
        "z3": 0,
        "z4": 0,
        "z5": 0,
        "z6": 0,
        "z7": 0,
    }

    if not watts_stream:
        return power_zones

    for i in range(min(len(watts_stream), len(deltas))):
        value = watts_stream[i]
        delta = deltas[i]

        if value is None:
            continue

        if value <= power_z1_upper:
            power_zones["z1"] += delta
        elif value <= power_z2_upper:
            power_zones["z2"] += delta
        elif value <= power_z3_upper:
            power_zones["z3"] += delta
        elif value <= power_z4_upper:
            power_zones["z4"] += delta
        elif value <= power_z5_upper:
            power_zones["z5"] += delta
        elif value <= power_z6_upper:
            power_zones["z6"] += delta
        else:
            power_zones["z7"] += delta

    return power_zones


def compute_hr_zones(
    hr_stream: list[Any],
    deltas: list[int],
    hr_z1_upper: int | None,
    hr_z2_upper: int | None,
    hr_z3_upper: int | None,
    hr_z4_upper: int | None,
) -> dict[str, int]:
    hr_zones = {
        "z1": 0,
        "z2": 0,
        "z3": 0,
        "z4": 0,
        "z5": 0,
    }

    if not hr_stream:
        return hr_zones

    for i in range(min(len(hr_stream), len(deltas))):
        value = hr_stream[i]
        delta = deltas[i]

        if value is None:
            continue

        if hr_z1_upper is not None and value <= hr_z1_upper:
            hr_zones["z1"] += delta
        elif hr_z2_upper is not None and value <= hr_z2_upper:
            hr_zones["z2"] += delta
        elif hr_z3_upper is not None and value <= hr_z3_upper:
            hr_zones["z3"] += delta
        elif hr_z4_upper is not None and value <= hr_z4_upper:
            hr_zones["z4"] += delta
        else:
            hr_zones["z5"] += delta

    return hr_zones
