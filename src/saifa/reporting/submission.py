"""Submission documents composed from the same verified evidence used by the app."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from saifa.dashboard.data import inside, load_bundle
from saifa.dashboard.decision import load_decision
from saifa.data.snapshots import file_hash, write_json
from saifa.domain.config import UNIVERSE
from saifa.domain.dashboard import METHODS, STRATEGIES

SHORT = {
    "baseline_40_60": "Baseline",
    "minimum_volatility": "Min volatility",
    "maximum_sharpe": "Max Sharpe",
}
MODEL = {
    "historical": "Historical",
    "parametric_normal": "Normal",
    "monte_carlo_normal": "Gaussian MC",
    "evt_pot_gpd": "EVT",
}
TEAL = colors.HexColor("#126C68")
INK = colors.HexColor("#163044")


def pct(value):
    return "Unavailable" if pd.isna(value) else f"{value:.2%}"


def usd(value):
    return "Unavailable" if pd.isna(value) else f"${value:,.0f}"


def number(value):
    return "Unavailable" if pd.isna(value) else f"{value:.3f}"


class Document:
    def __init__(self, title, snapshot):
        styles = getSampleStyleSheet()
        self.body = ParagraphStyle(
            "body", fontName="Helvetica", fontSize=10, leading=14, textColor=INK, spaceAfter=9
        )
        self.small = ParagraphStyle("small", parent=self.body, fontSize=8, leading=10)
        self.heading = ParagraphStyle(
            "heading",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=28,
            textColor=INK,
            spaceAfter=16,
        )
        self.subheading = ParagraphStyle(
            "subheading",
            parent=styles["Heading2"],
            textColor=TEAL,
            fontSize=13,
            leading=17,
            spaceAfter=8,
        )
        self.title, self.snapshot = title, snapshot
        self.story, self.text, self.pages = [], [], 0

    def page(self, title, subtitle):
        if self.story:
            self.story.append(PageBreak())
        self.story += [
            Paragraph(escape(title), self.heading),
            Paragraph(escape(subtitle), self.small),
            Spacer(1, 12),
        ]
        self.text += ["\n# " + title, subtitle]

    def p(self, text, heading=None):
        if heading:
            self.story.append(Paragraph(escape(heading), self.subheading))
            self.text.append("\n## " + heading)
        self.story.append(Paragraph(escape(text), self.body))
        self.text.append(text)

    def table(self, headers, rows, widths=None, compact=False):
        cells = [[Paragraph(escape(str(x)), self.small) for x in row] for row in [headers, *rows]]
        table = Table(
            cells,
            colWidths=widths or [499 / len(headers)] * len(headers),
            repeatRows=1,
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E1EFEC")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F4F7F8")],
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 3 if compact else 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3 if compact else 6),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.8, TEAL),
                ]
            )
        )
        self.story += [table, Spacer(1, 12)]
        self.text += [" | ".join(map(str, headers)), *[" | ".join(map(str, row)) for row in rows]]

    def chart(self, frame, ylabel, height=185):
        fig, ax = plt.subplots(figsize=(7.6, height / 72))
        frame.plot(ax=ax, linewidth=1.3, color=["#126C68", "#C17A25", "#466A99"])
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_xlabel("")
        ax.tick_params(labelsize=8)
        ax.legend(fontsize=8, loc="best", frameon=False)
        ax.grid(alpha=0.17)
        fig.tight_layout()
        stream = BytesIO()
        fig.savefig(stream, format="png", dpi=180)
        plt.close(fig)
        stream.seek(0)
        ImageReader(stream)  # Validate the generated image before embedding.
        self.story += [Image(stream, width=499, height=height), Spacer(1, 10)]

    def save(self, path):
        def footer(canvas, doc):
            self.pages = doc.page
            canvas.setStrokeColor(TEAL)
            canvas.line(48, 41, 547, 41)
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(INK)
            canvas.drawString(48, 29, "SAIFA | Team recommendation - client approval pending")
            canvas.drawRightString(547, 29, f"{doc.page}")

        SimpleDocTemplate(
            str(path),
            pagesize=(595, 842),
            rightMargin=48,
            leftMargin=48,
            topMargin=45,
            bottomMargin=55,
            title=self.title,
            author="SAIFA team - AI-assisted draft",
            invariant=1,
        ).build(self.story, onFirstPage=footer, onLaterPages=footer)
        path.with_suffix(".md").write_text("\n\n".join(self.text) + "\n", encoding="utf-8")
        return self.pages


def write_submission(root: Path, snapshot: Path) -> Path:
    bundle = load_bundle(root, root / "output/app" / snapshot.name / "bundle.json")
    decision, evidence = load_decision(root, bundle)
    output = root / "output/pdf" / snapshot.name
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "submission-manifest.json"
    write_json(manifest_path, {"status": "building"})
    comparison = evidence["comparison"].set_index("strategy")
    weights = bundle.tables["risk"]["portfolio_weights"].set_index("strategy")
    risk = bundle.tables["risk"]["risk_comparison"]
    history = bundle.tables["stress"]["historical_summary"]
    hypothetical = bundle.tables["stress"]["hypothetical_summary"]
    tests = evidence["backtest_tests"]
    spend = evidence["spending_summary"]
    observed_real = evidence["observed_real"].set_index("strategy")
    meta = bundle.metadata
    policy = meta["portfolio"]["config"]
    riskmeta = meta["risk"]
    # These extra data diagnostics are hash-verified against the already verified data summary.
    data_folder = inside(root, bundle.manifest["stages"]["data"]["path"])
    adf_path = data_folder / "stationarity.csv"
    if file_hash(adf_path) != meta["data"]["outputs_sha256"]["stationarity.csv"]:
        raise ValueError("Stationarity diagnostic changed; rebuild verified inputs")
    adf = pd.read_csv(adf_path)
    period = f"{comparison.iloc[0].start_date} to {comparison.iloc[0].end_date}"
    context = f"Snapshot {snapshot.name} | Evaluation {period} | USD"
    cost = policy["transaction_cost_bps"]
    report = Document("SAIFA investment committee research report", snapshot.name)

    report.page(
        "A cautious mandate needs a clear decision",
        "Quant Edge 1.0 final | Investment report | " + context,
    )
    report.p(decision["decision"], "Team recommendation for committee consideration")
    report.table(
        ["Candidate", "Ending NAV", "Annual growth", "Worst drawdown"],
        [
            [SHORT[s], usd(r.ending_value), pct(r.annualised_return), pct(-r.maximum_drawdown)]
            for s, r in comparison.iterrows()
        ],
    )
    report.p(
        f"All candidates start with {usd(policy['initial_capital'])} and use monthly "
        f"rebalancing with {cost:g} bps on gross purchases and sales, including initial funding. "
        "These are nominal results with reinvested distributions and no withdrawals."
    )
    report.p(
        "Minimum volatility is a discussion candidate because minimising development variance "
        "matches the preservation priority. This is not a newly validated selection rule: the "
        "evaluation has already been viewed. Maximum Sharpe earned more in this period, while "
        "minimum volatility had less volatility and drawdown. Neither is an approved investment."
    )
    report.p(
        "No candidate passes the proposed crisis drawdown review level in both 2008 and 2022. "
        "One-day risk estimates below their separate review level do not resolve that conflict. "
        "Coverage failures and exception clustering also challenge confidence in the models."
    )
    report.p(decision["inflation_limitation"], "Purchasing power and remaining limits")
    report.p(
        "The team's stated position concerns these three tested allocations, not rejection of "
        "the university's investment mandate itself. Independent calculation checks and "
        "client/committee approval remain open. Any revised objective or portfolio design "
        "needs fresh validation; numerical limits must not be raised solely to pass observed tests."
    )

    report.page("Mandate and portfolio construction", context)
    report.p(
        "The university endowment supports scholarships, research, faculty development and "
        "capital projects. The mandate prioritises capital preservation while seeking income "
        "and sustainable real growth. The proposed strategic horizon is ten years with annual "
        "policy review and monthly monitoring; the available evaluation is much shorter."
    )
    report.p(
        "The draft objective is 3% annualised real growth after modelled trading costs and "
        "before withdrawals and taxes. The spending study additionally tests the stricter "
        "question of 3% real remaining-capital growth after withdrawals. This does not amend "
        "the client policy. No actual spending schedule or client-approved risk budget exists."
    )
    report.table(
        ["Construction rule", "Research proposal"],
        [
            [
                "Funding",
                "Long only; 100% invested; no leverage, derivatives or investable cash sleeve",
            ],
            ["AGG / each ETF", "AGG at least 40%; each ETF at most 60%"],
            [
                "Equity / sectors",
                "Total equity at most 50%; XLE/XLK each at most 10%, combined 15%",
            ],
            ["GLD", "At most 20%"],
            ["Benchmark", "40% SPY / 60% AGG, identical evaluation period and costs"],
        ],
        [135, 364],
    )
    report.table(
        ["Candidate", *UNIVERSE],
        [[SHORT[s], *[pct(weights.loc[s, t]) for t in UNIVERSE]] for s in STRATEGIES],
        [100] + [57] * 7,
    )
    report.p(
        "Markowitz inputs are arithmetic daily means and sample covariance from development "
        "returns through 2018, annualised by 252. SLSQP estimates minimum variance and maximum "
        "excess-return-to-volatility subject to these bounds. A 25-point efficient frontier "
        "documents the feasible return-risk trade-off; estimated means are uncertain."
    )
    report.p(
        "Both candidates reach the AGG ceiling and use gold plus US equities. ETF count is "
        "not independent diversification: SPY and XLK overlap economically. Zero EFA/EEM/XLE "
        "weights are historical constrained optimiser outputs, not universal judgments about "
        "those assets. AGG carries duration and credit risk; GLD provides no contractual income."
    )

    report.page("Data quality and sample discipline", context)
    data = meta["data"]
    report.p(
        f"Frozen Yahoo Finance adjusted prices cover {data['first_price']} to {data['last_return']}: "
        f"{data['prices']:,} aligned price rows and {data['returns']:,} return rows. FRED DGS3MO "
        "supplies the lagged risk-free proxy. The snapshot records source settings and hashes. "
        "Provider revisions mean it is not a point-in-time historical archive."
    )
    report.p(
        "The seven ETFs are aligned to XNYS sessions; common coverage starts with GLD. Missing "
        "held-asset values are not silently filled. Adjusted prices handle splits and reinvested "
        "distributions; distributions are not added again as cash. Log returns support statistical "
        "diagnostics; simple returns preserve exact portfolio P&L and wealth compounding."
    )
    report.p(
        f"Quality checks found {data['blocking_flags']} blocking flags and {data['review_flags']} "
        "review flags (large returns and volatility changes). Genuine crisis moves remain in "
        "the sample. Human disposition is recorded separately; a zero blocking count does not "
        "mean all events have been approved."
    )
    report.table(
        ["ETF", "ADF statistic", "p-value", "Lag"],
        [
            [
                r.ticker,
                f"{r.statistic:.2f}",
                "<1e-16" if r.p_value < 1e-16 else number(r.p_value),
                r.used_lag,
            ]
            for r in adf.itertuples()
        ],
    )
    report.p(
        "ADF uses a constant, AIC lag selection and a 5% test level on the full descriptive "
        "return sample. Rejection of a unit root does not establish constant volatility, "
        "stable dependence or a forecastable distribution."
    )
    report.table(
        ["Period", "Role"],
        [
            ["Through 2018", "Estimate target allocations; inspect development diagnostics"],
            ["2019-2021", "Validation evidence; no allocation refit"],
            ["2022 onward", "Retrospective final evaluation; not a fresh untouched holdout"],
        ],
        [135, 364],
    )

    report.page("Costed historical performance", context)
    report.table(
        ["Candidate", "Cumulative", "Volatility / yr", "Direct costs", "Rebalances"],
        [
            [
                SHORT[s],
                pct(r.cumulative_return),
                pct(r.annualised_volatility),
                usd(r.total_transaction_cost),
                int(r.scheduled_rebalances),
            ]
            for s, r in comparison.iterrows()
        ],
    )
    daily = bundle.tables["portfolio"]["evaluation_daily"].copy()
    daily["Date"] = pd.to_datetime(daily.Date)
    nav = daily.pivot(index="Date", columns="strategy", values="nav").rename(columns=SHORT)
    report.chart(nav / 1e6, "Nominal NAV (USD million)", 180)
    dd = daily.pivot(index="Date", columns="strategy", values="drawdown").rename(columns=SHORT)
    report.chart(-dd * 100, "Loss from running peak (%)", 165)
    report.p(
        "Initial cost is funded from the original capital. At complete month-end closes, "
        "weights return to target after that day's market movement. The solver funds the cost "
        "on both buys and sells from the portfolio. The incomplete final month is not rebalanced."
    )
    report.p(
        "Shown drawdown includes the initial capital as an opening high-water mark. Direct "
        "costs exclude the opportunity cost of future returns on money spent. Taxes, management "
        "fees, variable spreads and price impact are not modelled; 10 bps is an assumption."
    )

    report.page("Performance ratios and what they mean", context)
    report.table(
        ["Measure", *[SHORT[s] for s in STRATEGIES]],
        [
            [label, *[fmt(comparison.loc[s, key]) for s in STRATEGIES]]
            for label, key, fmt in [
                ("Sharpe", "sharpe_ratio", number),
                ("Sortino", "sortino_ratio", number),
                ("SPY beta", "beta", number),
                ("Treynor", "treynor_ratio", pct),
                ("Jensen alpha / yr", "jensen_alpha", pct),
                ("Information ratio", "information_ratio", number),
                ("Calmar", "calmar_ratio", number),
            ]
        ],
    )
    report.p(
        "Sharpe compares arithmetic excess return with total volatility; Sortino uses downside "
        "deviation of excess returns. Treynor divides excess return by market beta. Jensen alpha "
        "is the annualised CAPM regression intercept, not proof of investment skill."
    )
    report.p(
        "CAPM regresses daily portfolio excess returns on SPY excess returns. Risk-free accrual "
        "uses lagged DGS3MO; SPY is an imperfect proxy for a global mixed-asset opportunity set. "
        "Bonds and gold are not well described by equity market beta alone."
    )
    report.p(
        "Information ratio compares active return with tracking error relative to the costed "
        "40/60 baseline. The baseline's self-comparison is undefined, not zero. Calmar divides "
        "annualised geometric return by maximum drawdown magnitude."
    )
    report.p(
        "The existing ratio module excludes the opening allocation row, while wealth-based "
        "drawdown includes the initial funding cost. Therefore ratio-module drawdown and Calmar "
        "use a slightly different opening basis. These outputs are disclosed rather than "
        "silently substituted for the funded-NAV drawdown reported on page 4."
    )
    baseline, minimum, maximum = [comparison.loc[s] for s in STRATEGIES]
    report.p(
        f"Minimum volatility ended {usd(minimum.ending_value - baseline.ending_value)} above "
        f"the baseline. Maximum Sharpe ended {usd(maximum.ending_value - minimum.ending_value)} "
        "above minimum volatility. These realised differences describe one historical sample; "
        "they are not expected future benefits. Minimum volatility retains concentration and "
        "duration exposure despite its lower measured variance."
    )

    report.page("One-session VaR and Expected Shortfall", context)
    report.p(
        f"As-of {riskmeta['as_of']}, forecasting {riskmeta['forecast_session']}; "
        f"{riskmeta['observations']:,} returns from {riskmeta['window_start']}; "
        f"{usd(riskmeta['reference_nav'])} fixed target exposure for every method. "
        "Positive numbers are losses. Percentages below are percentages of that reference NAV, "
        "not of the ending historical portfolio value."
    )
    rows = []
    for s in STRATEGIES:
        for m in METHODS:
            pair = risk[(risk.strategy == s) & (risk.method == m)].set_index("confidence")
            rows.append(
                [
                    SHORT[s],
                    MODEL[m],
                    pct(pair.loc[0.95].var_fraction),
                    pct(pair.loc[0.95].es_fraction),
                    pct(pair.loc[0.99].var_fraction),
                    pct(pair.loc[0.99].es_fraction),
                    usd(pair.loc[0.99].es_usd),
                ]
            )
    report.table(
        ["Candidate", "Method", "VaR 95%", "ES 95%", "VaR 99%", "ES 99%", "ES 99% USD"],
        rows,
        [88, 68, 62, 62, 62, 62, 95],
    )
    report.p(
        "VaR is a quantile loss cutoff. ES is the average loss in the worst tail mass and "
        "captures severity beyond the cutoff. Neither is a loss ceiling. Historical simulation "
        "uses whole asset-return rows, an inverse empirical CDF, and fractional boundary mass "
        "for ES; this preserves observed dependence but cannot invent unseen events."
    )
    report.p(
        "Normal VaR/ES use estimated mean and sample covariance. Gaussian Monte Carlo uses "
        "200,000 correlated scenarios with seed 42; it shares Normal assumptions, so agreement "
        "is expected, not independent confirmation. Fat tails, clustering and regime changes "
        "can undermine both. One-day estimates exclude future trading costs and withdrawals."
    )

    report.page("EVT: tail evidence and uncertainty", context)
    diag = bundle.tables["risk"]["threshold_diagnostics"]
    selected_diag = diag[(diag["period"] == "as_of") & ((diag["quantile"] - 0.90).abs() < 1e-8)]
    report.p(
        "Peaks over threshold fits a Generalised Pareto distribution to losses exceeding the "
        "prespecified 90% loss quantile. That rule was provisionally reviewed after arithmetic "
        "checks; parameter stability is imperfect and it is not established as optimal. "
        "Development/as-of diagnostics, six-threshold sensitivity and block bootstrap expose uncertainty."
    )
    report.table(
        ["Candidate", "Exceedances", "Shape", "Scale", "Fit status"],
        [
            [SHORT[r.strategy], r.exceedances, number(r.shape), number(r.scale), r.status]
            for r in selected_diag.itertuples()
        ],
    )
    evt = risk[(risk.method == "evt_pot_gpd") & (risk.confidence == 0.99)]
    intervals = ["var_ci_low", "var_ci_high", "es_ci_low", "es_ci_high"]
    report.p(
        "At the effective threshold boundary (90% for the current fits), EVT VaR equals the "
        "empirical loss cutoff; ES uses the fitted GPD tail mean. This is not extrapolated VaR "
        "or independent confirmation of Historical VaR. Below-boundary confidence, insufficient "
        "tails and undefined ES remain unavailable. Ties can raise the effective boundary. "
        "Bootstrap intervals are withheld when more than 10% of draws are invalid."
    )
    if intervals:
        report.p(
            "99% estimates: 95% block-bootstrap intervals, expressed as loss fractions in percent."
        )
        report.table(
            ["Candidate", "VaR lower", "VaR upper", "ES lower", "ES upper"],
            [
                [SHORT[r.strategy], *[pct(getattr(r, c)) for c in intervals[:4]]]
                for r in evt.itertuples()
            ],
        )
    report.p(
        "Block-bootstrap intervals describe sensitivity to the available dependent sample "
        "under the chosen procedure. They do not capture all model error, structural change "
        "or events outside the data. High quantiles rely on relatively few extreme losses."
    )
    report.p(
        "EVT is retained as a complementary tail model. Its acceptable 99% evaluation tests "
        "do not justify selecting it after seeing the test results: its 95% coverage rejects "
        "for the optimised candidates. A fresh validation plan is needed for any revised "
        "model or threshold; no tuning was performed to make the final period look favourable."
    )

    report.page("Forecast validation: failures matter", context)
    report.p(
        "Each walk-forward forecast uses 1,000 returns available before its target session. "
        "Weights remain fitted through 2018. Validation and evaluation are separate. The table "
        "shows full evaluation tests at a 5% significance level; it does not cherry-pick dates."
    )
    ev = tests[(tests.period == "evaluation") & (tests.confidence.isin([0.95, 0.99]))]
    report.table(
        ["Candidate / method", "Conf.", "Hits / expected", "Kupiec p", "Indep. p"],
        [
            [
                SHORT[r.strategy] + " / " + MODEL[r.method],
                f"{r.confidence:.0%}",
                f"{int(r.coverage_exceptions)} / {r.coverage_expected_exceptions:.2f}",
                number(r.coverage_p_value),
                number(r.independence_p_value),
            ]
            for r in ev.itertuples()
        ],
        [185, 45, 105, 82, 82],
        compact=True,
    )
    rejection_rows = []
    for name in ("validation", "evaluation"):
        subset = tests[(tests.period == name) & tests.confidence.isin([0.95, 0.99])]
        rejection_rows.append(
            f"{name}: {int((subset.coverage_decision == 'reject').sum())}/{len(subset)} coverage and {int((subset.independence_decision == 'reject').sum())}/{len(subset)} independence rejections"
        )
    report.p(
        "At 5% significance, "
        + "; ".join(rejection_rows)
        + ". Related tests are not independent rankings."
    )
    report.p(
        "Kupiec tests overall frequency; Christoffersen tests clustering. Baseline Historical "
        "99% coverage can look acceptable while independence rejects. Optimised Normal/MC "
        "99% coverage rejects. Sparse transition cells weaken asymptotic inference. "
        "Non-rejection is not proof of safety, and these tests do not validate ES severity."
    )
    report.p(
        "Basel colours require 250 complete sessions at 99%. Latest green windows do not "
        "erase earlier red windows or full-period failures. These are educational diagnostics, "
        "not a regulatory-compliance claim. Detailed statuses and warnings are exported in CSV."
    )

    report.page("Stress losses and risk budgeting", context)
    report.p(
        "Historical crises replay USD 10m at fixed initial allocations with subsequent weight "
        "drift, without rebalancing, costs or withdrawals. The 2008 replay uses actual 2008 "
        "ETF returns: the 40/60 baseline is preset, while the two optimised allocations were "
        "fitted through 2018. None is an actual 2008 investment track record."
    )
    report.table(
        ["Candidate / crisis", "Terminal loss USD", "Peak drawdown", "15% review breach"],
        [
            [
                SHORT[r.strategy] + " / " + r.scenario,
                usd(r.terminal_loss_usd),
                pct(r.maximum_drawdown_fraction),
                str(r.review_trigger_breached),
            ]
            for r in history.itertuples()
        ],
        [200, 110, 100, 89],
    )
    report.table(
        ["Candidate", "Base shock loss", "1.5x shock loss", "10% level at 1.5x"],
        [
            [
                SHORT[s],
                pct(
                    hypothetical[(hypothetical.strategy == s) & (hypothetical.multiplier == 1)]
                    .iloc[0]
                    .loss_fraction
                ),
                pct(
                    hypothetical[(hypothetical.strategy == s) & (hypothetical.multiplier == 1.5)]
                    .iloc[0]
                    .loss_fraction
                ),
                "Breached",
            ]
            for s in STRATEGIES
        ],
    )
    report.p(meta["stress"]["shock_narrative"])
    shocks = meta["stress"]["config"]["stress"]["shocks"]
    report.p(
        "Base ETF shocks: " + ", ".join(f"{t} {pct(v)}" for t, v in shocks) + ". "
        "Multipliers are severities, not event probabilities. Team scenario approval remains pending."
    )
    report.p(
        "Component Normal VaR/ES and Historical ES reconcile to portfolio totals and include "
        "signed offsets. Marginal risk is a derivative; component risk multiplies it by the "
        "position weight. Funded one-percentage-point transfers obey the construction bounds. "
        "These local sensitivities do not prove that a new allocation would survive every crisis."
    )

    report.page("Observed purchasing power", context)
    report.p(
        "The original proposed 3% real-growth objective is before withdrawals. This is a "
        "retrospective measurement of the same costed monthly portfolio paths, from "
        f"{decision['observed_real_start']} through {decision['observed_real_end']}. "
        "CPIAUCSL is monthly: January 2022 and September 2026 price levels are paired with "
        "the first funding session and the final September trading session. October 2026 "
        "portfolio returns are excluded because October CPI was not yet released by the risk as-of date."
    )
    report.table(
        ["Candidate", "Costed nominal", "Observed real", "Real growth / yr", "3% test"],
        [
            [
                SHORT[s],
                usd(r.ending_nominal_wealth),
                usd(r.ending_real_wealth),
                pct(r.annualised_real_growth),
                "Met" if r.objective_met_in_observed_period else "Below",
            ]
            for s, r in observed_real.iterrows()
        ],
    )
    report.p(
        "Observed price-level factor: September 2026 CPI 336.298 / January 2022 CPI "
        "282.543 = 1.190254. Real wealth equals nominal NAV divided by that factor; "
        "annualisation uses 365.25 / elapsed calendar days. All three candidates fall below "
        "3% in this observed period. That period is under five years, so it does not establish "
        "success or failure over the proposed ten-year horizon."
    )
    report.p(
        "CPI source: FRED CPIAUCSL, retrieved 28 October 2026. FRED lists September 2026 "
        "as released on 14 October 2026. October 2025 CPI is missing in the source during "
        "the federal shutdown; no interpolation was made. Endpoint values are observed. "
        "Monthly CPI averages approximate purchasing power at daily NAV dates, and FRED may revise history."
    )
    report.p(
        "These figures contain no withdrawals. The next page keeps the separately labelled "
        "0%, 2% and 4% assumed-inflation spending scenarios; those are not observed CPI outcomes."
    )

    report.page("Spending: a conditional sensitivity", context)
    report.p(decision["inflation_limitation"])
    report.p(decision["payment_rule"])
    report.table(
        [
            "Candidate",
            "Assumed inflation",
            "Nominal ending",
            "Scenario-real ending",
            "Real capital growth / yr",
            "3% after spending?",
        ],
        [
            [
                SHORT[r.strategy],
                pct(r.inflation_assumption),
                usd(r.ending_nominal_wealth),
                usd(r.ending_scenario_real_wealth),
                pct(r.annualised_real_remaining_capital_growth),
                "Yes (scenario)" if r.meets_after_spending_objective else "No (scenario)",
            ]
            for r in spend.itertuples()
        ],
        [95, 64, 89, 89, 82, 80],
    )
    report.p(decision["funding_rule"])
    report.p(
        "Proportional withdrawals preserve portfolio weights. With proportional costs and "
        "fractional holdings, future net percentage returns equal the existing costed strategy. "
        "The calculation scales future rebalancing costs to the remaining capital and adds "
        "the withdrawal sale cost; it does not double-charge the original costed return."
    )
    report.p(decision["objective_note"])
    report.p(
        "Real ending wealth is nominal wealth divided by the assumed price-level factor. "
        "The CSV also reports no-spending nominal/real comparators, cumulative payouts and "
        "any payment shortfall. Remaining-capital growth is not total return: withdrawn money "
        "has left the fund. Adjusted-price gains are not separately identified spendable income."
    )
    report.p(decision["horizon_note"])

    report.page("Decision, conditions and review triggers", context)
    report.p(decision["decision"])
    report.p(
        "Team perspectives supplied on 31 October 2026: Mahinsa favours minimum volatility "
        "only for further preservation research; Lumith highlights clustered VaR exceptions; "
        "Janith highlights crisis and joint-shock breaches; Rayan distinguishes observed "
        "before-withdrawal real growth from unverified spending suitability; Sandanu rejects "
        "immediate implementation pending client needs and a response to model failures. "
        "These positions do not constitute individual calculation sign-offs or client approval."
    )
    for i, condition in enumerate(decision["conditions"], 1):
        report.p(f"{i}. {condition}")
    report.table(
        ["Research review trigger", "Proposed response; requires approval"],
        [
            [
                "One-day 99% ES above 2% NAV",
                "Investigate drivers and model evidence; discuss funded exposure reduction",
            ],
            [
                "Crisis-path drawdown above 15%",
                "Reconsider objectives and portfolio design; cannot claim mandate satisfied",
            ],
            [
                "Hypothetical loss above 10%",
                "Review scenario severity, liquidity and spending needs together",
            ],
            [
                "Coverage / independence rejection",
                "Document model weakness; use multiple risk views and fresh validation",
            ],
            [
                "Missing / stale source evidence",
                "Withhold affected estimate; rebuild and investigate before deciding",
            ],
        ],
        [180, 319],
    )
    report.p(
        "The three thresholds are proposed review levels, not automatic orders, hard "
        "optimisation constraints or client-approved tolerances. No revised allocation has "
        "been computed here to remove the breaches. A future design must be tested without "
        "reusing the observed evaluation as untouched evidence."
    )
    report.p(
        "Real implementation additionally needs approved policy, actual holdings/cash flows, "
        "custodian reconciliation, execution authority and monitoring. The frozen research app "
        "does not trade, monitor live exposures or approve a fund manager's actions."
    )

    report.page("Reproduction, disclosure and evidence", context)
    report.p(
        "Reproduce offline after dependency installation: uv run --locked python "
        "commands/run_app_data.py; then uv run --locked python commands/run_submission.py. "
        "Launch with uv run --locked streamlit run app.py. No market data is downloaded by "
        "these commands. A fresh checkout needs the included frozen snapshot and preparation."
    )
    report.p(
        "The base bundle checks source and result hashes. The decision extension binds to "
        "that exact bundle and records source-code, policy and dependency-lock hashes plus "
        "Git revision and dirty state where .git is present. The submission manifest records artifact "
        "hashes and page counts. Generated outputs are rebuilt, not silently selected from "
        "whichever folder is newest."
    )
    report.p(
        "OpenAI Codex assisted code, tests, spending assumptions, dashboard text and report "
        "composition. The five named team perspectives and final recommendation were supplied "
        "by the team through Mahinsa on 31 October 2026. Earlier material includes AI-assisted "
        "portfolio, risk, EVT, backtesting and stress implementation. This report is not a "
        "claim that every calculation or scenario received independent human approval. Members "
        "must substantiate the figures, explain the methods and record actual reviews in the "
        "phase worksheets and AI-use log."
    )
    report.p(
        "Automated tests check examples, cash-flow identities, scaling, missing evidence, "
        "dated forecasts and UI behavior. Successful tests establish implementation evidence; "
        "they cannot approve a client policy or prove future suitability. Current verification "
        "commands and results are recorded in the Phase 10 milestone."
    )
    report.p(
        "Internal evidence: docs/final/01-planning (requirements, policy, AI disclosure); "
        "03-baseline through 09-streamlit-app (methods and review records); "
        "10-investment-decision (spending, implementation and manual review). "
        "Primary brief: Quant Edge 1.0 Final Challenge, October 2026, pages 3-10."
    )
    report.p(
        "Data references: Yahoo Finance via yfinance; FRED DGS3MO "
        "(https://fred.stlouisfed.org/series/DGS3MO); separate frozen FRED CPIAUCSL "
        "(https://fred.stlouisfed.org/series/CPIAUCSL). Statistical definitions and source "
        "references are documented in the risk, EVT, backtesting and decision methodology files."
    )
    report.p(
        "Final submission deadline supplied by the team: 31 October 2026. Exact cutoff "
        "time, submission route, repository access and individual roster confirmation remain open. "
        "The final-five presentation is separate from this report. Pending reviews are "
        "visible limitations, not completed sign-offs."
    )
    pages = {"investment-report.pdf": report.save(output / "investment-report.pdf")}
    if not 7 <= pages["investment-report.pdf"] <= 15:
        raise ValueError("Report page count outside required 7-15 pages")

    for filename, title in [
        ("executive-tear-sheet.pdf", "Executive tear sheet"),
        ("committee-recommendation.pdf", "Committee recommendation"),
    ]:
        doc = Document(title, snapshot.name)
        doc.page(title, context)
        doc.p(decision["decision"])
        doc.p(
            "Conditional minimum-volatility target: "
            + ", ".join(
                f"{t} {pct(weights.loc['minimum_volatility', t])}"
                for t in UNIVERSE
                if weights.loc["minimum_volatility", t] > 1e-8
            )
            + ". All other eligible ETFs have zero target weight. Research candidate only; no implementation approval."
        )
        if filename.startswith("executive"):
            doc.table(
                ["Candidate", "Ending NAV", "Annual growth", "Worst drawdown"],
                [
                    [
                        SHORT[s],
                        usd(r.ending_value),
                        pct(r.annualised_return),
                        pct(-r.maximum_drawdown),
                    ]
                    for s, r in comparison.iterrows()
                ],
            )
            selected_risk = risk[
                (risk.strategy == "minimum_volatility") & (risk.confidence == 0.99)
            ]
            doc.table(
                ["99% risk method", "VaR % / USD", "ES % / USD"],
                [
                    [
                        MODEL[r.method],
                        f"{pct(r.var_fraction)} / {usd(r.var_usd)}",
                        f"{pct(r.es_fraction)} / {usd(r.es_usd)}",
                    ]
                    for r in selected_risk.itertuples()
                ],
            )
            doc.p(
                f"Performance: monthly rebalancing, {cost:g} bps gross costs, no withdrawals. "
                f"Risk: {riskmeta['as_of']}, next session, fixed USD 10m, before future trading costs."
            )
            doc.p(
                "All candidates breach proposed 15% crisis drawdown in 2008 and 2022; "
                "1.5x hypothetical losses exceed 10%. Optimised Normal/MC 99% coverage rejects; "
                "baseline exceptions cluster. EVT boundary VaR is empirical, with modelled ES. "
                "No model is certified safe."
            )
            doc.p(
                "Observed CPI real growth before withdrawals, 2022-01-03 to 2026-09-30: "
                + ", ".join(
                    f"{SHORT[s]} {pct(observed_real.loc[s, 'annualised_real_growth'])}"
                    for s in STRATEGIES
                )
                + ". All are below the proposed 3% annual target in this shorter historical period."
            )
            two = spend[
                (spend.strategy == "minimum_volatility") & (spend.inflation_assumption == 0.02)
            ].iloc[0]
            doc.p(
                f"Illustrative 2% inflation + annual spending: minimum-volatility ending nominal "
                f"wealth {usd(two.ending_nominal_wealth)}, scenario-real wealth "
                f"{usd(two.ending_scenario_real_wealth)}; real remaining-capital growth "
                f"{pct(two.annualised_real_remaining_capital_growth)} per year. This spending "
                "result uses assumed inflation; the client's actual spending is unknown."
            )
        else:
            doc.p(
                "Why retain this candidate: its development variance objective aligns with "
                "preservation. In the viewed evaluation it reduced volatility and drawdown versus "
                "the baseline, but it remains concentrated in AGG and sensitive to rates. "
                "The higher realised return of maximum Sharpe does not override the mandate."
            )
            doc.p(
                "Why reject immediate implementation: crisis review breaches, model coverage/clustering failures, observed "
                "real growth below 3% in the shorter measured period, and unknown client spending prevent an unconditional suitability "
                "claim. Current daily ES below its separate trigger does not cancel crisis losses. "
                "2008 uses historical returns; only the two optimised weights were fitted later."
            )
            for condition in decision["conditions"]:
                doc.p(condition)
        doc.p(
            "Team recommendation supplied 31 October 2026; AI-assisted document preparation. "
            "Independent checks, scenario review and client policy/allocation approval remain open."
        )
        pages[filename] = doc.save(output / filename)
        if pages[filename] != 1:
            raise ValueError(f"{filename} must be one page, got {pages[filename]}")
    write_json(
        manifest_path,
        {
            "status": "complete",
            "snapshot_id": snapshot.name,
            "source_bundle_sha256": file_hash(bundle.manifest_path),
            "decision_manifest_sha256": file_hash(
                root / "output/decision" / snapshot.name / "manifest.json"
            ),
            "stationarity_sha256": file_hash(adf_path),
            "page_counts": pages,
            "files": {
                p.name: file_hash(p)
                for p in sorted(output.iterdir())
                if p.suffix in {".pdf", ".md"}
            },
            "approval_status": decision["approval_status"],
        },
    )
    return output
