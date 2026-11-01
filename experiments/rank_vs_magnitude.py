"""
Две меры качества оценки блокировки: порядок и величина.

Решение о допуске в асинхронный движок сравнивает оценку с порогом, и его
исход не меняется при любом строго возрастающем преобразовании оценки,
если порог преобразовать так же. Поэтому для допуска важно лишь, верно ли
оценка упорядочивает запросы. Взвешивание очереди складывает оценки
нескольких запросов и сравнивает суммы между движками, и здесь нужна
верная величина в миллисекундах.

На отложенной выборке (значения параметра в ней при настройке не
встречались) для каждой оценки считаются:

  * медианная относительная ошибка — мера величины, как в
    `train_cost_model.py`;
  * тау-b Кендалла между оценкой и измеренной блокировкой асинхронного
    движка — мера порядка;
  * площадь под ROC-кривой для разделения запросов на безопасные и
    опасные для цикла событий при пороге 30 мс — та же мера порядка,
    но там, где она нужна допуску;
  * медианная относительная ошибка суммы оценок по случайным наборам из
    восьми запросов одного движка — мера величины там, где она нужна
    взвешиванию очереди.

    python experiments/rank_vs_magnitude.py
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scipy.stats import kendalltau  # noqa: E402

from core.cost_model import EndpointMeanCost, LinearParamCost  # noqa: E402
from core.predictor import (  # noqa: E402
    HOLDOUT_PATH_DEFAULT, NeuralCost, PowerLawCost, load_samples,
)

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_PATH = BASE_DIR / "data" / "rank_vs_magnitude.json"

THRESHOLD_MS = 30.0
BATCH = 8
DRAWS = 20000
SEED = 1101


def auc(scores_neg: list[float], scores_pos: list[float]) -> float:
    """Вероятность того, что опасный запрос оценён выше безопасного."""
    wins = 0.0
    for p in scores_pos:
        for n in scores_neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(scores_pos) * len(scores_neg))


def main() -> None:
    import torch

    torch.set_num_threads(1)
    train = load_samples()
    holdout = load_samples(HOLDOUT_PATH_DEFAULT)
    estimators = {
        "endpoint_mean": EndpointMeanCost(train),
        "linear_param": LinearParamCost(train),
        "power_law": PowerLawCost.load(),
        "neural": NeuralCost.load(),
    }
    rng = random.Random(SEED)
    by_worker: dict[str, list[dict]] = {}
    for row in holdout:
        by_worker.setdefault(row["worker"], []).append(row)
    draws = {w: [rng.sample(rows, BATCH) for _ in range(DRAWS)]
             for w, rows in by_worker.items()}

    results = {"threshold_ms": THRESHOLD_MS, "batch": BATCH,
               "n_holdout": len(holdout),
               "n_async": len(by_worker.get("async", [])), "estimators": {}}
    print(f"{'оценка':<15}{'MdRE':>8}{'тау':>8}{'AUC':>8}{'ошибка суммы':>15}")
    for name, est in estimators.items():
        pred = {id(r): est.blocking(r["endpoint"], r.get("param"), r["worker"])
                for r in holdout}
        errors = [abs(pred[id(r)] - r["block_ms"]) / max(r["block_ms"], 1.0)
                  * 100 for r in holdout]
        rows_async = by_worker["async"]
        truth = [r["block_ms"] for r in rows_async]
        guess = [pred[id(r)] for r in rows_async]
        tau = kendalltau(guess, truth, variant="b").statistic
        neg = [pred[id(r)] for r in rows_async if r["block_ms"] <= THRESHOLD_MS]
        pos = [pred[id(r)] for r in rows_async if r["block_ms"] > THRESHOLD_MS]
        roc = auc(neg, pos)
        sum_errors = []
        for worker, sets in draws.items():
            for batch in sets:
                true_sum = sum(r["block_ms"] for r in batch)
                est_sum = sum(pred[id(r)] for r in batch)
                sum_errors.append(abs(est_sum - true_sum) / true_sum * 100)
        entry = {
            "median_ape_blocking_pct": round(statistics.median(errors), 1),
            "kendall_tau_b_async": round(float(tau), 3),
            "auc_async_threshold": round(roc, 3),
            "median_batch_sum_error_pct": round(statistics.median(sum_errors), 1),
            "n_safe": len(neg), "n_unsafe": len(pos),
        }
        results["estimators"][name] = entry
        print(f"{name:<15}{entry['median_ape_blocking_pct']:>7.1f}%"
              f"{entry['kendall_tau_b_async']:>8.3f}"
              f"{entry['auc_async_threshold']:>8.3f}"
              f"{entry['median_batch_sum_error_pct']:>14.1f}%")
    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    print(f"Сохранено: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
