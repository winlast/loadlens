# Post-pilot protocol extension before confirmation

Pilot measured approximately 33 ms vs 14 ms lag for clustered vs separated operations. No pilot row is used for training or test. Primitive ranges are fixed in design.json. Full main dataset has 160 multiset families with four variants each, five random-order repetitions, including 64 training, 16 validation, 32 short-test and 48 long-test families.

Secondary transfer checks reuse frozen test programs and predictions under uvloop with timers, and uvloop with a separate HTTP delay service. These are same-host implementation/transport checks, not independent hardware replications. No fitting is performed on either transfer set.

External HTTP replay: first 8 short and first 8 long test families, all four variants (64 programs), three random-order repeats. Policies: all inline, all offloaded, predicted lag above a fixed 20 ms budget from effect-aware neural composition, largest-node analytic control and ordered GRU. Offload is an isolated process, not a thread. Simultaneous independent HTTP probes measure maximum response time and heavy-request duration. Threshold is operationally illustrative and not tuned on test values. Policy decisions and prediction models are frozen before replay. Report the amount of offloading alongside latency; all-offload is a protection reference, not an efficiency competitor.

Representation sensitivity: recompute predictions assuming every await suspends (syntax) and assuming none suspends (sum). The true suspension flag is deliberately supplied by the controlled program's configuration. No automatic inference from arbitrary Python code or unknown cache state is claimed.
