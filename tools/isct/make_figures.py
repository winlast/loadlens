"""Figures for the ISCT paper: vector SVG (text as paths) plus 1200 dpi PNG."""
import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

R = Path(sys.argv[1])          # research data dir
M = Path(sys.argv[2])          # main data dir (read only)
OUT = Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
CM = 1 / 2.54
LANG = os.environ.get("ISCT_LANG", "en")  # "ru": Russian labels, files *_ru.*
RU_LABELS = {
    "event loop, hashing": "цикл, хеширование",
    "event loop, sorting": "цикл, сортировка",
    "threads, hashing": "потоки, хеширование",
    "threads, sorting": "потоки, сортировка",
    "prediction (1)": "модель (1)",
    "Predicted mean wait in an event loop, ms": "Предсказанное ожидание в цикле, мс",
    "Measured probe delay, ms": "Задержка зонда, мс",
    "(a)": "(а)", "(b)": "(б)",
    "deterministic": "детермин.", "bimodal": "бимодальный",
    "ρ = 0.3": "ρ = 0,3", "ρ = 0.5": "ρ = 0,5",
    "Event-loop probe delay, ms": "Задержка зонда, мс",
    "share > 200 ms": "доля > 200 мс",
    "Distortion exponent γ": "Показатель искажения γ",
    "Light > 200 ms, %": "Лёгкие > 200 мс, %",
    "Throughput, requests/s": "Пропускная способность, запр./с",
    "least-connections": "least-connections",
    "cost-aware admission": "допуск по оценке стоимости",
    "100 ms": "100 мс", "200 ms": "200 мс",
    "Concurrent clients": "Параллельные клиенты",
    "Light requests, p95, ms": "p95 лёгких запросов, мс",
}


def t(text):
    return RU_LABELS.get(text, text) if LANG == "ru" else text


def num(x):
    return f"{x:.2f}".replace(".", ",") if LANG == "ru" else f"{x:.2f}"

plt.rcParams.update({
    "font.family": "Times New Roman", "font.size": 8, "axes.titlesize": 8,
    "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "legend.fontsize": 7, "axes.linewidth": 0.75, "lines.linewidth": 1.0,
    "xtick.major.width": 0.75, "ytick.major.width": 0.75,
    "xtick.minor.width": 0.5, "ytick.minor.width": 0.5,
    "svg.fonttype": "path", "pdf.fonttype": 42, "axes.spines.top": False,
    "axes.spines.right": False, "mathtext.fontset": "stix",
})


def save(fig, name):
    name = name + ("_ru" if LANG == "ru" else "")
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(OUT / f"{name}.png", dpi=1200, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def fig_queue_model():
    d = json.loads((R / "queue_model_validation.json").read_text(encoding="utf-8"))
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12.2 * CM, 4.7 * CM),
                                 gridspec_kw={"width_ratios": [1.35, 1]})
    styles = {
        ("async", "hash"): dict(marker="o", mfc="black", mec="black", label=t("event loop, hashing")),
        ("async", "sort"): dict(marker="^", mfc="black", mec="black", label=t("event loop, sorting")),
        ("sync", "hash"): dict(marker="o", mfc="white", mec="black", label=t("threads, hashing")),
        ("sync", "sort"): dict(marker="^", mfc="white", mec="black", label=t("threads, sorting")),
    }
    used = set()
    for eng in ("async", "sync"):
        for pt in d["engines"][eng]["points"]:
            kind = "sort" if pt["scenario"].startswith("sort") else "hash"
            st = dict(styles[(eng, kind)])
            label = st.pop("label")
            label = label if (eng, kind) not in used else None
            used.add((eng, kind))
            y = max(pt["probe_delay_mean_ms"], 0.1)
            ax.errorbar(pt["pk_predicted_wait_ms"], y, yerr=pt["probe_delay_ci95_ms"],
                        fmt="none", ecolor="0.45", elinewidth=0.6, capsize=1.2)
            ax.plot(pt["pk_predicted_wait_ms"], y, linestyle="none", ms=3.6,
                    mew=0.75, label=label, **st)
    lim = [1, 200]
    ax.plot(lim, lim, color="0.3", lw=0.75, ls="--", label=t("prediction (1)"))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1.5, 200)
    ax.set_ylim(0.05, 400)
    ax.set_xlabel(t("Predicted mean wait in an event loop, ms"))
    ax.set_ylabel(t("Measured probe delay, ms"))
    ax.legend(loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=2, frameon=False,
              handletextpad=0.3, borderaxespad=0.1, labelspacing=0.2, columnspacing=0.8)
    ax.text(0.97, 0.04, t("(a)"), transform=ax.transAxes, ha="right", va="bottom", fontsize=8)

    # (b) equal mean, equal utilization: deterministic vs bimodal
    a = {(p["scenario"], p["rho"]): p for p in d["engines"]["async"]["points"]}
    xs, w = [0, 1], 0.2
    for k, rho in enumerate((0.3, 0.5)):
        for j, (scen, hatch) in enumerate((("hash_equal", None), ("hash_bimodal", "////"))):
            x = k + (j - 0.5) * w * 1.05
            p = a[(scen, rho)]
            bx.bar(x, p["probe_delay_mean_ms"], width=w, color="0.75" if j == 0 else "white",
                   edgecolor="black", linewidth=0.75, hatch=hatch,
                   label=(t(("deterministic", "bimodal")[j]) if k == 0 else None))
            bx.errorbar(x, p["probe_delay_mean_ms"], yerr=p["probe_delay_ci95_ms"],
                        fmt="none", ecolor="black", elinewidth=0.6, capsize=1.5)
            bx.plot(x, p["pk_predicted_wait_ms"], marker="_", color="black", ms=9, mew=1.2,
                    label=(t("prediction (1)") if (k == 0 and j == 0) else None))
    bx.set_xticks(xs)
    bx.set_xticklabels([t("ρ = 0.3"), t("ρ = 0.5")])
    bx.set_ylabel(t("Event-loop probe delay, ms"))
    bx.set_xlim(-0.5, 1.5)
    bx.set_ylim(0, 72)
    bx.legend(loc="upper left", frameon=False, handletextpad=0.3, borderaxespad=0.1,
              labelspacing=0.2)
    bx.text(0.97, 0.96, t("(b)"), transform=bx.transAxes, ha="right", va="top", fontsize=8)
    fig.tight_layout(w_pad=1.2)
    save(fig, "fig1_queue_model")


def fig_distortion():
    p = R / "magnitude_distortion.json"
    if not p.exists():
        print("no distortion data yet")
        return
    d = json.loads(p.read_text(encoding="utf-8"))
    pts = sorted(((float(g), v) for g, v in d["points"].items()), key=lambda t: t[0])
    g = [t[0] for t in pts]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12.2 * CM, 3.9 * CM))
    ax.plot(g, [v["light_over_budget_pct"] for _, v in pts], marker="o", color="black",
            mfc="black", ms=3.6, label=t("share > 200 ms"))
    ax.set_xlabel(t("Distortion exponent γ"))
    ax.set_ylabel(t("Light > 200 ms, %"))
    ax.axvline(1.0, color="0.6", lw=0.6, ls=":")
    ax.set_xticks(g)
    ax.set_xticklabels([num(v) for v in g])
    ax.set_ylim(bottom=0)
    ax.set_title(t("(a)"), loc="left", fontsize=8)
    bx.errorbar(g, [v["rps"] for _, v in pts], yerr=[v["rps_std"] for _, v in pts],
                marker="s", color="black", mfc="white", ms=3.6, capsize=1.5, elinewidth=0.6)
    bx.set_xlabel(t("Distortion exponent γ"))
    bx.set_ylabel(t("Throughput, requests/s"))
    bx.axvline(1.0, color="0.6", lw=0.6, ls=":")
    bx.set_xticks(g)
    bx.set_xticklabels([num(v) for v in g])
    bx.set_title(t("(b)"), loc="left", fontsize=8)
    lo = min(v["rps"] - v["rps_std"] for _, v in pts)
    hi = max(v["rps"] + v["rps_std"] for _, v in pts)
    bx.set_ylim(max(0, lo - 5), hi + 5)
    fig.tight_layout(w_pad=1.5)
    save(fig, "fig2_distortion")


def fig_capacity():
    d = json.loads((M / "nginx_capacity.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(12.2 * CM, 4.3 * CM))
    names = {"обычная (least_conn)": (t("least-connections"), dict(marker="o", mfc="white")),
             "по оценке стоимости": (t("cost-aware admission"), dict(marker="s", mfc="black"))}
    for key, (label, st) in names.items():
        curve = d["режимы"][key]["кривая"]
        ax.plot([c["потоков"] for c in curve], [c["лёгкие_p95_мс"] for c in curve],
                color="black", ms=3.6, mec="black", label=label, **st)
        for c in curve:
            ax.annotate(f"{c['рпс']:.0f}", (c["потоков"], c["лёгкие_p95_мс"]),
                        textcoords="offset points", xytext=(0, 4 if st["mfc"] == "white" else -9),
                        ha="center", fontsize=6.5, color="0.2")
    for y in (100, 200):
        ax.axhline(y, color="0.5", lw=0.6, ls="--")
        ax.text(33.5, y * 1.06, t(f"{y} ms"), fontsize=7, color="0.25", ha="right")
    ax.set_yscale("log")
    ax.set_ylim(40, 1500)
    ax.set_xlim(0, 34)
    ax.set_xticks([2, 4, 8, 12, 16, 24, 32])
    ax.set_xlabel(t("Concurrent clients"))
    ax.set_ylabel(t("Light requests, p95, ms"))
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    save(fig, "fig3_capacity")


if __name__ == "__main__":
    which = sys.argv[4:] or ["queue", "distortion", "capacity"]
    if "queue" in which:
        fig_queue_model()
    if "distortion" in which:
        fig_distortion()
    if "capacity" in which:
        fig_capacity()
    print("ok")
