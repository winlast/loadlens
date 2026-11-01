"""
ISCT paper: Rank or Magnitude: Learned Request Cost Estimates for Event-Loop-Aware Routing.

Every number in the text is read from the measurement files at build time.
usage: build_paper.py <research data dir> <main data dir> <figures dir> <template dir> <out.docx>
"""
import json
import math
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx_builder import Doc, run  # noqa: E402

R, M, FIG, TPL, OUT = (Path(a) for a in sys.argv[1:6])


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def f1(x):
    return f"{x:.1f}"


def pct(x):
    return f"{x:.1f}%"


# ---------------------------------------------------------------------------
# numbers
# ---------------------------------------------------------------------------
grid = load(R / "cost_grid_detail.json")
ec = load(R / "endpoint_cost.json")
bf = load(R / "budget_frontier.json")
mech = load(R / "mechanism.json")
dc = load(R / "decision_cost.json")
drift = load(R / "drift_comparison.json")
hio = load(R / "homogeneous_io.json")["levels"]["32"]
hcpu = load(R / "homogeneous_cpu.json")["levels"]["32"]
rvm = load(R / "rank_vs_magnitude.json")
qm = load(R / "queue_model_validation.json")
dist_p = R / "magnitude_distortion.json"
dist = load(dist_p) if dist_p.exists() else {
    "concurrency": 32, "repeats": 5, "requests": 600, "budget_ms": 30,
    "points": {"0.5": {}, "0.75": {}, "1.0": {}, "1.5": {}, "2.0": {}}}
az = load(M / "azure_trace.json")
pg = load(M / "thirdparty_postgrest.json")
cap = load(M / "nginx_capacity.json")
gor = load(M / "gorouter.json")

blk_sync = grid["/api/auth/verify"]["sync"][0]["block_ms"]
blk_async = grid["/api/auth/verify"]["async"][0]["block_ms"]
search = {r["param"]: r["total_ms"] for r in ec["/api/search"]}
report = {r["param"]: r["total_ms"] for r in ec["/api/report/generate"]}
spread_search = search[600] / search[10]
spread_report = report[75] / report[8]

azs = az["разброс_p99_к_p50"]

# queue model validation
qa = qm["engines"]["async"]
qs = qm["engines"]["sync"]
a_pts = {(p["scenario"], p["rho"]): p for p in qa["points"]}
s_pts = {(p["scenario"], p["rho"]): p for p in qs["points"]}
a_hash = [p for p in qa["points"] if p["scenario"].startswith("hash")]
ratios = [p["probe_delay_mean_ms"] / p["pk_predicted_wait_ms"] for p in a_hash]
logx = [math.log(p["pk_predicted_wait_ms"]) for p in qa["points"]]
logy = [math.log(max(p["probe_delay_mean_ms"], 0.05)) for p in qa["points"]]
r_log = statistics.correlation(logx, logy)
s_hash = [p for p in qs["points"] if p["scenario"].startswith("hash")]
s_hash_max = max(p["probe_delay_mean_ms"] for p in s_hash)
s_hash_pred_max = max(p["pk_predicted_wait_ms"] for p in s_hash)
cal = qa["calibrated_ms"]
bim3, eq3 = a_pts[("hash_bimodal", 0.3)], a_pts[("hash_equal", 0.3)]
bim5, eq5 = a_pts[("hash_bimodal", 0.5)], a_pts[("hash_equal", 0.5)]
_dummy = {"probe_delay_mean_ms": float("nan")}
sort_large_s = s_pts.get(("sort_large", 0.4), _dummy)
sort_large_a = a_pts[("sort_large", 0.4)]
sort_small_s = s_pts.get(("sort_small", 0.4), _dummy)
low = [p for p in a_hash if p["rho"] <= 0.2 or p["mean_b_ms"] < 30]

# offline rank vs magnitude
E = rvm["estimators"]

# distortion
dp = {float(k): v for k, v in dist["points"].items()}
g_sorted = sorted(dp)
d1 = dp.get(1.0, {})

# end-to-end
fr = bf
best_single = max(fr["all_sync"]["rps"], fr["all_async"]["rps"])
pw = fr["budget_power_30"]

# capacity
cl = cap["режимы"]["обычная (least_conn)"]
cc = cap["режимы"]["по оценке стоимости"]
cc_p95 = [c["лёгкие_p95_мс"] for c in cc["кривая"]]
cl_p95 = [c["лёгкие_p95_мс"] for c in cl["кривая"]]
cap100_l, cap100_c = cl["ёмкость_при_пороге"]["100.0"]["рпс"], cc["ёмкость_при_пороге"]["100.0"]["рпс"]
cap200_l, cap200_c = cl["ёмкость_при_пороге"]["200.0"]["рпс"], cc["ёмкость_при_пороге"]["200.0"]["рпс"]

def fig_h(name):
    from PIL import Image
    with Image.open(FIG / f"{name}.png") as im:
        w, h = im.size
    return round(12.2 * h / w, 2)


# ---------------------------------------------------------------------------
# result-dependent passages
# ---------------------------------------------------------------------------
max_over = max(ratios)
pk_ratio5 = bim5["pk_predicted_wait_ms"] / eq5["pk_predicted_wait_ms"]
pk_ratio3 = bim3["pk_predicted_wait_ms"] / eq3["pk_predicted_wait_ms"]
small = [p for p in a_hash if p["scenario"] == "hash_small"]
long_ratios = [p["probe_delay_mean_ms"] / p["pk_predicted_wait_ms"] for p in a_hash
               if p["scenario"] != "hash_small"]
assert max(long_ratios) == max_over
E1_TEXT_1 = (
    "Figure 1a compares measured probe delays with the prediction of (1). For the event loop the "
    "model captures the effect across two orders of magnitude (correlation of logarithms "
    f"{r_log:.2f}). For the shortest computations ({cal['hash_small']:.0f} ms) the delays of "
    + ", ".join(f"{p['probe_delay_mean_ms']:.1f}" for p in small)
    + " ms at the three utilizations match the predicted "
    + ", ".join(f"{p['pk_predicted_wait_ms']:.1f}" for p in small)
    + " ms. For longer computations and mixes the measurement is "
    f"{min(long_ratios):.1f}–{max(long_ratios):.1f} times the prediction, the largest gap "
    f"occurring at $\\rho =0.6$ with {cal['hash_large']:.0f} ms computations, as the loop also "
    "spends time on connections and response serialization not covered by the idle calibration. "
    "On the thread engine with "
    f"hashing, which releases the interpreter lock, probes waited at most {s_hash_max:.1f} ms, "
    f"whereas an event loop fed the same streams would impose up to {s_hash_pred_max:.0f} ms.")
E1_TEXT_2 = (
    "The second moment matters in the way the model predicts. At equal utilization and nearly "
    "equal mean blocking, a stream in which one computation in ten is long delayed probes "
    f"{bim5['probe_delay_mean_ms'] / eq5['probe_delay_mean_ms']:.1f} times more at $\\rho =0.5$ "
    f"({bim5['probe_delay_mean_ms']:.1f} against {eq5['probe_delay_mean_ms']:.1f} ms) and "
    f"{bim3['probe_delay_mean_ms'] / eq3['probe_delay_mean_ms']:.1f} times more at $\\rho =0.3$, "
    f"while (1) gives {pk_ratio5:.1f} and {pk_ratio3:.1f} (Fig. 1b). Computations that hold the "
    "interpreter lock remove the protection offered by threads: sorting with blocking of "
    f"{cal['sort_large']:.0f} ms at $\\rho =0.4$ delayed probes on the thread engine by "
    f"{sort_large_s['probe_delay_mean_ms']:.1f} ms, against {sort_large_a['probe_delay_mean_ms']:.1f} "
    "ms on the event loop. Such work counts as blocking on both engines, which is why the router "
    "estimates $b_{e}$ for each engine separately instead of labelling requests as computational.")

N_PLACEHOLDER = "[pending]"
DIST_ABSTRACT = N_PLACEHOLDER
E2_TEXT_1 = N_PLACEHOLDER
E2_TEXT_2 = N_PLACEHOLDER
DISC_1 = N_PLACEHOLDER
CONCL = N_PLACEHOLDER
FIG1_H = fig_h("fig1_queue_model")
FIG2_H = fig_h("fig2_distortion")
FIG3_H = fig_h("fig3_capacity")

if (Path(__file__).parent / "results_text.py").exists():
    from results_text import results_text
    DIST_ABSTRACT, E2_TEXT_1, E2_TEXT_2, DISC_1, CONCL = results_text(dict(locals()))

N = dict(locals())

# ---------------------------------------------------------------------------
# text
# ---------------------------------------------------------------------------
TITLE = "Rank or Magnitude: Learned Request Cost Estimates for Event-Loop-Aware Routing"
RUN_TITLE = "Rank or Magnitude: Learned Request Cost Estimates"
RUN_AUTHORS = "S. D. Sinyavskiy and M. I. Kolosov"

from text_content import ABSTRACT, KEYWORDS, write_body  # noqa: E402

words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]*", re.sub(r"\$[^$]*\$", "x", ABSTRACT(N))))
title_words = len(TITLE.replace(":", "").split())
print(f"abstract words: {words}; title words: {title_words}")
assert 150 <= words <= 250, words
assert title_words <= 12

doc = Doc()
doc.title(TITLE)
# authors (ЦПНП format): names, correspondent mark, affiliation, e-mail and ORCID
doc.raw_para(run("Stanislav D. Sinyavskiy", sz=20) + run("1(*)", sz=20, sup=True)
             + run(" and Maxim I. Kolosov", sz=20) + run("1", sz=20, sup=True),
             after=120, jc="center", sz=20)
doc.raw_para(run("* Correspondent author", sz=18), after=120, jc="center", sz=18)
doc.raw_para(run("1", sz=18, sup=True)
             + run(" Bauman Moscow State Technical University, Moscow, Russia", sz=18),
             after=0, jc="center", sz=18)
doc.raw_para(run("S. D. Sinyavskiy, e-mail: ", sz=18)
             + run("ssd-tula@mail.ru", sz=18, font="Courier New")
             + run("; ORCID: 0009-0001-6773-0628", sz=18), after=0, jc="center", sz=18)
doc.raw_para(run("M. I. Kolosov, e-mail: ", sz=18)
             + run("KOLOSOV_EMAIL", sz=18, font="Courier New", highlight="yellow")
             + run("; ORCID: ", sz=18)
             + run("0000-0000-0000-0000", sz=18, highlight="yellow"),
             after=200, jc="center", sz=18)
doc.abstract(ABSTRACT(N))
doc.keywords(KEYWORDS)
write_body(doc, N, FIG)
doc.save(TPL, OUT, RUN_AUTHORS, RUN_TITLE)
print("saved", OUT)
