"""Passages that depend on the magnitude-distortion experiment and on the final numbers."""


def results_text(L):
    dp = L["dp"]
    g = sorted(dp)
    share = {k: dp[k]["light_over_budget_pct"] for k in g}
    rps = {k: dp[k]["rps"] for k in g}
    p95 = {k: dp[k]["light_p95"] for k in g}
    best_g = min(g, key=lambda k: share[k])
    worst_g = max(g, key=lambda k: share[k])
    mech = L["mech"]
    factor = share[worst_g] / share[best_g]

    dist_abstract = (
        "with every admission decision held fixed, distorting only the magnitudes of the estimate "
        f"moves the share of delayed light requests between {share[best_g]:.1f} and "
        f"{share[worst_g]:.1f} percent, and underestimating heavy requests is the harmful "
        "direction.")

    e2_1 = (
        "Figure 2 shows the effect of changing magnitudes alone. All configurations make identical "
        "admission decisions, yet the share of light requests answered later than 200 ms falls from "
        f"{share[worst_g]:.1f}% at $\\gamma ={worst_g:g}$ to {share[best_g]:.1f}% at "
        f"$\\gamma ={best_g:g}$, a {factor:.1f}-fold change, against {share[1.0]:.1f}% for the "
        "undistorted estimate, and the 95th percentile of light requests falls from "
        f"{p95[worst_g]:.0f} to {p95[best_g]:.0f} ms. Throughput stays between "
        f"{min(rps.values()):.1f} and {max(rps.values()):.1f} requests per second, within the spread "
        "between repetitions.")
    e2_2 = (
        "Compressing magnitudes ($\\gamma <1$) makes heavy requests already on the thread engine "
        "look lighter, so more light requests are sent there and wait behind computations that hold "
        "the interpreter lock; the linear rule makes this error on routes with quadratic cost. "
        "Stretching them ($\\gamma >1$) keeps light requests on the event-loop engine. Exact "
        "magnitudes therefore did not give the shortest tail here, presumably because blocking was "
        "profiled with a single concurrent request and understates what heavy computations do to "
        "the thread engine under full load. The cross run agrees: with the linear rule for "
        "admission and the perceptron for weighting, "
        f"{mech['split_linear_neural_20']['light_over_budget_pct']:.1f}% of light requests exceeded "
        "200 ms; with the roles swapped, "
        f"{mech['split_neural_linear_15']['light_over_budget_pct']:.1f}%, close to "
        f"{mech['budget_linear_20']['light_over_budget_pct']:.1f}% for the rule in both roles.")

    disc_1 = (
        "The experiments support both halves of the hypothesis. Admission behaves as an ordinal "
        "decision: every estimate monotone in the request parameter separated safe from unsafe "
        "requests perfectly, and by the invariance of Sect. 2.3 rescaling it cannot change a single "
        "decision. Queue weighting behaves as a cardinal one: with admission fixed, magnitudes "
        "alone changed the tail several-fold, and underestimating heavy requests was the costly "
        "direction. A hand-written rule is thus a sound admission filter, whereas queue weighting "
        "needs a calibrated, preferably conservative estimate; here the cheapest one is a "
        "two-parameter power law per route, as accurate as the perceptron at about one hundredth of "
        "its decision cost.")

    concl = (
        "What a learned cost estimate must get right when a router shields an event loop from "
        "heavy requests differs between the two decisions the router makes. Whether a request may "
        "enter the loop depends only on how requests are ordered, so a rule monotone in the request "
        "parameter suffices; how the queues of the engines are compared depends on the estimate in "
        "milliseconds, and there a fitted model is required, biased if anything towards "
        "overestimating heavy requests. The queueing model accounts for the need to protect the "
        "event loop through the second moment of admitted work and converts a latency objective "
        "into an admission threshold by (4) without an experimental sweep. In practice, cost-aware "
        "routing pays off when traffic is heterogeneous and the latency objective is tight; with "
        "loose objectives or homogeneous traffic, least-connections balancing is as good or better. "
        "Further work will address costs that depend on several request features at once, as in "
        "the PostgREST service, and routing that remains stable when the protected engine "
        "degrades.")
    return dist_abstract, e2_1, e2_2, disc_1, concl
