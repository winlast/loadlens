# Composition study design frozen before collection

Question: can a model calibrated on individual operations predict the longest event-loop stall of unseen sequential request compositions, including coroutine calls that complete without suspending?

This is a controlled systems experiment, not production traffic. The operation library reuses real PBKDF2, list sorting, SQLite reads and JPEG processing from LoadLens. Program graphs are directed paths. Asynchronous timer waits model suspension; they are not described as network measurements. A separate HTTP replay will check external latency if the pilot supports the formulation.

Primary target: maximum delay of a periodic 1 ms event-loop callback during each execution, including a post-execution drain so the final CPU region is observed. Secondary targets: request duration and measured maximum non-suspending region (diagnostic only). Preserve raw node traces, callback delays, repetition order and environment.

Candidate predictor: positive learned per-operation duration plus a symbolic sum inside each non-suspending region and max across regions. Awaited cache hits do not split a region. Controls: total CPU sum, largest individual operation, splitting at every syntactic await, unordered learned regression and order-aware learned regression with the same operation and suspension information. Compare parametric and neural node regressors; do not presume the neural version is best.

Splits are by operation multiset family, with all order/cache variants and repeats kept together. Fit short compositions only (2 or 3 CPU operations), validate on other short families, test on unseen short families and longer compositions (4, 6, 8). Individual operation calibration spans the test size range; composition transfer is primary, size extrapolation is not claimed. Fixed generation seed 20261116. Fixed model seeds 0 to 9. No test-driven hyperparameter selection.

Accuracy is evaluated per composition using median repeated target, with family-level paired bootstrap confidence intervals (10,000 resamples). Repeats are technical repetitions, not independent samples. Report median absolute percentage error, P90 absolute percentage error, underprediction by more than a factor of two, and absolute error. Report confidence intervals for paired model differences, not just each score.

Pilot: time the primitive grid and measure a small set of matched compositions before choosing practical size range. Pilot records are excluded from confirmatory evaluation. Any further protocol changes must be timestamped here before full collection and disclosed. Strong gains over an unordered baseline alone do not establish superiority over order-aware methods or necessity of a general graph architecture.

Limits planned in advance: one host, controlled paths rather than arbitrary graphs, known suspension effects rather than automatic static inference, no cross-request queue model, no correctness or service-level safety guarantee. Negative or weak results must be retained and must change the paper's claims.
