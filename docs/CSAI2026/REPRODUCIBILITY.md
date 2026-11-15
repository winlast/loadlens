# Anonymous reproduction package

Provenance Graphs for Auditing Generalisation in Learned Request Cost Models

This package contains the unchanged 540-record benchmark archive and the new
provenance/generalisation analysis. It contains no new runtime measurements.

From the package root, using Python 3.12 and the dependencies in requirements.txt:

    python experiments/csai_provenance.py
    python experiments/verify_research.py

The first command refits all models and writes data/csai. The second independently
checks graph links, all split manifests, per-record predictions and aggregates.
Existing data/csai outputs preserve the exact results used in the manuscript.
The raw archive has 540 rows; the new prediction experiment uses 450 rows from
five parameterised operations. The fixed-cost route remains in the identity audit.
Twenty row partitions, twenty grouped partitions and one fixed upper-range
partition with twenty neural initialisations yield 180 predictor-run records.
The 20 repetitions are not independent recollections of the workload.

provenance_graph.json is the base typed graph; splits.json supplies assignments;
predictions.csv holds all 22977 prediction rows; results.json contains aggregates;
audit.json records source digests and software versions. No production service
needs to run for this offline reproduction. Re-fitting can have minor numeric
differences with a different PyTorch build or hardware. verification.json records
the independent checks of the archived output, not a new data-collection audit.
