# Effect aware composition study

This package contains a controlled, single-host benchmark of event-loop blocking prediction. There are 160 operation-multiset families, 640 named variants and 584 distinct annotated paths. Five technical repetitions are aggregated within each variant. Train/validation families have 2 or 3 synchronous work nodes; long-test families have 4,6,8. Calibration spans the test size range. The suspension effect is supplied by the program configuration, not inferred from arbitrary source.

## Reproduce analysis of retained measurements

Use Python 3.12 on Linux and install requirements.txt in an isolated environment. From this directory run:

```
python experiments/composition/analyze.py
python experiments/composition/verify.py
```

Analysis fits the ten seeded versions of each learned method using the frozen partitions. It takes several minutes on the collection host. Tree-ensemble prediction sums can differ at floating-point roundoff under parallel accumulation; a tolerance of 1e-10 covers the observed discrepancy. Raw data are retained. Verification reconstructs callback maxima, region costs, grouped identities, metrics and frozen replay decisions. bootstrap units are families, never individual repetitions.

## Collect new timings

The retained design is authoritative; do not run the design command over it when reproducing the reported analysis. New measurements are hardware-dependent and are not expected to be byte identical. The collectors resume existing JSONL files; use a separate copy of data/composition for a fresh collection.

```
python experiments/composition/study.py collect
python experiments/composition/study.py collect --loop uvloop --split short,long
```

For HTTP transport, start `python experiments/composition/stub.py` in a separate terminal (localhost18391), then run `python experiments/composition/study.py collect --loop uvloop --transport http --split short,long`. Stop that server afterwards.

For the policy replay, first run analyze.py to freeze predictions, start `python experiments/composition/replay_server.py` (localhost18392), then run `python experiments/composition/replay.py` in a separate terminal. Stop the replay server afterwards. These commands perform only local benchmark traffic. Recollection changes the data underlying reported results; retain the original raw files and manifests.

## Interpretation

The cost rule is sum within non-suspending regions and max across regions. The elementary error bound is conditional on correct effects and node-cost errors. Paths are a restricted graph family. No arbitrary-DAG, cross-host, production-traffic, throughput or service-level guarantee is claimed. The recurrent model is more accurate on short test compositions; the structural model is more accurate on long tests. Parametric composition is competitive with neural node calibration. Replay uses frozen predictions computed offline and one active heavy request.

Pilot timings are excluded from the reported train/test data. PREREGISTERED_DESIGN.md and PROTOCOL_EXTENSION.md preserve the declared measurement and comparison protocol. The anonymous package redacts the testbed's identifying name in Markdown protocol text; no numerical data are redacted.
