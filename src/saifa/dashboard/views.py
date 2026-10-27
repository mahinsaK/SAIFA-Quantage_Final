"""Judge-facing pages. Read verified outputs; never refit models during a widget rerun."""

import altair as alt
import matplotlib
import numpy as np
import pandas as pd
import streamlit as st

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from saifa.dashboard.presentation import LOSS_COLOR, PORTFOLIO_COLORS, RISK_COLOR, money, percent
from saifa.dashboard.section_navigation import render_section_navigation
from saifa.dashboard.selections import (
    backtest_view,
    frontier_display_data,
    recent_return_correlations,
    select_risk,
)
from saifa.domain.config import UNIVERSE, BacktestConfig
from saifa.domain.dashboard import METHODS, STRATEGIES, DashboardBundle, DashboardDataError


def table(frame, key=None, *, alt="Research results table", column_config=None):
    st.dataframe(
        frame,
        hide_index=True,
        width="stretch",
        key=key,
        alt=alt,
        column_config=column_config,
    )


def download(frame, label, name):
    st.download_button(label, frame.to_csv(index=False).encode(), file_name=name, mime="text/csv")


def portfolio_page(bundle: DashboardBundle, strategy: str):
    from saifa.dashboard.decision import decision_banner, decision_evidence, spending_sensitivity

    st.header("Portfolio performance", anchor="portfolio-page")
    evidence = decision_evidence(bundle)
    sections = [
        ("portfolio-summary", "Summary"),
        ("portfolio-performance", "Performance"),
        ("portfolio-drawdown", "Drawdown"),
        ("portfolio-frontier", "Efficient frontier"),
        ("portfolio-diversification", "Diversification"),
    ]
    render_section_navigation(
        sections, pinned_id="portfolio-summary", aria_label="Portfolio sections"
    )
    if evidence is not None:
        decision_banner(evidence[0])
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
    st.subheader("Selected portfolio at a glance", anchor="portfolio-summary")
    with st.container(horizontal=True):
        for label, value in zip(
            ["Ending value", "Cumulative return", "Annualised return", "Largest drawdown"],
            [
                money(row.ending_value),
                percent(row.cumulative_return),
                percent(row.annualised_return),
                percent(-row.maximum_drawdown),
            ],
        ):
            st.metric(label, value, border=True)
    st.subheader("Compare the three candidates")
    comparison = metrics.copy()
    table(
        pd.DataFrame(
            {
                "Portfolio": comparison.strategy.map(STRATEGIES),
                "Ending value (USD)": comparison.ending_value.map(money),
                "Annualised return": comparison.annualised_return.map(percent),
                "Annualised volatility": comparison.get(
                    "annualised_volatility", pd.Series(np.nan, index=comparison.index)
                ).map(percent),
                "Largest drawdown": (-comparison.maximum_drawdown).map(percent),
                "Trading costs (USD)": comparison.get(
                    "total_transaction_cost", pd.Series(np.nan, index=comparison.index)
                ).map(money),
            }
        ),
        key="portfolio_comparison",
    )
    st.caption(
        "Same evaluation dates and funded accounting for all three candidates. "
        "The table reports historical outcomes, not a forecast or an approved allocation."
    )
    st.subheader("Performance and holdings", anchor="portfolio-performance")
    weights = (
        bundle.tables["risk"]["portfolio_weights"]
        .set_index("strategy")
        .loc[strategy, list(UNIVERSE)]
        .astype(float)
    )
    left, right = st.columns([1, 2])
    with left:
        st.subheader("Target allocation")
        st.bar_chart(
            (weights * 100).rename("Weight (%)"),
            color=PORTFOLIO_COLORS[strategy],
            horizontal=True,
            x_label="ETF",
            y_label="Weight (%)",
            alt=f"Target ETF weights for {STRATEGIES[strategy]} in percent",
        )
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
        st.line_chart(
            values,
            y_label="Value index (initial capital = 100)",
            alt="Historical value index for the three candidate portfolios",
        )
        st.caption(
            "Lines compare all three allocations. Summary figures and the detailed path below follow the selected portfolio. The first plotted value includes initial trading cost."
        )
    selected = daily.loc[daily.strategy == strategy].set_index("Date")
    st.subheader(f"Drawdown · {STRATEGIES[strategy]}", anchor="portfolio-drawdown")
    st.line_chart(
        (-selected.drawdown * 100).rename("Drawdown loss (%)"),
        color=LOSS_COLOR,
        y_label="Loss from running peak (%)",
        alt=f"Historical peak-to-trough drawdown for {STRATEGIES[strategy]} in percent",
    )
    st.caption(
        "Drawdown is shown as a positive loss. The initial USD 10m is included as the opening peak. Holdings drift between month-end rebalances; distributions are reinvested. These performance paths exclude withdrawals; the separate committee sensitivity below models hypothetical spending."
    )
    st.subheader("Development-period efficient frontier", anchor="portfolio-frontier")
    st.caption(
        f"Daily returns before {config['development_end_exclusive']} were used to fit this curve "
        "and the two marked candidates. Both axes are annualised estimates before trading costs. "
        "The 2022 onward performance above is a separate, realised comparison after costs."
    )
    try:
        frontier, candidates = frontier_display_data(
            tables["efficient_frontier"], tables["candidate_weights"]
        )
    except DashboardDataError as exc:
        st.warning(f"Efficient frontier unavailable: {exc}")
    else:
        x = alt.X("Annual volatility (%):Q", scale=alt.Scale(zero=False))
        y = alt.Y("Expected annual return (%):Q", scale=alt.Scale(zero=False))
        tooltip = [
            alt.Tooltip("Annual volatility (%):Q", format=".2f"),
            alt.Tooltip("Expected annual return (%):Q", format=".2f"),
        ]
        curve = (
            alt.Chart(frontier)
            .mark_line(color="#8C9BA5", strokeWidth=2)
            .encode(x=x, y=y, tooltip=tooltip)
        )
        points = (
            alt.Chart(candidates)
            .mark_point(filled=True, size=160)
            .encode(
                x=x,
                y=y,
                color=alt.Color(
                    "Portfolio:N",
                    scale=alt.Scale(
                        domain=[STRATEGIES["minimum_volatility"], STRATEGIES["maximum_sharpe"]],
                        range=[
                            PORTFOLIO_COLORS["minimum_volatility"],
                            PORTFOLIO_COLORS["maximum_sharpe"],
                        ],
                    ),
                    title="Candidate",
                ),
                tooltip=[alt.Tooltip("Portfolio:N"), *tooltip],
            )
        )
        st.altair_chart(
            (curve + points).properties(height=340),
            width="stretch",
            alt="Development efficient frontier with minimum-volatility and maximum-Sharpe candidates",
        )
        st.caption(
            "Higher expected return usually requires more estimated volatility. The two candidates "
            "are close together on this scale; use the values below to compare them."
        )
        table(
            candidates,
            alt="Development expected return and volatility for the two fitted candidates",
            column_config={
                "Annual volatility (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Expected annual return (%)": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
    st.subheader("How do the seven ETFs move together?", anchor="portfolio-diversification")
    try:
        correlations, first, last = recent_return_correlations(
            bundle.tables["data"]["simple_returns"]
        )
    except DashboardDataError as exc:
        st.warning(f"ETF correlation unavailable: {exc}")
    else:
        st.caption(
            f"Pearson correlation of daily simple returns · {first.date()} to {last.date()} "
            "· latest 252 aligned trading sessions in the frozen snapshot. "
            "This is a recent descriptive window, not the pre-2019 optimiser input."
        )
        heatmap = (
            correlations.rename_axis(index="ETF 1", columns="ETF 2")
            .stack()
            .rename("Correlation")
            .reset_index()
        )
        x = alt.X("ETF 1:N", sort=list(UNIVERSE), title="ETF")
        y = alt.Y("ETF 2:N", sort=list(UNIVERSE), title="ETF")
        cells = (
            alt.Chart(heatmap)
            .mark_rect()
            .encode(
                x=x,
                y=y,
                color=alt.Color(
                    "Correlation:Q",
                    scale=alt.Scale(
                        domain=[-1, 0, 1],
                        range=["#B14F43", "#F3F5F6", "#137C73"],
                    ),
                    title="Correlation",
                ),
                tooltip=["ETF 1:N", "ETF 2:N", alt.Tooltip("Correlation:Q", format=".2f")],
            )
        )
        values = (
            alt.Chart(heatmap)
            .mark_text(fontSize=12)
            .encode(
                x=x,
                y=y,
                text=alt.Text("Correlation:Q", format=".2f"),
                color=alt.condition(
                    "abs(datum.Correlation) >= 0.65", alt.value("white"), alt.value("#263238")
                ),
            )
        )
        st.altair_chart(
            (cells + values).properties(height=420),
            width="stretch",
            alt="Correlation matrix of the seven eligible ETFs over the latest 252 aligned sessions",
        )
        st.caption(
            "+1 means returns moved together, −1 means they moved in opposite directions, "
            "and 0 means little linear relationship. Correlations can change, especially in a crisis."
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
    if evidence is not None:
        spending_sensitivity(evidence[0], evidence[1], strategy)


def risk_page(bundle: DashboardBundle, strategy: str, confidence: float, method: str):
    st.header("Risk comparison", anchor="risk-page")
    render_section_navigation(
        [
            ("risk-portfolios", "Portfolios"),
            ("risk-selected", "Selected estimate"),
            ("risk-methods", "Methods"),
        ],
        pinned_id="risk-portfolios",
        aria_label="Risk comparison sections",
    )
    meta = bundle.metadata["risk"]
    st.caption(
        "VaR is a loss cutoff. ES is the average loss beyond that cutoff; neither is a worst-case bound."
    )
    st.caption(
        f"As-of close {meta['as_of']} → next exchange session {meta['forecast_session']} · "
        f"{meta['observations']:,} returns from {meta['window_start']} · reference NAV {money(meta['reference_nav'])} · {confidence:.0%} confidence"
    )
    all_risk = bundle.tables["risk"]["risk_comparison"]
    st.subheader("Three portfolios · selected method", anchor="risk-portfolios")
    peers = all_risk.loc[(all_risk.confidence == confidence) & (all_risk.method == method)].copy()
    peer_display = pd.DataFrame(
        {
            "Portfolio": peers.strategy.map(STRATEGIES),
            "VaR (% NAV)": peers.var_percent,
            "VaR (USD)": peers.var_usd,
            "ES (% NAV)": peers.es_percent,
            "ES (USD)": peers.es_usd,
            "Status": peers.status,
        }
    )
    table(
        peer_display,
        alt="One-session risk comparison across the three candidate portfolios",
        column_config={
            "VaR (% NAV)": st.column_config.NumberColumn(format="%.2f%%"),
            "VaR (USD)": st.column_config.NumberColumn(format="$%.2f"),
            "ES (% NAV)": st.column_config.NumberColumn(format="%.2f%%"),
            "ES (USD)": st.column_config.NumberColumn(format="$%.2f"),
        },
    )
    st.caption(
        "All rows use fixed target exposures and the same USD 10m NAV for one session. "
        "They exclude future trades and differ from the drifting performance NAV. A smaller "
        "one-day estimate does not guarantee a smaller crisis drawdown."
    )
    comparison = select_risk(all_risk, strategy, confidence)
    row = comparison.set_index("method").loc[method]
    st.subheader(f"{STRATEGIES[strategy]} · {METHODS[method]}", anchor="risk-selected")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("VaR (USD)", money(row.var_usd))
    c2.metric("VaR (% NAV)", percent(row.var_fraction))
    c3.metric("ES (USD)", money(row.es_usd))
    c4.metric("ES (% NAV)", percent(row.es_fraction))
    if row.status != "ok" or pd.isna(row.var_fraction) or pd.isna(row.es_fraction):
        st.warning(f"{METHODS[method]}: {row.status}. {row.warning}")
    elif pd.notna(row.warning) and str(row.warning):
        st.caption(str(row.warning))
    evt_row = comparison.set_index("method").loc["evt_pot_gpd"]
    if "Threshold-boundary" in str(evt_row.warning):
        st.caption(
            "EVT at the threshold boundary: VaR equals the empirical loss cutoff; "
            "ES models the average loss beyond it. This VaR is not tail extrapolation "
            "or independent confirmation of Historical VaR."
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
    st.subheader("Four methods · selected portfolio", anchor="risk-methods")
    table(
        display,
        alt="VaR and expected shortfall estimates from four methods for the selected portfolio",
        column_config={
            "VaR (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "VaR (USD)": st.column_config.NumberColumn(format="$%.2f"),
            "ES (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "ES (USD)": st.column_config.NumberColumn(format="$%.2f"),
        },
    )
    chart = comparison.set_index("method")[["var_usd", "es_usd"]].rename(
        columns={"var_usd": "VaR", "es_usd": "ES"}
    )
    chart.index = chart.index.map(METHODS)
    st.bar_chart(
        chart,
        stack=False,
        y_label="Signed loss (USD)",
        alt="VaR and expected shortfall in dollars for each available risk method",
    )
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
                "var_valid_replicates",
                "es_valid_replicates",
                "interval_warning",
            )
        ]
        table(estimates[cols])
        interval_warning = evt_row.get("interval_warning", "")
        if pd.notna(interval_warning) and str(interval_warning):
            st.warning(str(interval_warning))
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
    st.header("Does forecast risk match realised losses?", anchor="backtest-page")
    st.caption("An exception is a next-session loss above the VaR forecast.")
    meta = bundle.metadata["backtest"]
    raw = dict(meta["config"]["backtest"])
    raw["confidence_levels"] = tuple(raw["confidence_levels"])
    config = BacktestConfig(**raw)
    st.caption(
        f"{STRATEGIES[strategy]} · {METHODS[method]} · {confidence:.0%} confidence · inclusive dates {start} to {end} · fixed {money(config.reference_nav)} NAV"
    )
    st.caption("Tests recalculate for these dates; validation and evaluation stay separate.")
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
    render_section_navigation(
        [
            ("backtest-overview", "Overview"),
            *[(f"backtest-{period}", period.title()) for period in view.tests.period],
            ("backtest-forecasts", "Forecasts"),
        ],
        pinned_id="backtest-overview",
        aria_label="Backtesting sections",
    )
    if confidence == 0.90 and method == "evt_pot_gpd":
        st.caption(
            "At the effective 90% threshold boundary, EVT VaR equals the empirical cutoff; "
            "ES uses the fitted tail. These are not extrapolated VaR forecasts. Ties or "
            "failed fits can still make forecasts unavailable; missing rows remain in the tests."
        )
    st.subheader("Backtest at a glance", anchor="backtest-overview")
    overview = view.tests[
        [
            "period",
            "coverage_observations",
            "coverage_exceptions",
            "coverage_missing_forecasts",
            "coverage_p_value",
            "coverage_decision",
            "independence_p_value",
            "independence_decision",
        ]
    ].copy()
    overview["Basel traffic light"] = overview.period.map(
        view.lights.set_index("period").zone
    ).fillna("Unavailable")
    table(
        overview.rename(
            columns={
                "period": "Period",
                "coverage_observations": "Sessions",
                "coverage_exceptions": "Exceptions",
                "coverage_missing_forecasts": "Missing forecasts",
                "coverage_p_value": "Kupiec p-value",
                "coverage_decision": "Kupiec",
                "independence_p_value": "Christoffersen p-value",
                "independence_decision": "Christoffersen",
            }
        ),
        alt="Coverage, clustering and traffic-light findings by validation period",
        column_config={
            "Kupiec p-value": st.column_config.NumberColumn(format="%.3f"),
            "Christoffersen p-value": st.column_config.NumberColumn(format="%.3f"),
        },
    )
    if "reject" in set(view.tests.coverage_decision) | set(view.tests.independence_decision):
        st.error(
            "At least one statistical check rejects. Review the period below before using this risk model."
        )
    elif view.tests.coverage_missing_forecasts.any():
        st.warning("Some forecasts are missing; unavailable tests must not be read as passes.")
    else:
        st.caption("A non-rejection or green traffic light does not prove that the model is safe.")
    for _, row in view.tests.iterrows():
        st.subheader(
            f"{row.period.title()} · {row.start.date()} to {row.end.date()}",
            anchor=f"backtest-{row.period}",
        )
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
        light = view.lights.loc[view.lights.period == row.period].iloc[0]
        if light.status == "ok":
            message = f"Basel {str(light.zone).upper()} · {int(light.exceptions)} exceptions / 250 sessions · {light.start.date()} to {light.end.date()}"
            {"green": st.success, "yellow": st.warning, "red": st.error}[light.zone](message)
        else:
            st.info(f"Basel colour unavailable: {light.warning}")
    st.caption(
        "Basel colours apply only to 99% VaR and 250 complete sessions. These exception tests "
        "do not validate ES severity or establish regulatory compliance."
    )
    st.subheader("Forecasts versus realised losses", anchor="backtest-forecasts")
    plot = view.forecasts
    fig, ax = plt.subplots(figsize=(11, 3.8), layout="constrained")
    ax.plot(
        plot.forecast_date,
        plot.loss_usd,
        color="#8C9BA5",
        linewidth=0.7,
        label="Realised signed loss",
    )
    ax.plot(plot.forecast_date, plot.var_usd, color=RISK_COLOR, linewidth=1, label="Forecast VaR")
    hits = plot.loc[plot.exception == 1]
    ax.scatter(
        hits.forecast_date, hits.loss_usd, color=LOSS_COLOR, s=15, label="Exception", zorder=3
    )
    ax.set(ylabel="One-session loss (USD)", xlabel="Forecast target date")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.15)
    st.pyplot(fig, width="stretch", alt="Realised daily losses, VaR forecasts and exception dates")
    plt.close(fig)
    with st.expander("Audit forecast rows, transition counts and warnings"):
        table(view.tests)
        table(view.forecasts)
    download(view.forecasts, "Download selected dated forecasts", "selected_forecasts.csv")
    download(view.tests, "Download recalculated tests", "selected_backtest_tests.csv")


def _risk_contributions(bundle: DashboardBundle, strategy: str, confidence: float, method: str):
    tables = bundle.tables["stress"]
    st.subheader("Sources of one-session risk", anchor="stress-contributions")
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


def stress_page(bundle: DashboardBundle, strategy: str, confidence: float, method: str):
    st.header("Stress analysis", anchor="stress-page")
    render_section_navigation(
        [
            ("stress-crisis", "Crisis replay"),
            ("stress-compare", "Compare portfolios"),
            ("stress-shock", "Joint shock"),
            ("stress-contributions", "Risk contributions"),
        ],
        pinned_id="stress-crisis",
        aria_label="Stress analysis sections",
    )
    tables, meta = bundle.tables["stress"], bundle.metadata["stress"]
    st.caption(
        f"{STRATEGIES[strategy]} · reference NAV {money(meta['reference_nav'])}. "
        "Crisis and hypothetical losses are scenarios, not probabilities."
    )
    st.subheader("Historical crisis replay", anchor="stress-crisis")
    summary = tables["historical_summary"]
    scenarios = summary.scenario.drop_duplicates().tolist()
    scenario = st.selectbox("Crisis window", scenarios, key="crisis")
    row = summary.loc[(summary.strategy == strategy) & (summary.scenario == scenario)].iloc[0]
    st.caption(
        f"Requested {row.requested_start} to {row.requested_end_exclusive} (end exclusive) · {row.observed_sessions}/{row.expected_sessions} sessions"
    )
    st.caption(
        "Fixed holdings drift without rebalancing, fees or withdrawals; this differs from portfolio performance."
    )
    if scenario == "2008_GFC":
        st.warning(
            "2008 is a retrospective replay: the candidate weights were fitted through 2018 and were unavailable in 2008. This is not a historical investment track record."
        )
    if row.status != "ok":
        st.warning(f"Replay unavailable: {row.warning}")
    else:
        with st.container(horizontal=True):
            st.metric("Terminal loss (USD)", money(row.terminal_loss_usd), border=True)
            st.metric(
                "Largest fall from a previous peak",
                percent(row.maximum_drawdown_fraction),
                border=True,
            )
            st.metric(
                "Peak-to-trough loss (USD)",
                money(row.drawdown_usd_at_max_fraction),
                border=True,
            )
        if row.maximum_drawdown_fraction > row.drawdown_review_level:
            st.error(
                f"Exceeds the proposed {row.drawdown_review_level:.0%} drawdown review level. A final investment response is still required."
            )
        paths = tables["historical_paths"]
        paths = paths.loc[(paths.strategy == strategy) & (paths.scenario == scenario)].copy()
        paths["Date"] = pd.to_datetime(paths.Date)
        st.line_chart(
            paths.set_index("Date").nav.rename("Portfolio value (USD)"),
            color=PORTFOLIO_COLORS[strategy],
            y_label="NAV (USD)",
            alt=f"Historical crisis NAV for {STRATEGIES[strategy]}",
        )
        st.line_chart(
            (paths.set_index("Date").drawdown_fraction * 100).rename("Drawdown loss (%)"),
            color=LOSS_COLOR,
            y_label="Loss from running peak (%)",
            alt=f"Historical crisis drawdown for {STRATEGIES[strategy]}",
        )
        st.caption(
            f"Maximum percentage drawdown uses the actual peak {money(row.peak_nav)} on {row.peak_date} and trough {money(row.trough_nav)} on {row.trough_date}. Terminal loss is measured from initial capital."
        )
    crisis_comparison = summary.loc[summary.scenario == scenario].copy()
    st.subheader("Compare portfolios in this crisis", anchor="stress-compare")
    table(
        pd.DataFrame(
            {
                "Portfolio": crisis_comparison.strategy.map(STRATEGIES),
                "Terminal loss (USD)": crisis_comparison.terminal_loss_usd,
                "Maximum drawdown (%)": crisis_comparison.maximum_drawdown_fraction * 100,
                "Status": crisis_comparison.status,
            }
        ),
        alt="Crisis loss and maximum drawdown for each candidate portfolio",
        column_config={
            "Terminal loss (USD)": st.column_config.NumberColumn(format="$%.2f"),
            "Maximum drawdown (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )
    st.subheader("Hypothetical joint shock", anchor="stress-shock")
    st.caption(meta["shock_narrative"])
    shock_inputs = tables["scenario_shocks"].copy()
    for field in ("base_shock_return", "development_worst_daily_return"):
        if field in shock_inputs:
            shock_inputs[field] *= 100
    shocks = tables["hypothetical_summary"]
    options = sorted(shocks.multiplier.unique())
    multiplier = st.select_slider(
        "Shock severity multiplier", options=options, value=1.0, key="severity"
    )
    shock = shocks.loc[(shocks.strategy == strategy) & (shocks.multiplier == multiplier)].iloc[0]
    with st.container(horizontal=True):
        st.metric("Hypothetical loss (% NAV)", percent(shock.loss_fraction), border=True)
        st.metric("Hypothetical loss (USD)", money(shock.loss_usd), border=True)
    if shock.loss_fraction > shock.review_level:
        st.error(f"Exceeds the proposed {shock.review_level:.0%} hypothetical-loss review level.")
    parts = tables["hypothetical_components"]
    parts = parts.loc[(parts.strategy == strategy) & (parts.multiplier == multiplier)]
    st.bar_chart(
        parts.set_index("ticker").loss_usd.rename("Loss contribution (USD)"),
        color=LOSS_COLOR,
        horizontal=True,
        x_label="ETF",
        y_label="Signed loss (USD)",
        alt="ETF contributions to the selected hypothetical loss",
    )
    with st.expander("Shock inputs and calculation detail"):
        table(
            shock_inputs.rename(
                columns={
                    "ticker": "ETF",
                    "base_shock_return": "Assumed return (%)",
                    "development_worst_daily_return": "Worst development-day return (%)",
                }
            ),
            alt="Assumed ETF shocks and development sample context",
        )
        st.caption(
            "Development minima come from different days. The joint shock is not a jointly observed event or probability."
        )
        table(parts, alt="Selected hypothetical shock contribution detail")
    st.caption(
        "All shocks occur together over one session. Severity is not probability. "
        "Team scenario review is pending; a non-breach is not proof of safety."
    )
    download(parts, "Download selected shock contributions", f"{strategy}_shock.csv")
    _risk_contributions(bundle, strategy, confidence, method)


def assumptions_page(bundle: DashboardBundle):
    st.header("Assumptions and limitations")
    data, risk = bundle.metadata["data"], bundle.metadata["risk"]
    st.warning(
        "Research candidates only. Some backtests reject, crisis review levels are breached, "
        "and the committee has not approved an allocation."
    )
    st.caption(
        "Observed real growth and spending suitability cannot be established: the frozen snapshot "
        "has no CPI series or actual client spending schedule."
    )
    with st.expander("Data sources and reproducibility"):
        st.write(
            f"Frozen snapshot: **{bundle.manifest['snapshot_id']}**. Adjusted ETF prices from Yahoo "
            f"Finance and lagged FRED DGS3MO rates cover {data['first_return']} to {data['last_return']}. "
            f"There are {data['returns']:,} aligned daily returns and {data['review_flags']} review "
            "flags; flagged market events are not automatically deleted."
        )
        st.write(
            "Local outputs are checked for matching hashes and completion status. Controls do not "
            f"download prices. Bundle prepared at {bundle.manifest['prepared_at_utc']}."
        )
    with st.expander("Timing, trading costs and different NAV bases"):
        st.write(
            "Allocations use development data through 2018. Validation is 2019–2021; evaluation "
            "is 2022 onward. Earlier evaluation results have been viewed, so this is retrospective "
            "evidence. Monthly performance charges 10 bps on gross buys plus sells, including "
            "initial funding. Risk forecasts use fixed target exposures and a constant USD 10m; "
            "historical stress compounds fixed initial holdings with no fees or rebalancing."
        )
    with st.expander("Risk models and backtest limits"):
        st.write(
            "Normal models assume thin tails and do not model volatility clustering. Historical "
            "tails use few extreme observations. Gaussian Monte Carlo adds simulation error, not "
            "protection from a wrong distribution. EVT depends on threshold choice, enough "
            "exceedances and fit stability; some ES estimates may be undefined. At the effective "
            "threshold boundary, EVT VaR is the empirical cutoff and ES uses the fitted tail. "
            "Confidence below that boundary (including some tied samples) is unavailable. A 99% Historical ES "
            "based on 1,000 days uses ten observations of tail mass."
        )
        st.write(
            "Coverage and clustering rejections remain in the decision. Non-rejection, a green "
            "traffic light or a low point estimate does not demonstrate safety. Backtests assess "
            "VaR exception frequency/dependence, not ES severity. Stress scenarios do not cover "
            "every crisis or assign probabilities."
        )
    with st.expander("Proposed mandate, spending and unmodelled costs"):
        st.write(
            "The USD 10m endowment seeks preservation, income and real growth. The proposed "
            "2% one-day 99% ES, 15% historical drawdown and 10% hypothetical-loss levels are "
            "research review triggers, not client-approved limits; their horizons and denominators "
            "differ. Breaches require interpretation, not automatic allocation approval."
        )
        st.write(
            "The proposed ten-year horizon and 3% real-growth objective are not forecasts. Adjusted "
            "total returns reinvest distributions and are not all spendable income. Actual spending, "
            "taxes and management fees are unknown. The spending extension assumes 0%, 2% or 4% "
            "inflation with annual withdrawals. No CPI is in the frozen data, so observed purchasing "
            "power and spending sustainability are unestablished. Market impact, bid–ask changes, "
            "forced sales, fractional-share restrictions and intra-day liquidity are unmodelled."
        )
    with st.expander("Human review and build provenance"):
        st.write(
            "Review records are in docs/final by phase. Some arithmetic is signed off, while "
            "output inspection, scenario review and the final recommendation remain open. "
            "Software tests and complete output status do not substitute for human sign-off."
        )
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
