"""Judge-facing pages. Read verified outputs; never refit models during a widget rerun."""

import matplotlib
import numpy as np
import pandas as pd
import streamlit as st

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from saifa.dashboard.selections import backtest_view, select_risk
from saifa.domain.config import UNIVERSE, BacktestConfig
from saifa.domain.dashboard import METHODS, STRATEGIES, DashboardBundle, DashboardDataError


def money(value):
    return "Unavailable" if pd.isna(value) else f"${value:,.2f}"


def percent(value):
    return "Unavailable" if pd.isna(value) else f"{value:.2%}"


def table(frame, key=None):
    st.dataframe(frame, hide_index=True, width="stretch", key=key)


def download(frame, label, name):
    st.download_button(label, frame.to_csv(index=False).encode(), file_name=name, mime="text/csv")


def portfolio_page(bundle: DashboardBundle, strategy: str):
    from saifa.dashboard.decision import decision_summary

    st.header("Portfolio performance")
    decision_summary(bundle, strategy)
    st.write(
        "Compare what the three allocations earned and how far their value fell during the same evaluation period."
    )
    tables, metadata = bundle.tables["portfolio"], bundle.metadata["portfolio"]
    config = metadata["config"]
    metrics = tables["evaluation_metrics"]
    row = metrics.set_index("strategy").loc[strategy]
    st.caption(
        f"{row.start_date} to {row.end_date} · initial capital {money(config['initial_capital'])} · "
        f"monthly rebalancing · {config['transaction_cost_bps']:g} bps on gross buys + sells, including initial funding"
    )
    st.info(
        "Weights were fitted through 2018; performance shown here is the 2022 onward evaluation. This period has already been viewed, so the evaluation is retrospective."
    )
    cols = st.columns(4)
    for col, label, value in zip(
        cols,
        ["Ending value", "Cumulative return", "Annualised return", "Largest drawdown"],
        [
            money(row.ending_value),
            percent(row.cumulative_return),
            percent(row.annualised_return),
            percent(-row.maximum_drawdown),
        ],
    ):
        col.metric(label, value)
    weights = (
        bundle.tables["risk"]["portfolio_weights"]
        .set_index("strategy")
        .loc[strategy, list(UNIVERSE)]
        .astype(float)
    )
    left, right = st.columns([1, 2])
    with left:
        st.subheader("Target allocation")
        st.bar_chart((weights * 100).rename("Weight (%)"), color="#126C68", y_label="Weight (%)")
        table(
            pd.DataFrame(
                {"ETF": weights.index, "Target weight (%)": (weights * 100).round(3).values}
            )
        )
    with right:
        st.subheader("Growth of the initial capital")
        daily = tables["evaluation_daily"].copy()
        daily["Date"] = pd.to_datetime(daily.Date)
        # Include original capital so the opening transaction cost remains visible.
        values = (
            daily.pivot(index="Date", columns="strategy", values="nav")
            / config["initial_capital"]
            * 100
        )
        values.columns = [STRATEGIES[c] for c in values.columns]
        st.line_chart(values, y_label="Value index (initial capital = 100)")
        st.caption(
            "Lines compare all three allocations. Summary figures and the detailed path below follow the selected portfolio. The first plotted value includes initial trading cost."
        )
    selected = daily.loc[daily.strategy == strategy].set_index("Date")
    st.subheader(f"Drawdown · {STRATEGIES[strategy]}")
    st.line_chart(
        (-selected.drawdown * 100).rename("Drawdown loss (%)"),
        color="#B24C35",
        y_label="Loss from running peak (%)",
    )
    st.caption(
        "Drawdown is shown as a positive loss. The initial USD 10m is included as the opening peak. Holdings drift between month-end rebalances; distributions are reinvested. These performance paths exclude withdrawals; the separate committee sensitivity above models hypothetical spending."
    )
    with st.expander("Performance measures and latest holdings"):
        comparison = metrics.merge(
            tables["performance_ratios"], on="strategy", suffixes=("", "_ratio")
        )
        table(comparison)
        weightcols = [f"{t}_weight" for t in UNIVERSE]
        latest = selected.iloc[-1].reindex(weightcols).to_numpy(dtype=float)
        # Baseline CSV omits never-held ETFs. Missing held-asset weights stay unavailable.
        latest = np.where(np.isnan(latest) & (weights.to_numpy() == 0), 0, latest)
        table(pd.DataFrame({"ETF": UNIVERSE, "Latest weight (%)": latest * 100}))
        st.caption(
            "Blank ratios are mathematically undefined; they are not zero. CAPM uses SPY as an imperfect mixed-asset market proxy."
        )
    download(
        selected.reset_index(), "Download selected portfolio path", f"{strategy}_performance.csv"
    )


def risk_page(bundle: DashboardBundle, strategy: str, confidence: float, method: str):
    st.header("One-session risk")
    meta = bundle.metadata["risk"]
    st.write(
        "VaR is a loss cutoff; Expected Shortfall (ES) estimates the average loss in the worst tail. Neither is a maximum possible loss."
    )
    st.caption(
        f"As-of close {meta['as_of']} → next exchange session {meta['forecast_session']} · "
        f"{meta['observations']:,} returns from {meta['window_start']} · reference NAV {money(meta['reference_nav'])} · {confidence:.0%} confidence"
    )
    st.info(
        "These estimates use fixed target exposures at USD 10m for one session. They exclude future trades and do not use the drifted NAV shown on the performance page."
    )
    comparison = select_risk(bundle.tables["risk"]["risk_comparison"], strategy, confidence)
    row = comparison.set_index("method").loc[method]
    st.subheader(f"{STRATEGIES[strategy]} · {METHODS[method]}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("VaR (USD)", money(row.var_usd))
    c2.metric("VaR (% NAV)", percent(row.var_fraction))
    c3.metric("ES (USD)", money(row.es_usd))
    c4.metric("ES (% NAV)", percent(row.es_fraction))
    if row.status != "ok" or pd.isna(row.var_fraction) or pd.isna(row.es_fraction):
        st.warning(f"{METHODS[method]}: {row.status}. {row.warning}")
    elif pd.notna(row.warning) and str(row.warning):
        st.caption(str(row.warning))
    if confidence == 0.90:
        st.warning(
            "EVT at 90% is unavailable: the selected POT threshold is also 90%, so this confidence lies at the threshold boundary. Historical, Normal and Gaussian Monte Carlo remain available. No higher-confidence value is substituted."
        )
    display = pd.DataFrame(
        {
            "Method": comparison.method.map(METHODS),
            "VaR (%)": comparison.var_percent,
            "VaR (USD)": comparison.var_usd,
            "ES (%)": comparison.es_percent,
            "ES (USD)": comparison.es_usd,
            "Status": comparison.status,
            "Reason / limitation": comparison.warning.fillna(""),
        }
    )
    st.subheader("Compare methods on identical inputs")
    table(display)
    chart = comparison.set_index("method")[["var_usd", "es_usd"]].rename(
        columns={"var_usd": "VaR", "es_usd": "ES"}
    )
    chart.index = chart.index.map(METHODS)
    st.bar_chart(chart, stack=False, y_label="Signed loss (USD)")
    st.caption(
        "Blank cells mean unavailable. A negative signed-loss estimate represents a gain at that quantile. Gaussian Monte Carlo and Parametric Normal share distribution assumptions and should be close within simulation error."
    )
    with st.expander("EVT diagnostics and uncertainty"):
        estimates = comparison.loc[comparison.method == "evt_pot_gpd"]
        cols = [
            c
            for c in estimates
            if c.startswith(("var_ci", "es_ci", "bootstrap"))
            or c
            in (
                "threshold_quantile",
                "threshold",
                "exceedances",
                "shape",
                "scale",
                "status",
                "warning",
            )
        ]
        table(estimates[cols])
        diagnostics = bundle.tables["risk"]["threshold_diagnostics"]
        table(diagnostics.loc[diagnostics.strategy == strategy])
        sensitivity = bundle.tables["risk"]["threshold_sensitivity"]
        table(
            sensitivity.loc[
                (sensitivity.strategy == strategy) & (sensitivity.confidence == confidence)
            ]
        )
        st.caption(
            "The provisional 90% threshold was not selected to improve evaluation performance. Tail fits are sample-sensitive; uncertainty and unreliable/undefined values remain visible."
        )
    download(
        comparison, "Download selected risk comparison", f"{strategy}_risk_{confidence:.0%}.csv"
    )


def backtest_page(
    bundle: DashboardBundle, strategy: str, confidence: float, method: str, start, end
):
    st.header("Does forecast risk match realised losses?")
    st.write(
        "An exception occurs when the next-session loss is strictly greater than the forecast VaR. Equality is not an exception."
    )
    meta = bundle.metadata["backtest"]
    raw = dict(meta["config"]["backtest"])
    raw["confidence_levels"] = tuple(raw["confidence_levels"])
    config = BacktestConfig(**raw)
    st.caption(
        f"{STRATEGIES[strategy]} · {METHODS[method]} · {confidence:.0%} confidence · inclusive dates {start} to {end} · fixed {money(config.reference_nav)} NAV"
    )
    st.info(
        "Statistics are recalculated for your selected dates. Validation and evaluation remain separate; the latest Basel window resets at each period boundary and at your selected start date."
    )
    try:
        view = backtest_view(
            bundle.tables["backtest"]["forecasts"],
            strategy,
            method,
            confidence,
            start,
            end,
            config,
            meta["validation_end_exclusive"],
        )
    except DashboardDataError as exc:
        st.warning(str(exc))
        return
    if confidence == 0.90 and method == "evt_pot_gpd":
        st.warning(
            "90% EVT forecasts are unavailable at the 90% POT threshold. Missing forecasts are retained, so coverage and independence are unavailable rather than passed."
        )
    for _, row in view.tests.iterrows():
        st.subheader(f"{row.period.title()} · {row.start.date()} to {row.end.date()}")
        cols = st.columns(4)
        for col, label, value in zip(
            cols,
            [
                "Observed exceptions",
                "Expected exceptions",
                "Forecast sessions",
                "Missing forecasts",
            ],
            [
                str(row.coverage_exceptions) if row.coverage_valid_forecasts else "Unavailable",
                f"{row.coverage_expected_exceptions:.2f}",
                str(row.coverage_observations),
                str(row.coverage_missing_forecasts),
            ],
        ):
            col.metric(label, value)
        if row.coverage_missing_forecasts:
            st.warning(
                "Some forecasts are unavailable. Exception counts include only available forecasts; "
                "coverage and independence tests are unavailable for this incomplete sequence."
            )
        tests = pd.DataFrame(
            [
                {
                    "Test": "Kupiec · overall frequency",
                    "p-value": row.coverage_p_value,
                    "Decision at 5%": row.coverage_decision,
                    "Caution": row.coverage_warning,
                },
                {
                    "Test": "Christoffersen · clustering",
                    "p-value": row.independence_p_value,
                    "Decision at 5%": row.independence_decision,
                    "Caution": row.independence_warning,
                },
            ]
        )
        table(tests)
        if "reject" in (row.coverage_decision, row.independence_decision):
            st.error(
                "A test rejects its assumption in this selection. Retain this result in the investment decision."
            )
        light = view.lights.loc[view.lights.period == row.period].iloc[0]
        if light.status == "ok":
            message = f"Basel {str(light.zone).upper()} · {int(light.exceptions)} exceptions / 250 sessions · {light.start.date()} to {light.end.date()}"
            {"green": st.success, "yellow": st.warning, "red": st.error}[light.zone](message)
        else:
            st.info(f"Basel colour unavailable: {light.warning}")
    st.caption(
        "Non-rejection and a green window do not establish safety. The Basel thresholds apply only to 99% and 250 complete sessions; they are a historical diagnostic, not a compliance claim. VaR exception tests do not validate ES severity."
    )
    plot = view.forecasts
    fig, ax = plt.subplots(figsize=(11, 3.8), layout="constrained")
    ax.plot(
        plot.forecast_date,
        plot.loss_usd,
        color="#8C9BA5",
        linewidth=0.7,
        label="Realised signed loss",
    )
    ax.plot(plot.forecast_date, plot.var_usd, color="#126C68", linewidth=1, label="Forecast VaR")
    hits = plot.loc[plot.exception == 1]
    ax.scatter(
        hits.forecast_date, hits.loss_usd, color="#B24C35", s=15, label="Exception", zorder=3
    )
    ax.set(ylabel="One-session loss (USD)", xlabel="Forecast target date")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.15)
    st.pyplot(fig, width="stretch")
    plt.close(fig)
    with st.expander("Audit forecast rows, transition counts and warnings"):
        table(view.tests)
        table(view.forecasts)
    download(view.forecasts, "Download selected dated forecasts", "selected_forecasts.csv")
    download(view.tests, "Download recalculated tests", "selected_backtest_tests.csv")


def stress_page(bundle: DashboardBundle, strategy: str, confidence: float, method: str):
    st.header("Stress and sources of risk")
    tables, meta = bundle.tables["stress"], bundle.metadata["stress"]
    st.caption(
        f"{STRATEGIES[strategy]} · reference NAV {money(meta['reference_nav'])}. Risk attribution uses {confidence:.0%} confidence; crisis and hypothetical losses are scenarios with no confidence level assigned."
    )
    st.subheader("Which assets contribute to one-session risk?")
    attribution = tables["asset_contributions"]
    attribution = attribution.loc[
        (attribution.strategy == strategy) & (attribution.confidence == confidence)
    ]
    supported = method in ("historical", "parametric_normal")
    if not supported:
        st.info(
            f"{METHODS[method]} attribution is not implemented. The table below explicitly compares Historical ES and Normal VaR/ES; it does not substitute either for the selected model."
        )
    else:
        attribution = attribution.loc[attribution.method == method]
    totals = tables["contribution_summary"]
    totals = totals.loc[(totals.strategy == strategy) & (totals.confidence == confidence)]
    if supported:
        totals = totals.loc[totals.method == method]
    display_totals = totals[
        ["method", "measure", "total_percent", "total_usd", "status", "warning"]
    ].copy()
    display_totals["method"] = display_totals.method.map(METHODS)
    display_totals["measure"] = display_totals.measure.str.upper()
    table(
        display_totals.rename(
            columns={
                "method": "Method",
                "measure": "Measure",
                "total_percent": "Risk (% NAV)",
                "total_usd": "Risk (USD)",
                "status": "Status",
                "warning": "Limitation",
            }
        )
    )
    display_assets = attribution[
        [
            "ticker",
            "weight",
            "method",
            "measure",
            "component_percent",
            "component_usd",
            "share_percent",
        ]
    ].copy()
    display_assets["weight"] *= 100
    display_assets["method"] = display_assets.method.map(METHODS)
    display_assets["measure"] = display_assets.measure.str.upper()
    table(
        display_assets.rename(
            columns={
                "ticker": "ETF",
                "weight": "Weight (%)",
                "method": "Method",
                "measure": "Measure",
                "component_percent": "Contribution (% NAV)",
                "component_usd": "Contribution (USD)",
                "share_percent": "Share of total risk (%)",
            }
        )
    )
    with st.expander("Marginal exposure derivatives"):
        table(attribution[["ticker", "method", "measure", "marginal_fraction"]])
    st.caption(
        "Components sum to portfolio risk when defined. Negative components offset risk. A marginal describes an exposure increase; a funded transfer uses the difference between receiver and donor marginals. Historical ES allocates portfolio-tail loss, not standalone ETF ES."
    )
    with st.expander("Funded 1 percentage point transfers"):
        transfers = tables["sizing_checks"]
        transfers = transfers.loc[
            (transfers.strategy == strategy) & (transfers.confidence == confidence)
        ]
        if supported:
            transfers = transfers.loc[transfers.method == method]
        table(transfers)
        st.caption(
            "Use exact repricing for finite changes. Infeasible transfers have reasons. This sensitivity table excludes trading costs and does not recommend a trade."
        )
    st.subheader("Historical crisis replay")
    summary = tables["historical_summary"]
    scenarios = summary.scenario.drop_duplicates().tolist()
    scenario = st.selectbox("Crisis window", scenarios, key="crisis")
    row = summary.loc[(summary.strategy == strategy) & (summary.scenario == scenario)].iloc[0]
    st.caption(
        f"Requested {row.requested_start} to {row.requested_end_exclusive} (end exclusive) · {row.observed_sessions}/{row.expected_sessions} sessions"
    )
    st.info(
        "Fixed initial holdings compound with drifting weights. No rebalancing, fees or withdrawals. These retrospective replays are separate from the monthly-rebalanced performance comparison."
    )
    if scenario == "2008_GFC":
        st.warning(
            "2008 is a retrospective replay: the candidate weights were fitted through 2018 and were unavailable in 2008. This is not a historical investment track record."
        )
    if row.status != "ok":
        st.warning(f"Replay unavailable: {row.warning}")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Terminal loss (USD)", money(row.terminal_loss_usd))
        c2.metric("Maximum drawdown", percent(row.maximum_drawdown_fraction))
        c3.metric("Peak-to-trough loss (USD)", money(row.drawdown_usd_at_max_fraction))
        if row.maximum_drawdown_fraction > row.drawdown_review_level:
            st.error(
                f"Exceeds the proposed {row.drawdown_review_level:.0%} drawdown review level. A final investment response is still required."
            )
        paths = tables["historical_paths"]
        paths = paths.loc[(paths.strategy == strategy) & (paths.scenario == scenario)].copy()
        paths["Date"] = pd.to_datetime(paths.Date)
        st.line_chart(
            paths.set_index("Date").nav.rename("Portfolio value (USD)"),
            color="#126C68",
            y_label="NAV (USD)",
        )
        st.line_chart(
            (paths.set_index("Date").drawdown_fraction * 100).rename("Drawdown loss (%)"),
            color="#B24C35",
            y_label="Loss from running peak (%)",
        )
        st.caption(
            f"Maximum percentage drawdown uses the actual peak {money(row.peak_nav)} on {row.peak_date} and trough {money(row.trough_nav)} on {row.trough_date}. Terminal loss is measured from initial capital."
        )
    with st.expander("Compare all portfolios in this crisis"):
        table(summary.loc[summary.scenario == scenario])
    st.subheader("Hypothetical joint shock")
    st.write(meta["shock_narrative"])
    shock_inputs = tables["scenario_shocks"].copy()
    for field in ("base_shock_return", "development_worst_daily_return"):
        if field in shock_inputs:
            shock_inputs[field] *= 100
    table(
        shock_inputs.rename(
            columns={
                "ticker": "ETF",
                "base_shock_return": "Assumed return (%)",
                "development_worst_daily_return": "Worst development-day return (%)",
            }
        )
    )
    st.caption(
        "ETF shock inputs above are percentages. Development minima are context from different historical days, not a jointly observed scenario or a probability."
    )
    shocks = tables["hypothetical_summary"]
    options = sorted(shocks.multiplier.unique())
    multiplier = st.select_slider(
        "Shock severity multiplier", options=options, value=1.0, key="severity"
    )
    shock = shocks.loc[(shocks.strategy == strategy) & (shocks.multiplier == multiplier)].iloc[0]
    c1, c2 = st.columns(2)
    c1.metric("Hypothetical loss (% NAV)", percent(shock.loss_fraction))
    c2.metric("Hypothetical loss (USD)", money(shock.loss_usd))
    if shock.loss_fraction > shock.review_level:
        st.error(f"Exceeds the proposed {shock.review_level:.0%} hypothetical-loss review level.")
    parts = tables["hypothetical_components"]
    parts = parts.loc[(parts.strategy == strategy) & (parts.multiplier == multiplier)]
    st.bar_chart(
        parts.set_index("ticker").loss_usd.rename("Loss contribution (USD)"),
        color="#B24C35",
        y_label="Signed loss (USD)",
    )
    table(parts)
    st.caption(
        "All shocks occur together over one hypothetical session. The multiplier changes severity, not probability. These are research assumptions awaiting team scenario review; a non-breach is not approval or proof of safety."
    )
    download(parts, "Download selected shock contributions", f"{strategy}_shock.csv")


def assumptions_page(bundle: DashboardBundle):
    st.header("Assumptions, limitations and provenance")
    data, risk = bundle.metadata["data"], bundle.metadata["risk"]
    st.write(
        "The fund's USD 10m mandate balances preservation, income and real growth. The three displayed allocations are research candidates; no final committee recommendation has been approved."
    )
    st.subheader("Data and reproducibility")
    st.write(
        f"Frozen snapshot: **{bundle.manifest['snapshot_id']}**. Adjusted ETF prices from Yahoo Finance and lagged FRED DGS3MO rates cover {data['first_return']} to {data['last_return']}. There are {data['returns']:,} aligned daily returns. The recorded data review flags number {data['review_flags']}; flagged market events are not automatically deleted."
    )
    st.write(
        "The app reads local outputs and verifies their hashes and completion status. Opening or changing controls does not download prices. The bundle was prepared at "
        + bundle.manifest["prepared_at_utc"]
        + "."
    )
    st.subheader("Timing and accounting")
    st.write(
        "Allocations use development data through 2018. Validation is 2019–2021; evaluation is 2022 onward. Earlier evaluation results have been viewed, so this is retrospective evidence. Monthly performance charges 10 bps on gross buys plus sells, including initial funding. Risk forecasts use fixed target exposures and a constant USD 10m; historical stress compounds fixed initial holdings with no fees or rebalancing."
    )
    st.subheader("Models can fail")
    st.write(
        "Normal models assume thin tails and do not model volatility clustering. Historical tails use few extreme observations. Gaussian Monte Carlo adds simulation error, not protection from a wrong distribution. EVT depends on threshold choice, enough exceedances and fit stability; some ES estimates may be undefined. At 90% confidence, the current 90% EVT threshold makes that estimate unavailable. A 99% Historical ES based on 1,000 days uses ten observations of tail mass."
    )
    st.write(
        "Coverage and clustering rejections must remain in the decision. Non-rejection, a green traffic light or a low point estimate does not demonstrate safety. The backtests test VaR exception frequency/dependence, not ES severity. Stress scenarios do not exhaust possible crises or assign probabilities."
    )
    st.subheader("Client assumptions still need a decision")
    st.write(
        "The 2% one-day 99% ES, 15% historical drawdown and 10% hypothetical-loss levels are proposed research review triggers, not client-approved limits. They have different horizons and denominators. Breaches require interpretation; the app does not automatically approve an allocation."
    )
    st.write(
        "The proposed ten-year horizon and 3% real-growth objective are not established forecasts. Adjusted total returns reinvest distributions and are not all spendable income. No client spending schedule, inflation-adjusted withdrawal plan, tax profile or management fee is known. The committee extension illustrates 0%, 2% and 4% assumed inflation with annual withdrawals. No CPI series is in the frozen data, so actual purchasing-power growth and spending sustainability remain unestablished. Market impact, bid–ask changes, forced sales, fractional-share restrictions and intra-day liquidity are unmodelled."
    )
    st.subheader("Human review")
    st.write(
        "Human calculations and approval records are maintained in docs/final by phase. Some arithmetic is signed off, while output inspection, scenario review and the final recommendation remain open. Software tests and a complete output status do not substitute for human sign-off."
    )
    with st.expander("Recorded configuration and build provenance"):
        st.json(
            {
                "snapshot": bundle.manifest["snapshot_id"],
                "risk": risk["config"],
                "backtest": bundle.metadata["backtest"]["config"],
                "bundle": bundle.manifest,
            }
        )
    st.markdown(
        "Method references: [Euler risk allocation](https://arxiv.org/abs/0708.2542) · [BCBS stress testing principles](https://www.bis.org/publications/201810-guidelines-stress-testing-principles)"
    )
