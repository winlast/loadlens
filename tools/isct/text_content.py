"""Text of the ISCT paper. Numbers come from the dictionary N built from data files."""
from pathlib import Path

KEYWORDS = ("Tail latency, Load balancing, Admission control, Queueing model, "
            "Asynchronous web servers, Processor sharing, Algorithms with predictions.")


def f1(x):
    return f"{x:.1f}"


def f0(x):
    return f"{x:.0f}"


def ABSTRACT(N):
    E = N["E"]
    return (
        "Load balancers distribute web requests without knowing what each request will cost, "
        "although in many services the cost of a call is set by its parameters rather than by its "
        "address. This work determines which property a learned per-request cost estimate must have "
        "when a router uses it to keep heavy computations away from an event-loop server, where they "
        "stall all concurrent requests, and to send them to a thread-based server. The event loop is "
        "modelled as a non-preemptive single-server queue: the delay it imposes on light requests "
        "grows with the second moment of admitted work, which yields a closed-form admission "
        "threshold for a target delay. It is shown that the admission decision is invariant to any "
        "order-preserving distortion of the estimate, whereas weighting of engine queues depends on "
        "its absolute value. Experiments on a testbed with real hashing, image "
        "encoding, database and network operations confirm both parts. A hand-written rule ranks "
        "requests perfectly at the admission threshold, yet errs by "
        f"{f1(E['linear_param']['median_batch_sum_error_pct'])} percent on summed queue work against "
        f"{f1(E['power_law']['median_batch_sum_error_pct'])} percent for a fitted power law; "
        f"{N['DIST_ABSTRACT']} Embedded in a production proxy, the policy sustains "
        f"{f0((N['cap100_c'] / N['cap100_l'] - 1) * 100)} percent more traffic than least-connections "
        "balancing under a 100 millisecond latency objective. Learning is therefore needed for the "
        "magnitude of the estimate, not for ranking requests."
    )


def write_body(doc, N, FIG: Path):
    E = N["E"]
    qa, qs = N["qa"], N["qs"]
    cal = N["cal"]

    # ------------------------------------------------------------------ 1
    doc.h1("Introduction")
    doc.p(
        "Event-driven servers such as Node.js, the Python asyncio frameworks and Netty keep thousands "
        "of connections open with a single thread per core, because waiting for a database or a "
        "remote service costs them almost nothing. The same design makes them fragile. A handler that "
        "computes for 100 ms keeps the event loop busy for 100 ms, and every other request served by "
        "that loop waits; Davis et al. showed how easily such stalls arise in server-side JavaScript "
        "[1]. Thread-per-request servers do not suffer from this, since a computing thread is "
        "preempted, but they pay for each concurrent connection with a thread and its stack, which is "
        "why event-driven architectures were proposed in the first place [2]. At scale such stalls "
        "turn into tail latency, and the tail, not the mean, sets the response time of services that "
        "fan out to many components [3–5].")
    doc.p(
        "An obvious remedy is to run both kinds of engine side by side and let the front proxy decide, "
        "for each request, where it goes. Common balancers cannot make this decision. Round robin, "
        "least connections, the power of two choices [6] and join-idle-queue [7] treat requests as "
        "interchangeable, and per-route weights assume that the address of a call determines its "
        "cost. Size-aware task assignment cuts response times sharply when job sizes are "
        "heavy-tailed [8], but it presumes that the size of each job is known. In web services it is "
        "not, and it varies within one endpoint: in the public Azure Functions trace [9] the 99th "
        "percentile of execution time exceeds the median at least tenfold for "
        f"{f1(N['azs']['доля_функций_с_разбросом_от_10_раз_%'])}% of "
        # thin space as the thousands separator; applied to the number only
        + f"{N['az']['функций']:,}".replace(",", "\u2009") + " functions.")
    doc.p(
        "The missing ingredient, an estimate of the cost of a request before it runs, is what learned "
        "components of computer systems are meant to provide [10, 11]. The theory of algorithms with "
        "predictions studies how much such estimates help and how their errors hurt [12, 13], and "
        "recent schedulers for large language model inference show that learning only the relative "
        "order of output lengths suffices to approximate shortest-job-first [14]. These works "
        "judge a predictor by a single figure of merit. A router, however, uses the estimate twice: "
        "to decide whether a request may enter the event loop at all, and to weigh the queues of the "
        "engines when choosing among admissible ones. Whether the two uses place the same demands on "
        "the estimate has not been examined, although it decides whether a trained model is needed "
        "at all.")
    doc.p(
        "The aim of this work is to establish which property of a per-request cost estimate each of "
        "the two routing decisions requires, and to measure what is lost when the estimate lacks it. "
        "The hypothesis is that admission needs only the correct order of requests, whereas queue "
        "weighting needs the correct magnitude. The contributions are a queueing model that ties the "
        "harm done in an event loop to the second moment of admitted work and yields an admission "
        "threshold for a target delay, an invariance argument that separates ordinal from cardinal "
        "requirements on the estimate, and experiments with real work, including a production "
        "proxy, that test both.")

    # ------------------------------------------------------------------ 2
    doc.h1("Materials and Methods")
    doc.h2("System Model")
    doc.p(
        "A gateway receives each request $x$ and forwards it either to a thread-per-request engine "
        "$S$ (Flask in threaded mode) or to an event-loop engine $A$ (FastAPI on uvicorn). The gateway "
        "sees only what a reverse proxy sees: the route, the query parameter $p$ that sets the amount "
        "of work (a limit, an image size or a number of days) and the body size. Two quantities "
        "describe the effect of $x$ on an engine $e$. The service time $s_{e}(x)$ is how long $x$ "
        "itself takes. The blocking time $b_{e}(x)$ is the largest delay that $x$ inflicts on light "
        "requests served concurrently by the same engine. Profiling showed that $s_{e}$ hardly "
        "depends on the engine while $b_{e}$ may differ by an order of magnitude: password hashing "
        f"blocks $S$ for {f1(N['blk_sync'])} ms and $A$ for {f1(N['blk_async'])} ms. The blocking time "
        "is therefore the quantity a router has to predict.")
    doc.h2("Queueing Model of the Two Engines")
    doc.p(
        "The event loop runs the computational part of every handler to completion, one handler at a "
        "time. With respect to computation it is a single non-preemptive server, and a light request "
        "arriving at a random moment waits for the rest of the current computation and for all "
        "computations queued before it. For Poisson arrivals at rate $\\lambda$ and blocking time $B$ "
        "this is the M/G/1 queue, whose mean waiting time is given by the Pollaczek–Khinchine "
        "formula [15]:")
    doc.eq(r"W_{A}=\frac{\lambda \mathrm{E}[B^{2}]}{2(1-\rho)},\quad \rho =\lambda \mathrm{E}[B].")
    doc.p(
        "The numerator carries the main consequence. At equal utilization $\\rho$, rare long "
        "computations harm their neighbours far more than frequent short ones, because the delay "
        "scales with $\\mathrm{E}[B^{2}]/\\mathrm{E}[B]$, the mean residual of the work in service. A "
        "thread engine behaves differently. Computation that releases the global interpreter lock "
        "(hashing, image codecs, SQLite) runs on another core, and the operating system time-shares "
        "cores among threads; on one core this is processor sharing, under which a job of size $s$ "
        "responds in")
    doc.eq(r"T_{S}(s)=\frac{s}{1-\rho},")
    doc.p(
        "independently of how the other jobs are distributed [15, 16]. Computation that holds the "
        "lock is another matter: the lock changes hands only once per switch interval (5 ms by "
        "default), and a light request that releases it at every system call may wait an interval "
        "per call. Threads thus protect light requests from computation that releases the lock and "
        "from little else, so blocking has to be estimated for each engine. Let the router admit "
        "$x$ to $A$ when its estimate $\\hat{b}(x)$ does not exceed a threshold $\\theta$. Admitted "
        "work then has a truncated distribution, and (1) becomes")
    doc.eq(r"W_{A}(\theta)=\frac{\lambda_{A}\mathrm{E}[B^{2};\hat{b}\le \theta]}{2(1-\rho_{A})},")
    doc.p(
        "where $\\mathrm{E}[X;C]$ denotes the expectation of $X$ restricted to the event $C$, and "
        "$\\lambda_{A}$, $\\rho_{A}$ are the arrival rate and utilization of admitted work. With an "
        "exact estimate every admitted request has $B\\le \\theta$, so "
        "$\\mathrm{E}[B^{2};B\\le \\theta]\\le \\theta \\mathrm{E}[B;B\\le \\theta]$, and a target $w$ "
        "for the mean added delay is guaranteed by")
    doc.eq(r"\theta \le \frac{2w(1-\rho_{A})}{\rho_{A}}.")
    doc.p(
        "For instance, at $\\rho_{A}=0.5$ a target of 10 ms is met by admitting requests that block "
        "for at most 20 ms. Condition (4) turns a latency objective into a threshold without a sweep "
        "over operating points.")
    doc.h2("Two Roles of the Estimate")
    doc.p(
        "The policy uses $\\hat{b}$ twice. Admission compares $\\hat{b}(x)$ with $\\theta$. Among the "
        "admissible engines the request goes to the one with the least pending work "
        "$Q_{e}+\\hat{b}_{e}(x)$, where $Q_{e}$ is the sum over requests in progress on $e$ of their "
        "estimates minus the time they have already spent there. With exact estimates this is "
        "join-the-shortest-work-queue.")
    doc.p(
        "{i}Let $g$ be strictly increasing. The admission decision made with the estimate "
        "$g(\\hat{b})$ and the threshold $g(\\theta)$ coincides with the decision made with $\\hat{b}$ "
        "and $\\theta$ for every request. The engine chosen by least pending work is, in general, not "
        "invariant under $g$.{/i}", runin="Proposition 1.")
    doc.p(
        "The first statement holds because $\\hat{b}\\le \\theta \\Leftrightarrow g(\\hat{b})\\le "
        "g(\\theta)$. For the second, the choice compares sums of estimates, and "
        "$g(u)+g(v)\\ne g(u+v)$ unless $g$ is linear through the origin; moreover, pending work "
        "decreases with elapsed time measured in real milliseconds, so even a linear rescaling "
        "changes when an engine appears free.", runin="Proof.")
    doc.p(
        "Admission quality is thus captured by ordinal statistics, such as Kendall's rank correlation "
        "or the area under the receiver operating characteristic curve for the split at $\\theta$, "
        "whereas queue weighting is captured by the error of summed estimates. A rule that is "
        "monotone in the request parameter can be perfect in the first sense and poor in the second.")
    doc.h2("Estimators")
    doc.p(
        "Four estimators of $b_{e}(x)$ are compared. All are fitted on the same 384 profiled requests "
        "and validated on 156 held-out requests whose parameter values did not occur in fitting. The "
        "route mean assigns one number per route and engine, as weighted balancers do. The linear "
        "rule $\\hat{b}=cp$ is what an engineer writes knowing that $p$ is a limit or a size; only "
        "$c$ is fitted. The power law $\\hat{b}=ap^{\\beta}$ is fitted per route and engine by least "
        "squares in logarithmic coordinates. The perceptron has two hidden layers of 48 and 24 units "
        "and is trained in PyTorch [17] on the logarithm of the target. The true exponents of the "
        "workload, 1 for database selections and 2 for image processing and period aggregation, are "
        "not disclosed to any estimator.")
    doc.h2("Testbed and Experiments")
    doc.p(
        "Both engines run as single processes on one Linux host with 16 logical cores, next to a stub "
        "service that answers after a requested delay, so that input and output are real network "
        "traffic. Six routes perform real work: PBKDF2 hashing, JPEG encoding, list sorting, SQLite "
        "reads and outbound calls. The parameter of each request is drawn from a log-uniform "
        "distribution skewed towards small values, and it is the parameter, not the route, that sets "
        "the amount of work. Code and measurement data are available in the project repository "
        "[18]. Four experiments were performed.")
    doc.p(
        "A Poisson stream of calibrated computations is sent directly to one "
        "engine at utilization $\\rho \\in \\{0.2,0.4,0.6\\}$, with an independent Poisson stream of "
        f"probes ({f0(N['qm']['probe_rate_per_s'])} per second) calling a handler that does no work; "
        "probe latency above that on an idle engine is the waiting time. The computations are "
        "PBKDF2 hashing, which releases the interpreter lock (blocking of "
        f"{f0(cal['hash_small'])}, {f0(cal['hash_medium'])} and {f0(cal['hash_large'])} ms, and a "
        f"bimodal mix of 90% at {f0(cal['hash_small'])} ms and 10% at {f0(cal['hash_large'])} ms "
        "against a deterministic stream of nearly equal mean), and list sorting, which holds it "
        f"({f0(cal['sort_small'])} and {f0(cal['sort_large'])} ms). Each point covers at least 250 "
        "computations; predictions use blocking calibrated on the idle engine, and nothing is "
        "fitted to the measured delays.", runin="Model validation.")
    doc.p(
        f"Requests pass through the gateway with {N['dist']['concurrency']} concurrent clients, "
        f"{N['dist']['repeats']} repetitions of {N['dist']['requests']} requests per point. The "
        "power-law estimate is replaced by $\\theta (\\hat{b}/\\theta)^{\\gamma}$ with "
        f"$\\theta ={N['dist']['budget_ms']}$ ms and "
        "$\\gamma \\in \\{" + ",".join(str(g) for g in N["g_sorted"]) + "\\}$. The transform is "
        "strictly increasing and maps $\\theta$ onto itself, so by Proposition 1 every admission "
        "decision stays the same; only queue weighting sees distorted magnitudes.",
        runin="Magnitude distortion.")
    doc.p(
        "On the held-out set each estimator is scored by the median relative "
        "error, by Kendall's $\\tau_{b}$ and the area under the curve for blocking of $A$ above "
        f"{f0(N['rvm']['threshold_ms'])} ms, and by the median relative error of the summed estimate "
        f"over random sets of {N['rvm']['batch']} requests, which is what queue weighting compares.",
        runin="Offline accuracy.")
    doc.p(
        "Throughput and the share of light requests answered later than 200 ms "
        "are compared for single-engine deployments, least connections and the policy with each "
        "estimator at thresholds from 15 to 1000 ms (32 clients, 3 repetitions of 500 requests). "
        "The policy was also implemented as a Lua module in nginx and as a Go router; for nginx the "
        "95th percentile of light requests was recorded at 2 to 32 clients.",
        runin="End-to-end and deployment.")
    doc.p(
        "All processes share one host, each engine is one interpreter process, and throughput "
        "varies between runs by up to six requests per second, so conclusions rest on tail metrics "
        "pooled over repetitions.")

    # ------------------------------------------------------------------ 3
    doc.h1("Results")
    doc.h2("Cost Varies Within an Endpoint")
    doc.p(
        "On the testbed the service time within one route spans a factor of "
        f"{f0(N['spread_search'])} for the search route (limit 10 to 600) and "
        f"{f0(N['spread_report'])} for the report route (8 to 75 days). The same holds for software "
        "the authors did not write: behind PostgREST 12 with PostgreSQL 16 the 99th percentile of "
        f"latency on the single route /orders is {f0(N['pg']['разброс_раз'])} times the median, the "
        "10% heaviest calls take "
        f"{f0(N['pg']['доля_времени_у_10%_тяжёлых_%'])}% of the time, and a per-route estimate errs by "
        f"{f0(N['pg']['ошибка_оценки_по_маршруту_%'])}% against "
        f"{f0(N['pg']['ошибка_оценки_по_параметру_%'])}% for an estimate from request features. In the "
        "Azure trace the median function has a ratio of the 99th to the 50th percentile of "
        f"{f0(N['azs']['медиана'])}, a quarter of functions exceed {f0(N['azs']['четверть_сверху'])} and "
        f"a tenth exceed {f0(N['azs']['десятая_сверху'])} [9]. One weight per route cannot represent "
        "such variation.")

    doc.h2("The Queueing Model Predicts Event-Loop Delay")
    a_hash = N["a_hash"]
    ratios = N["ratios"]
    doc.p(N["E1_TEXT_1"])
    doc.figure(FIG / "fig1_queue_model.png", FIG / "fig1_queue_model.svg", 12.2, N["FIG1_H"],
               "Waiting time of light probes: (a) measured against the prediction of (1) for both "
               "engines; (b) event-loop engine at equal utilization and nearly equal mean blocking, "
               "deterministic against bimodal computations; bars show measurements with 95% "
               "confidence intervals, dashes the prediction.",
               "{i}Note.{/i} ρ, utilization of the engine by the calibrated computations.",
               "Source: Compiled by the authors")
    doc.p(N["E1_TEXT_2"])

    doc.h2("Ranking Is Easy, Magnitude Is Not")
    doc.p(
        "Table 1 confirms the split predicted by Proposition 1. Every estimator that uses the request "
        "parameter separates safe from unsafe requests at the threshold perfectly, including the "
        f"linear rule with a magnitude error of {f1(E['linear_param']['median_ape_blocking_pct'])}%. "
        "Only the route mean, which gives a whole route one value, misorders requests. On summed "
        f"work the picture changes: the linear rule errs by "
        f"{f1(E['linear_param']['median_batch_sum_error_pct'])}%, about "
        f"{f0(E['linear_param']['median_batch_sum_error_pct'] / E['power_law']['median_batch_sum_error_pct'])} "
        f"times more than the power law ({f1(E['power_law']['median_batch_sum_error_pct'])}%), because "
        "its error is systematic on the routes with quadratic cost and does not cancel in a sum. The "
        "perceptron and the power law are close on every metric, but the power law decides in "
        f"{f1(N['dc']['power_law']['microseconds'])} µs against "
        f"{f0(N['dc']['neural']['microseconds'])} µs.")
    rows = []
    names = [("endpoint_mean", "Route mean", None), ("linear_param", "Linear rule", "linear_param"),
             ("power_law", "Power law", "power_law"), ("neural", "Perceptron", "neural")]
    for key, label, dkey in names:
        e = E[key]
        rows.append([label, f1(e["median_ape_blocking_pct"]), f"{e['kendall_tau_b_async']:.3f}",
                     f"{e['auc_async_threshold']:.3f}", f1(e["median_batch_sum_error_pct"]),
                     f"{N['dc'][dkey]['microseconds']:.2f}" if dkey else "–"])
    doc.table(
        "Ordinal and cardinal accuracy of the blocking estimators on held-out requests",
        ["Estimator", "MdRE, %", "Kendall $\\tau_{b}$", "AUC", "Sum error, %", "Decision, µs"],
        rows, [1500, 1000, 1150, 900, 1150, 1150], ["left", "right", "right", "right", "right", "right"],
        "{i}Note.{/i} MdRE, median relative error of blocking; Kendall $\\tau_{b}$, rank correlation "
        "with measured blocking of the event-loop engine; AUC, area under the receiver operating "
        f"characteristic curve for blocking above {f0(N['rvm']['threshold_ms'])} ms; sum error, median "
        f"relative error of the sum over {N['rvm']['batch']} requests; decision, time of one routing "
        "decision on one core (not measured for the route mean).",
        "Source: Compiled by the authors")

    doc.h2("Magnitude Errors Cost Tail Latency")
    doc.p(N["E2_TEXT_1"])
    doc.figure(FIG / "fig2_distortion.png", FIG / "fig2_distortion.svg", 12.2, N["FIG2_H"],
               "Effect of an order-preserving distortion of the estimate with fixed admission "
               "decisions: (a) share of light requests answered later than 200 ms; (b) throughput, "
               "mean and standard deviation over repetitions.",
               "{i}Note.{/i} γ, exponent of the distortion; γ = 1 is the undistorted power law.",
               "Source: Compiled by the authors")
    doc.p(N["E2_TEXT_2"])

    doc.h2("End-to-End Trade-off")
    fr = N["fr"]
    doc.p(
        "Table 2 lists operating points next to the deployments without routing. Every admission "
        "configuration improves on both single engines in both metrics: the power law at "
        f"$\\theta =30$ ms delivers {f1(fr['budget_power_30']['rps'])} "
        f"requests per second, {f0((fr['budget_power_30']['rps'] / N['best_single'] - 1) * 100)}% above "
        f"the better single engine, with {f1(fr['budget_power_30']['light_over_budget_pct'])}% of light "
        f"requests delayed against {f1(fr['all_sync']['light_over_budget_pct'])}% and "
        f"{f1(fr['all_async']['light_over_budget_pct'])}%. Least connections attains the highest "
        f"throughput, {f1(fr['least_conn']['rps'])}, but leaves "
        f"{f1(fr['least_conn']['light_over_budget_pct'])}% of light requests delayed; against it the "
        "policy trades throughput for a shorter tail. On homogeneous streams the policy only loses: "
        f"{f1(N['hio']['budget_neural_30']['rps'])} against {f1(N['hio']['all_async']['rps'])} "
        "requests per second for the event loop with input-output calls alone, and "
        f"{f1(N['hcpu']['budget_neural_30']['rps'])} against {f1(N['hcpu']['all_sync']['rps'])} for "
        "the thread engine with computation alone.")
    t2 = [("all_sync", "All to thread engine $S$"), ("all_async", "All to event loop $A$"),
          ("least_conn", "Least connections"), ("budget_endpoint_15", "Route mean, $\\theta =15$"),
          ("budget_linear_60", "Linear rule, $\\theta =60$"), ("budget_power_30", "Power law, $\\theta =30$"),
          ("budget_neural_15", "Perceptron, $\\theta =15$")]
    doc.table(
        "Operating points with 32 concurrent clients and a heterogeneous flow",
        ["Deployment or policy", "Throughput, req/s", "Light > 200 ms, %", "Light p95, ms"],
        [[lab, f"{fr[k]['rps']:.1f} ± {fr[k]['rps_std']:.1f}", f1(fr[k]["light_over_budget_pct"]),
          f0(fr[k]["light_p95"])] for k, lab in t2],
        [2618, 1500, 1500, 1300], ["left", "right", "right", "right"],
        "{i}Note.{/i} θ, admission threshold in ms; light, requests to the lightest route; p95, 95th "
        "percentile; throughput is the mean ± standard deviation over repetitions.",
        "Source: Compiled by the authors")

    doc.h2("Behaviour Under a Latency Objective")
    doc.p(
        "Inside nginx the policy keeps the 95th percentile of light requests between "
        f"{f0(min(N['cc_p95']))} and {f0(max(N['cc_p95']))} ms over the whole load range, whereas "
        f"under least connections it grows from {f0(min(N['cl_p95']))} to {f0(max(N['cl_p95']))} ms "
        "(Fig. 3). Under a 100 ms objective the cost-aware module sustains "
        f"{f1(N['cap100_c'])} requests per second against {f1(N['cap100_l'])}, "
        f"{f0((N['cap100_c'] / N['cap100_l'] - 1) * 100)}% more; under a 200 ms objective least "
        f"connections sustains {f1(N['cap200_l'])} against {f1(N['cap200_c'])}, so the benefit exists "
        "only when the objective is tight. A standalone Go router implementing the same rule "
        f"reproduced the outcome ({f1(N['gor']['доля_медленнее_200_мс_%'])}% of light requests over "
        f"200 ms, median {f1(N['gor']['лёгкие_медиана_мс'])} ms) at "
        f"{N['gor']['стоимость_решения_нс'] / 1000:.1f} µs per decision under load.")
    doc.figure(FIG / "fig3_capacity.png", FIG / "fig3_capacity.svg", 12.2, N["FIG3_H"],
               "Latency of light requests against offered load for the policy embedded in nginx and "
               "for least-connections balancing; point labels give throughput in requests per "
               "second, dashed lines mark the latency objectives.",
               "{i}Note.{/i} p95, 95th percentile. Throughput of least connections at the "
               "objectives is interpolated between measured points.",
               "Source: Compiled by the authors")

    # ------------------------------------------------------------------ 4
    doc.h1("Discussion")
    doc.p(N["DISC_1"])
    doc.p(
        "The result complements work on learned scheduling. Ranking output lengths is enough for "
        "language model serving [14] because shortest-job-first on one queue is an ordinal policy; "
        "once work from several queues is compared, as in join-the-shortest-queue and its variants "
        "[6, 7], the estimate has to be calibrated in time units. In the terms of algorithms with "
        "predictions [12, 13], the error measure that matters depends on the decision, and for "
        "balancing it is the error of sums.")
    dr = N["drift"]
    doc.p(
        "The approach assumes that the protected engine stays as it was profiled. When a "
        "background load took processor time from the event-loop engine, the share of delayed light "
        f"requests rose from {f1(dr['budget_neural_30']['before']['slow_pct'])}% to "
        f"{f1(dr['budget_neural_30']['after']['slow_pct'])}%, while least connections held "
        f"{f1(dr['least_conn']['after']['slow_pct'])}% and the best adaptive correction tried reached "
        f"{f1(dr['healthfull_neural_30']['after']['slow_pct'])}%: requests were still classified "
        "correctly, but the engine had become slow for all of them, and only queue-length feedback "
        "reacts to that. The convoy effect observed for sorting is specific to CPython with a global "
        "lock, and its free-threaded build is expected to remove it.")

    # ------------------------------------------------------------------ 5
    doc.h1("Conclusion")
    doc.p(N["CONCL"])

    doc.runin9("Disclosure of Interests.",
               "The authors have no competing interests to declare that are relevant to the content "
               "of this article.")
    doc.references(REFERENCES)


REFERENCES = [
    "Davis J, Thekumparampil A, Lee D (2017) Node.fz: fuzzing the server-side event-driven "
    "architecture. In: Proceedings of the twelfth European conference on computer systems "
    "(EuroSys '17). ACM, New York, pp 145–160. doi:10.1145/3064176.3064188",
    "Welsh M, Culler D, Brewer E (2001) SEDA: an architecture for well-conditioned, scalable "
    "internet services. In: Proceedings of the eighteenth ACM symposium on operating systems "
    "principles (SOSP '01). ACM, New York, pp 230–243. doi:10.1145/502034.502057",
    "Dean J, Barroso LA (2013) The tail at scale. Commun ACM 56(2):74–80. "
    "doi:10.1145/2408776.2408794",
    "Li J, Sharma NK, Ports DRK, Gribble SD (2014) Tales of the tail: hardware, OS, and "
    "application-level sources of tail latency. In: Proceedings of the ACM symposium on cloud "
    "computing (SoCC '14). ACM, New York, pp 1–14. doi:10.1145/2670979.2670988",
    "Delimitrou C, Kozyrakis C (2018) Amdahl's law for tail latency. Commun ACM 61(8):65–72. "
    "doi:10.1145/3232559",
    "Mitzenmacher M (2001) The power of two choices in randomized load balancing. IEEE Trans "
    "Parallel Distrib Syst 12(10):1094–1104. doi:10.1109/71.963420",
    "Lu Y, Xie Q, Kliot G, Geller A, Larus JR, Greenberg A (2011) Join-idle-queue: a novel load "
    "balancing algorithm for dynamically scalable web services. Perform Eval 68(11):1056–1071. "
    "doi:10.1016/j.peva.2011.07.015",
    "Harchol-Balter M, Crovella ME, Murta CD (1999) On choosing a task assignment policy for a "
    "distributed server system. J Parallel Distrib Comput 59(2):204–228. "
    "doi:10.1006/jpdc.1999.1577",
    "Shahrad M, Fonseca R, Goiri Í et al (2020) Serverless in the wild: characterizing and "
    "optimizing the serverless workload at a large cloud provider. arXiv. "
    "doi:10.48550/arXiv.2003.03423",
    "Kraska T, Beutel A, Chi EH, Dean J, Polyzotis N (2018) The case for learned index "
    "structures. In: Proceedings of the 2018 international conference on management of data "
    "(SIGMOD '18). ACM, New York, pp 489–504. doi:10.1145/3183713.3196909",
    "Mao H, Schwarzkopf M, Venkatakrishnan SB, Meng Z, Alizadeh M (2019) Learning scheduling "
    "algorithms for data processing clusters. In: Proceedings of the ACM special interest group on "
    "data communication (SIGCOMM '19). ACM, New York, pp 270–288. doi:10.1145/3341302.3342080",
    "Mitzenmacher M, Vassilvitskii S (2022) Algorithms with predictions. Commun ACM "
    "65(7):33–35. doi:10.1145/3528087",
    "Mitzenmacher M (2020) Scheduling with predictions and the price of misprediction. In: "
    "Vidick T (ed) 11th innovations in theoretical computer science conference (ITCS 2020). "
    "Leibniz international proceedings in informatics, vol 151. Schloss Dagstuhl, Dagstuhl, "
    "pp 14:1–14:18. doi:10.4230/LIPIcs.ITCS.2020.14",
    "Fu Y, Zhu S, Su R, Qiao A, Stoica I, Zhang H (2024) Efficient LLM scheduling by learning to "
    "rank. arXiv. doi:10.48550/arXiv.2408.15792",
    "Harchol-Balter M (2013) Performance modeling and design of computer systems: queueing "
    "theory in action. Cambridge University Press, Cambridge. doi:10.1017/CBO9781139226424",
    "Wierman A, Harchol-Balter M (2003) Classifying scheduling policies with respect to "
    "unfairness in an M/GI/1. In: Proceedings of the 2003 ACM SIGMETRICS international conference "
    "on measurement and modeling of computer systems. ACM, New York, pp 238–249. "
    "doi:10.1145/781027.781057",
    "Paszke A, Gross S, Massa F et al (2019) PyTorch: an imperative style, high-performance deep "
    "learning library. arXiv. doi:10.48550/arXiv.1912.01703",
    "Sinyavskiy SD (2026) LoadLens: research branch with code and measurement data. "
    "https://github.com/winlast/loadlens/tree/research. Accessed 1 Nov 2026",
]
