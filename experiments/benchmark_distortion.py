"""
Искажение величины оценки при сохранённом порядке.

Перекрёстный замер (`split_*`) показал, что исход определяется оценкой,
которой взвешена очередь, а не оценкой, по которой принимается решение о
допуске. Но правило и модель различаются сразу многим, и тот замер не
отвечает, что именно в оценке нужно для взвешивания.

Здесь различие сведено к одному свойству. Берётся одна оценка (степенной
закон), и её значения заменяются на ref * (b / ref)^gamma. Порядок запросов
сохраняется точно, порог допуска ref переходит сам в себя, поэтому
решения о допуске одинаковы при всех gamma. Меняется только масштаб, в
котором складывается и сравнивается занятость движков. Если исход при
этом меняется, взвешиванию нужна верная величина; если нет — хватило бы
порядка.

    python experiments/benchmark_distortion.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("REPEATS", "5")
os.environ.setdefault("REQUESTS", "600")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experiments.benchmark_budget import (  # noqa: E402
    CONCURRENCY, REPEATS, REQUESTS, measure,
)

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_PATH = BASE_DIR / "data" / "magnitude_distortion.json"

SOURCE = os.environ.get("SOURCE", "power")
BUDGET = int(os.environ.get("BUDGET", "30"))
GAMMAS = [float(x) for x in
          os.environ.get("GAMMAS", "0.5,0.75,1.0,1.5,2.0").split(",")]


async def main() -> None:
    results = {"source": SOURCE, "budget_ms": BUDGET,
               "concurrency": CONCURRENCY, "requests": REQUESTS,
               "repeats": REPEATS, "points": {}}
    print(f"Оценка {SOURCE}, порог {BUDGET} мс, конкурентность "
          f"{CONCURRENCY}, {REPEATS} x {REQUESTS}\n")
    for gamma in GAMMAS:
        policy = f"distort_{SOURCE}_{gamma}_{BUDGET}"
        res = await measure(policy)
        results["points"][str(gamma)] = res
        print(f"gamma={gamma:<5} rps {res['rps']:6.1f} ±{res['rps_std']:<4.1f}"
              f" лёгкие p95 {res['light_p95']:6.0f} мс,"
              f" >200 мс {res['light_over_budget_pct']:5.1f} %", flush=True)
        RESULTS_PATH.write_text(json.dumps(results, indent=2,
                                           ensure_ascii=False),
                                encoding="utf-8")
    print(f"\nСохранено: {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
