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
    pg = L["pg"]
    factor = share[worst_g] / share[best_g]

    dist_abstract = (
        "with every admission decision held fixed, distorting only the magnitudes of the estimate "
        f"moves the share of delayed light requests between {share[best_g]:.1f} and "
        f"{share[worst_g]:.1f} percent, and underestimating heavy requests is the harmful "
        "direction.")

    e2_1 = (
        "Figure 2 shows what happens when only magnitudes change. All configurations make "
        "identical admission decisions, yet the share of light requests answered later than "
        f"200 ms falls from {share[worst_g]:.1f}% at $\\gamma ={worst_g:g}$ to {share[best_g]:.1f}% at "
        f"$\\gamma ={best_g:g}$, against {share[1.0]:.1f}% for the undistorted estimate, and the 95th "
        f"percentile of light requests falls from {p95[worst_g]:.0f} to {p95[best_g]:.0f} ms. "
        f"Throughput stays between {min(rps.values()):.1f} and {max(rps.values()):.1f} requests per "
        "second, within the spread between repetitions. The outcome of queue weighting depends on "
        "the magnitude of the estimate, as Proposition 1 states.")
    e2_2 = (
        "The direction of the effect is informative. Compressing magnitudes ($\\gamma <1$) makes "
        "heavy requests already on the thread engine look lighter, so more light requests are sent "
        "there and wait behind computations that hold the interpreter lock; this is the error the "
        "linear rule makes on routes with quadratic cost. Stretching them ($\\gamma >1$) keeps light "
        "requests on the protected event loop. The exact magnitude is thus not the optimum: "
        "blocking was profiled with a single concurrent request and understates what heavy "
        "computations do to the thread engine under full load, so a conservative estimate pays "
        "off. The cross experiment agrees: with the linear rule for admission and the perceptron for "
        f"weighting, {mech['split_linear_neural_20']['light_over_budget_pct']:.1f}% of light requests "
        "exceeded 200 ms; with the roles swapped, "
        f"{mech['split_neural_linear_15']['light_over_budget_pct']:.1f}%, close to "
        f"{mech['budget_linear_20']['light_over_budget_pct']:.1f}% for the rule in both roles.")

    disc_1 = (
        "The experiments support both halves of the hypothesis. Admission is an ordinal decision: "
        "every estimate monotone in the request parameter separated safe from unsafe requests "
        "perfectly, and by Proposition 1 rescaling it cannot change a single decision. Queue "
        "weighting is cardinal: with admission fixed, magnitudes alone changed the share of delayed "
        f"light requests {factor:.1f}-fold, and underestimating heavy requests is the costly "
        "direction. A hand-written rule is thus a sound "
        "admission filter, whereas queue weighting needs a calibrated, preferably conservative "
        "estimate; here the cheapest one is a two-parameter power law per route, as accurate as the "
        "perceptron at about one hundredth of its decision cost.")

    concl = (
        "What a learned cost estimate must get right when a router shields an event loop from "
        "heavy requests differs between the two decisions the router makes. Whether a request may "
        "enter the loop depends only on "
        "how requests are ordered, so a rule monotone in the request parameter suffices; how the "
        "queues of the engines are compared depends on the estimate in milliseconds, and there a "
        "fitted model is required, biased if anything towards overestimating heavy requests. The "
        "queueing model explains why the event loop needs protection at all, through the second "
        "moment of admitted work, and converts a latency objective into an admission threshold by "
        "(4) instead of an experimental sweep. In practice, cost-aware routing pays off when "
        "traffic is heterogeneous and the latency objective is tight; with loose objectives or "
        "homogeneous traffic, plain least-connections balancing is as good or better. Further work "
        "will address costs that depend on several request features at once, as in the PostgREST "
        f"service, where one parameter explained only {pg['объясняется_одним_параметром_%']:.0f}% of "
        "latency variance; routing that stays robust when the protected engine degrades; and "
        "engines built on the free-threaded CPython.")
    return dist_abstract, e2_1, e2_2, disc_1, concl
