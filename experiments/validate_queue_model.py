"""
Проверка очередной модели двух движков на открытом пуассоновском потоке.

Модель, которую проверяет этот замер. Цикл событий выполняет вычислительную
часть каждого запроса неделимо и по очереди, то есть по отношению к
вычислениям ведёт себя как одноканальная система M/G/1 без вытеснения.
Лёгкое обращение, пришедшее в случайный момент, ждёт окончания текущего
вычисления и всех, стоящих перед ним, и средняя задержка даётся формулой
Поллачека — Хинчина:

    E[W] = lambda * E[B^2] / (2 * (1 - rho)),   rho = lambda * E[B],

где B — время, на которое запрос занимает цикл событий. Важна не средняя
стоимость запроса, а её второй момент: при одной и той же загрузке редкие
тяжёлые запросы вредят соседям сильнее частых лёгких.

Поток на запрос ведёт себя иначе. Вычисление, освобождающее GIL (PBKDF2),
идёт параллельно на другом ядре, и задержка лёгкого обращения от
распределения стоимостей почти не зависит. Вычисление, удерживающее GIL
(сортировка списка), делит интерпретатор с остальными потоками порциями по
интервалу переключения, и защита потоком пропадает.

Схема замера. На движок напрямую, минуя шлюз, подаётся пуассоновский поток
калибровочных вычислений заданного размера с интенсивностью, при которой
загрузка равна rho, и независимый пуассоновский поток зондов GET /health.
Зонд не выполняет работы, поэтому его задержка сверх задержки на
ненагруженном движке и есть ожидание в очереди к циклу событий или к
интерпретатору. Предсказание считается по размерам, измеренным заранее на
ненагруженном движке, без подгонки под результат.

Запуск (движки поднимаются и гасятся самим скриптом):

    python experiments/validate_queue_model.py
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RESULTS_PATH = DATA_DIR / "queue_model_validation.json"

ENGINES = {
    "async": ("workers/async_worker.py", "http://127.0.0.1:8202"),
    "sync": ("workers/sync_worker.py", "http://127.0.0.1:8201"),
}

PROBE_RATE = float(os.environ.get("PROBE_RATE", "10"))   # зондов в секунду
MIN_JOBS = int(os.environ.get("MIN_JOBS", "250"))         # вычислений на точку
MIN_SECONDS = float(os.environ.get("MIN_SECONDS", "40"))
MAX_SECONDS = float(os.environ.get("MAX_SECONDS", "75"))
WARMUP_SECONDS = 3.0
SEED = 20261101


def start_engine(name: str) -> subprocess.Popen:
    script, url = ENGINES[name]
    proc = subprocess.Popen(
        [sys.executable, str(BASE_DIR / script)], cwd=BASE_DIR,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            if httpx.get(f"{url}/health", timeout=1).status_code == 200:
                return proc
        except httpx.HTTPError:
            pass
        time.sleep(0.3)
    proc.kill()
    raise RuntimeError(f"движок {name} не поднялся")


def stop_engine(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


async def one_job(client: httpx.AsyncClient, url: str, endpoint: str,
                  param: int) -> float:
    start = time.perf_counter()
    resp = await client.post(f"{url}/process",
                             json={"endpoint": endpoint, "param": param})
    resp.raise_for_status()
    return (time.perf_counter() - start) * 1000


async def one_probe(client: httpx.AsyncClient, url: str) -> float:
    start = time.perf_counter()
    resp = await client.get(f"{url}/health")
    resp.raise_for_status()
    return (time.perf_counter() - start) * 1000


async def baseline_probe(client: httpx.AsyncClient, url: str) -> float:
    """Задержка зонда на ненагруженном движке, медиана."""
    values = []
    for _ in range(60):
        values.append(await one_probe(client, url))
        await asyncio.sleep(0.02)
    return statistics.median(values[10:])


async def calibrate(client: httpx.AsyncClient, url: str, endpoint: str,
                    param: int, probe_ms: float) -> float:
    """
    Время, на которое одно вычисление занимает ненагруженный движок.

    Из полного времени ответа вычитается время пустого обращения: в нём
    сетевой обмен и разбор запроса, которые есть и у зонда.
    """
    values = []
    for _ in range(12):
        values.append(await one_job(client, url, endpoint, param))
        await asyncio.sleep(0.05)
    return max(statistics.median(values[2:]) - probe_ms, 0.1)


async def run_point(client: httpx.AsyncClient, url: str,
                    classes: list[tuple[str, int, float, float]],
                    rho: float, seed: int) -> dict:
    """
    Один режим: смесь классов вычислений с суммарной загрузкой rho.

    classes — список (маршрут, параметр, доля по числу, размер в мс).
    """
    mean_b = sum(share * size for _, _, share, size in classes)
    second = sum(share * size * size for _, _, share, size in classes)
    lam = rho / mean_b * 1000.0                      # вычислений в секунду
    duration = min(max(MIN_JOBS / lam, MIN_SECONDS), MAX_SECONDS)
    rng = random.Random(seed)

    # Расписание прихода заранее: оба потока пуассоновские и независимые.
    events: list[tuple[float, str, int]] = []
    t = 0.0
    while t < duration + WARMUP_SECONDS:
        t += rng.expovariate(lam)
        u, acc = rng.random(), 0.0
        for idx, (_, _, share, _) in enumerate(classes):
            acc += share
            if u <= acc:
                break
        events.append((t, "job", idx))
    t = 0.0
    while t < duration + WARMUP_SECONDS:
        t += rng.expovariate(PROBE_RATE)
        events.append((t, "probe", -1))
    events.sort()

    probes: list[float] = []
    tasks = []
    origin = time.perf_counter()

    async def probe_task(sent_at: float) -> None:
        value = await one_probe(client, url)
        if sent_at >= WARMUP_SECONDS:
            probes.append(value)

    for at, kind, idx in events:
        delay = at - (time.perf_counter() - origin)
        if delay > 0:
            await asyncio.sleep(delay)
        if kind == "job":
            endpoint, param = classes[idx][0], classes[idx][1]
            tasks.append(asyncio.create_task(
                one_job(client, url, endpoint, param)))
        else:
            tasks.append(asyncio.create_task(probe_task(at)))
    await asyncio.gather(*tasks, return_exceptions=True)

    return {
        "lambda_per_s": round(lam, 3),
        "rho": rho,
        "mean_b_ms": round(mean_b, 2),
        "second_moment_ms2": round(second, 1),
        "residual_ms": round(second / (2 * mean_b), 2),
        "duration_s": round(duration, 1),
        "probe_latencies": probes,
    }


def summarize(point: dict, probe_ms: float) -> dict:
    values = sorted(point.pop("probe_latencies"))
    delays = [max(v - probe_ms, 0.0) for v in values]
    n = len(delays)
    mean = statistics.mean(delays)
    std = statistics.stdev(delays) if n > 1 else 0.0
    rho, lam = point["rho"], point["lambda_per_s"] / 1000.0
    predicted = lam * point["second_moment_ms2"] / (2 * (1 - rho))
    point.update({
        "n_probes": n,
        "probe_delay_mean_ms": round(mean, 2),
        "probe_delay_ci95_ms": round(1.96 * std / math.sqrt(n), 2) if n else None,
        "probe_delay_p95_ms": round(delays[min(int(n * 0.95), n - 1)], 1),
        "pk_predicted_wait_ms": round(predicted, 2),
    })
    return point


# Размеры вычислений: параметр калибровочного маршрута подобран так, чтобы
# на ненагруженном асинхронном движке получилось около 20, 60 и 160 мс.
HASH_SIZES = {"small": 100, "medium": 300, "large": 800}
SORT_SIZES = {"small": 60, "large": 400}
RHOS = [0.2, 0.4, 0.6]


async def measure_engine(name: str) -> dict:
    url = ENGINES[name][1]
    proc = start_engine(name)
    out: dict = {"engine": name, "points": []}
    try:
        limits = httpx.Limits(max_connections=2000,
                              max_keepalive_connections=2000)
        async with httpx.AsyncClient(limits=limits, timeout=120) as client:
            probe_ms = await baseline_probe(client, url)
            out["probe_baseline_ms"] = round(probe_ms, 3)

            sizes: dict[str, float] = {}
            for label, param in HASH_SIZES.items():
                sizes[f"hash_{label}"] = await calibrate(
                    client, url, "/calib/hash", param, probe_ms)
            # Однородный класс со средним, равным среднему бимодальной
            # смеси ниже: сравнение при равных загрузке и средней стоимости.
            mix_mean = 0.9 * sizes["hash_small"] + 0.1 * sizes["hash_large"]
            equal_param = int(round(HASH_SIZES["small"] * mix_mean
                                    / sizes["hash_small"]))
            sizes["hash_equal"] = await calibrate(
                client, url, "/calib/hash", equal_param, probe_ms)
            for label, param in SORT_SIZES.items():
                sizes[f"sort_{label}"] = await calibrate(
                    client, url, "/calib/sort", param, probe_ms)
            out["calibrated_ms"] = {k: round(v, 2) for k, v in sizes.items()}
            out["equal_param_kiter"] = equal_param
            print(f"[{name}] зонд {probe_ms:.2f} мс, размеры "
                  + ", ".join(f"{k}={v:.1f}" for k, v in sizes.items()),
                  flush=True)

            plan: list[tuple[str, list, float]] = []
            for label, param in HASH_SIZES.items():
                for rho in RHOS:
                    plan.append((f"hash_{label}", [(
                        "/calib/hash", param, 1.0, sizes[f"hash_{label}"])],
                        rho))
            for rho in (0.3, 0.5):
                plan.append(("hash_bimodal", [
                    ("/calib/hash", HASH_SIZES["small"], 0.9,
                     sizes["hash_small"]),
                    ("/calib/hash", HASH_SIZES["large"], 0.1,
                     sizes["hash_large"])], rho))
                plan.append(("hash_equal", [(
                    "/calib/hash", equal_param, 1.0, sizes["hash_equal"])],
                    rho))
            for label, param in SORT_SIZES.items():
                plan.append((f"sort_{label}", [(
                    "/calib/sort", param, 1.0, sizes[f"sort_{label}"])], 0.4))

            for i, (scenario, classes, rho) in enumerate(plan):
                point = await run_point(client, url, classes, rho,
                                        seed=SEED + 97 * i)
                point = summarize(point, probe_ms)
                point["scenario"] = scenario
                out["points"].append(point)
                print(f"[{name}] {scenario:<13} rho={rho:.1f} "
                      f"E[B]={point['mean_b_ms']:6.1f} "
                      f"предсказано {point['pk_predicted_wait_ms']:7.1f} "
                      f"измерено {point['probe_delay_mean_ms']:7.1f} "
                      f"±{point['probe_delay_ci95_ms']:.1f} мс "
                      f"(n={point['n_probes']})", flush=True)
                await asyncio.sleep(1.0)
    finally:
        stop_engine(proc)
    return out


async def main() -> None:
    sys.path.insert(0, str(BASE_DIR))
    from core.workload import ensure_database

    ensure_database()
    results = {"probe_rate_per_s": PROBE_RATE, "seed": SEED,
               "cpu_count": os.cpu_count(), "engines": {}}
    for name in ("async", "sync"):
        results["engines"][name] = await measure_engine(name)
        RESULTS_PATH.write_text(json.dumps(results, indent=2,
                                           ensure_ascii=False),
                                encoding="utf-8")
    print(f"Сохранено: {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
