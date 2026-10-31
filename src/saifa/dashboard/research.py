"""Compact research panels; all expensive analysis is prepared offline."""

import altair as alt
import pandas as pd
import streamlit as st

from saifa.dashboard.presentation import money, percent
from saifa.dashboard.research_data import load_research
from saifa.dashboard.selections import backtest_view
from saifa.domain.config import UNIVERSE, BacktestConfig
from saifa.domain.dashboard import STRATEGIES, DashboardBundle, DashboardDataError
from saifa.domain.research import RESEARCH_PORTFOLIOS, VOLATILITY_METHODS, ResearchEvidence


def show(frame: pd.DataFrame, label: str, **kwargs):
    st.dataframe(frame, hide_index=True, width="stretch", alt=label, **kwargs)


def download(frame: pd.DataFrame, filename: str):
    st.download_button(
        "Download displayed research evidence",
        frame.to_csv(index=False),
        file_name=filename,
        mime="text/csv",
        key=f"research_download_{filename}",
    )


def _period(key: str) -> str:
    return st.selectbox(
        "Research comparison period",
        ["evaluation", "validation"],
        format_func=str.capitalize,
        key=key,
    )


def _metrics(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Portfolio": frame.strategy.map(RESEARCH_PORTFOLIOS),
            "Ending value (USD)": frame.ending_value.map(money),
            "Annual return": frame.annualised_return.map(percent),
            "Annual volatility": frame.annualised_volatility.map(percent),
            "Largest drawdown loss": (-frame.maximum_drawdown).map(percent),
            "Trading costs (USD)": frame.total_transaction_cost.map(money),
        }
    )


def allocations(evidence: ResearchEvidence):
    period = _period("lab_allocation_period")
    selected = st.selectbox(
        "Alternative allocation",
        ["minimum_es", "risk_parity"],
        format_func=RESEARCH_PORTFOLIOS.get,
        key="lab_allocation",
    )
    metrics = evidence.tables["candidate_metrics"].query("period == @period")
    st.caption(
        f"{metrics.start_date.iloc[0]} to {metrics.end_date.iloc[0]}; costed monthly-rebalanced portfolios, no withdrawals."
    )
    show(_metrics(metrics), "Same-period comparison of original and alternative allocations")
    weights = evidence.tables["allocation_weights"].set_index("strategy").loc[selected]
    display = pd.DataFrame(
        {
            "ETF": UNIVERSE,
            "Target weight": weights.loc[list(UNIVERSE)].to_numpy(dtype=float),
            "Variance risk share": [weights[f"risk_share_{t}"] for t in UNIVERSE],
        }
    )
    show(
        display,
        "Alternative target capital weights and signed variance risk shares",
        column_config={
            c: st.column_config.NumberColumn(format="percent")
            for c in ("Target weight", "Variance risk share")
        },
    )
    diagnostics = evidence.tables["allocation_diagnostics"].query("strategy == @selected")
    if selected == "risk_parity":
        row = diagnostics.iloc[0]
        achieved = pd.notna(row.get("equal_risk_achieved")) and row.equal_risk_achieved == True
        st.caption(
            "Equal risk achieved within tolerance."
            if achieved
            else "Policy-constrained risk balancing: equal risk was not achieved. See the measured risk shares."
        )
    paths = evidence.tables["candidate_daily"]
    paths = paths.loc[
        (paths.period == period)
        & paths.strategy.isin(["baseline_40_60", "minimum_volatility", selected])
    ].copy()
    paths["Date"] = pd.to_datetime(paths.Date)
    values = paths.pivot(index="Date", columns="strategy", values="nav")
    values.columns = values.columns.map(RESEARCH_PORTFOLIOS)
    st.line_chart(
        values,
        y_label="Portfolio value (USD)",
        alt="Costed performance of the baseline, minimum volatility and selected alternative",
    )
    with st.expander("Read allocation method, trade-offs and solver evidence"):
        st.write(
            "Minimum historical ES minimises the empirical 95% loss tail on development-only returns using a linear programme. Risk parity minimises squared gaps from equal variance-risk shares subject to the same policy. Constraints can prevent exact equality. Both were added after evaluation was viewed; neither is an approved allocation or prospectively validated risk model."
        )
        show(diagnostics, "Alternative development objective and solver evidence")
    download(metrics, f"{period}_alternative_allocations.csv")


def robustness(evidence: ResearchEvidence):
    strategy = st.selectbox(
        "Robustness objective",
        ["minimum_volatility", "maximum_sharpe"],
        format_func=RESEARCH_PORTFOLIOS.get,
        key="lab_robustness",
    )
    frame = evidence.tables["robustness_weights"].query("strategy == @strategy")
    failed = frame.status.ne("ok").sum()
    st.caption(
        f"Development data only · {len(frame) - failed} successful fits · {failed} unavailable fits. These are sensitivity experiments, not confidence guarantees."
    )
    variants = frame.loc[(frame.kind == "prespecified") & (frame.status == "ok")]
    st.bar_chart(
        variants.set_index("variant").one_way_weight_distance * 100,
        y_label="One-way target-weight change (percentage points)",
        alt="Allocation changes caused by prespecified training input variants",
    )
    show(variants, "Development training-window, mean and covariance sensitivities")
    samples = frame.loc[(frame.kind == "block_resample") & (frame.status == "ok"), list(UNIVERSE)]
    if not samples.empty:
        summary = samples.quantile([0.05, 0.5, 0.95]).T.reset_index()
        summary.columns = [
            "ETF",
            "5th percentile weight",
            "Median weight",
            "95th percentile weight",
        ]
        show(
            summary,
            "Descriptive weight dispersion across development block resamples",
            column_config={
                c: st.column_config.NumberColumn(format="percent") for c in summary.columns[1:]
            },
        )
    with st.expander("Read robustness assumptions and failed fits"):
        st.write(
            f"Windows, SPY mean shifts of ±2 annual percentage points, 25% diagonal covariance shrinkage and geometric blocks averaging {evidence.summary['config']['robustness_block']} sessions all use development data. Shrinkage intensity is fixed, not estimated as optimal Ledoit-Wolf shrinkage. Resampling weight percentiles describe sensitivity, not calibrated parameter confidence intervals. No evaluation return selects a variant."
        )
        show(frame.loc[frame.status != "ok"], "Failed robustness fits with explicit reasons")
    download(frame, f"{strategy}_robustness.csv")


def volatility(evidence: ResearchEvidence, original_forecasts: pd.DataFrame | None):
    strategy = st.selectbox(
        "Volatility research portfolio",
        list(STRATEGIES),
        format_func=STRATEGIES.get,
        key="lab_vol_portfolio",
    )
    methods = dict(VOLATILITY_METHODS)
    pool = evidence.tables["volatility_forecasts"]
    if original_forecasts is not None:
        methods.update(
            {"historical": "Historical reference", "parametric_normal": "Static Normal reference"}
        )
        pool = pd.concat([pool, original_forecasts], ignore_index=True)
    method = st.selectbox(
        "Research risk model", list(methods), format_func=methods.get, key="lab_vol_method"
    )
    confidence = st.selectbox(
        "Research confidence",
        [0.90, 0.95, 0.99],
        format_func=lambda c: f"{c:.0%}",
        key="lab_vol_confidence",
    )
    config = BacktestConfig(
        **{
            **evidence.summary["backtest_config"],
            "confidence_levels": tuple(evidence.summary["backtest_config"]["confidence_levels"]),
        }
    )
    first, last = (
        pd.Timestamp(pool.forecast_date.min()).date(),
        pd.Timestamp(pool.forecast_date.max()).date(),
    )
    default_start = max(
        first, pd.Timestamp(evidence.summary["portfolio_config"]["validation_end_exclusive"]).date()
    )
    dates = st.date_input(
        "Research forecast date range (inclusive)",
        value=(default_start, last),
        min_value=first,
        max_value=last,
        key="lab_vol_dates",
    )
    if len(dates) != 2:
        st.info("Choose both dates to calculate model checks.")
        return
    try:
        view = backtest_view(
            pool,
            strategy,
            method,
            confidence,
            *dates,
            config,
            evidence.summary["portfolio_config"]["validation_end_exclusive"],
        )
    except DashboardDataError as exc:
        st.info(str(exc))
        return
    latest = view.forecasts.iloc[-1]
    st.caption(
        f"Latest selected target {latest.forecast_date.date()} · as-of {latest.as_of} · one session · reference NAV {money(latest.reference_nav)}."
    )
    with st.container(horizontal=True):
        st.metric("VaR (USD)", money(latest.var_fraction * latest.reference_nav), border=True)
        st.metric(
            "Expected shortfall (USD)",
            money(latest.es_fraction * latest.reference_nav),
            border=True,
        )
    st.caption(str(latest.warning))
    chart = view.forecasts.copy()
    chart["Loss (USD)"] = chart.loss_fraction * chart.reference_nav
    chart["VaR (USD)"] = chart.var_fraction * chart.reference_nav
    lines = chart.melt(
        id_vars=["forecast_date"],
        value_vars=["Loss (USD)", "VaR (USD)"],
        var_name="Series",
        value_name="USD",
    )
    base = (
        alt.Chart(lines)
        .mark_line()
        .encode(
            x=alt.X("forecast_date:T", title="Forecast target date"),
            y="USD:Q",
            color="Series:N",
            tooltip=["forecast_date:T", "Series:N", alt.Tooltip("USD:Q", format=",.2f")],
        )
    )
    hits = (
        alt.Chart(chart.loc[chart.exception == 1])
        .mark_point(color="#B14F43", filled=True, size=55)
        .encode(
            x="forecast_date:T",
            y="Loss (USD):Q",
            tooltip=["forecast_date:T", "Loss (USD):Q", "VaR (USD):Q"],
        )
    )
    st.altair_chart(
        (base + hits).properties(height=300).interactive(),
        width="stretch",
        alt="Dated risk forecast and actual signed loss; red points are VaR exceptions",
    )
    show(
        view.tests, "Recalculated coverage and independence tests for the selected dated forecasts"
    )
    show(view.lights, "Latest eligible Basel diagnostic within each selected period")
    rejected = (
        view.tests.coverage_decision.eq("reject").any()
        or view.tests.independence_decision.eq("reject").any()
    )
    if rejected:
        st.warning(
            "Selected-range checks reject at least one coverage or independence hypothesis. Non-rejection elsewhere does not establish safety."
        )
    st.caption(
        "Changing the range recalculates tests from dated forecasts. Missing forecasts remain missing; short/sparse sequences can make tests unavailable."
    )
    pair = st.selectbox(
        "EWMA correlation pair", ["SPY / AGG", "SPY / GLD", "SPY / XLK"], key="lab_correlation"
    )
    left, right = pair.split(" / ")
    corr = evidence.tables["correlations"]
    corr = corr.loc[
        (corr.asset_1 == left)
        & (corr.asset_2 == right)
        & corr.forecast_date.between(str(dates[0]), str(dates[1]))
    ].copy()
    corr["Date"] = pd.to_datetime(corr.forecast_date)
    st.line_chart(
        corr.set_index("Date").correlation,
        y_label="Past-only EWMA correlation",
        alt="Time-varying correlation known before each forecast target session",
    )
    with st.expander("Read GARCH, regimes, dependence and fit limitations"):
        st.write(
            f"GARCH variance parameters are fitted annually to the preceding {evidence.summary['config']['volatility_lookback']:,} returns, then updated after each day's observed return. Gaussian variance QMLE conditions on the training sample mean. FHS rescales the training standardized-residual empirical tail. EWMA covariance updates jointly after observed asset returns; it is not a fitted DCC/copula model. All series use frozen target exposures, not monthly drifting NAV returns."
        )
        st.write(
            "High/low prior-volatility labels compare the previous 21 sessions with a development-period median threshold. This is a descriptive diagnostic, not a fitted Markov-switching forecasting model. The models were added after the evaluation period was viewed."
        )
        regimes = (
            view.forecasts.dropna(subset=["regime"])
            if "regime" in view.forecasts
            else pd.DataFrame()
        )
        if not regimes.empty:
            show(
                regimes.groupby("regime", as_index=False).agg(
                    observations=("forecast_date", "size"), exceptions=("exception", "sum")
                ),
                "Exception counts by prior-volatility label; not transition tests across filtered dates",
            )
        show(
            evidence.tables["volatility_fits"].query("strategy == @strategy"),
            "Annual GARCH parameter fits and failures",
        )
    download(view.forecasts, f"{strategy}_{method}_{confidence:.0%}_research_forecasts.csv")


def spending(evidence: ResearchEvidence):
    strategy = st.selectbox(
        "Spending research portfolio",
        list(STRATEGIES),
        format_func=STRATEGIES.get,
        key="lab_spending_portfolio",
    )
    rate = st.selectbox(
        "Initial annual withdrawal",
        [0.02, 0.03, 0.04],
        format_func=lambda c: f"{c:.0%} of initial capital",
        key="lab_spending_rate",
    )
    uplift = st.selectbox(
        "Additional compounded annual inflation uplift",
        [0.0, 0.02],
        format_func=lambda c: f"{c:.0%}",
        key="lab_spending_uplift",
    )
    selected = evidence.tables["spending_summary"].query(
        "strategy == @strategy and withdrawal_rate == @rate and inflation_annual_spread == @uplift"
    )
    row = selected.iloc[0]
    st.warning(
        "Conditional simulation results; these frequencies are not calibrated forecasts of university-fund survival."
    )
    st.caption(
        f"{row.paths:.0f} paths · {row.months / 12:g} simulated years · source {evidence.summary['spending_source_start']}–{evidence.summary['spending_source_end']} ({evidence.summary['spending_source_months']} complete monthly rows)."
    )
    with st.container(horizontal=True):
        st.metric(
            "Paths with no spending shortfall", percent(row.no_shortfall_fraction), border=True
        )
        st.metric("Median ending real wealth", money(row.ending_real_median), border=True)
        st.metric("5th percentile ending real wealth", money(row.ending_real_p05), border=True)
    st.caption(
        f"Conditional Monte Carlo Wilson interval for no shortfall: {row.conditional_wilson_low:.1%}–{row.conditional_wilson_high:.1%}. This excludes model and parameter uncertainty."
    )
    fan = evidence.tables["spending_fan"].query(
        "strategy == @strategy and withdrawal_rate == @rate and inflation_annual_spread == @uplift"
    )
    st.line_chart(
        fan.set_index("month")[["real_p05", "real_median", "real_p95"]].rename(
            columns={
                "real_p05": "5th percentile",
                "real_median": "Median",
                "real_p95": "95th percentile",
            }
        ),
        x_label="Simulated month",
        y_label="Real wealth (USD)",
        alt="Selected spending scenario real-wealth quantiles; not confidence bands for the actual future",
    )
    with st.expander("Read spending assumptions and inspect the joint monthly sample"):
        st.write(evidence.summary["spending_limit"])
        st.write(
            "Joint asset/inflation rows are resampled in geometric blocks, preserving contemporaneous dependence. Missing CPI ratios force block restarts. First payment occurs after month 12 and equals the selected fraction of initial capital; later annual payments track simulated inflation relative to the first payment. Monthly rebalancing and withdrawal-sale costs are funded from the portfolio. The uplift multiplies annual inflation growth by 1.02; it is not an observed rate or an additive two-percentage-point forecast."
        )
        st.write(
            "Actual spending, taxes, fees beyond the stated trading costs and a university-specific inflation benchmark remain unconfirmed. The short recent source excludes 2008 and does not prove ten-year sustainability. The 3% after-spending growth test is a separate stricter hypothetical objective."
        )
        show(
            selected,
            "Complete selected spending simulation outcome and conditional event frequencies",
        )
        show(
            evidence.tables["spending_inputs"],
            "Complete monthly joint return/inflation inputs; missing CPI ratios are not fabricated",
        )
    download(selected, f"{strategy}_{rate:.0%}_{uplift:.0%}_spending_research.csv")


def income(evidence: ResearchEvidence):
    strategy = st.selectbox(
        "Income research portfolio",
        list(RESEARCH_PORTFOLIOS),
        format_func=RESEARCH_PORTFOLIOS.get,
        key="lab_income",
    )
    selected = evidence.tables["income_summary"].query("strategy == @strategy")
    row = selected.iloc[0]
    st.caption(
        f"{row.start_date} to {row.end_date}; constant target exposure at {money(row.reference_nav)} reference NAV."
    )
    st.info(
        "Ex-date distribution proxy only. Actual payment-date cash receipts and tax treatment remain unavailable."
    )
    if row.status == "unavailable":
        st.warning(row.reason)
    else:
        st.metric("Constant-exposure gross distribution proxy", money(row.distribution_proxy_usd))
    ledger = evidence.tables["income_ledger"].query("strategy == @strategy")
    with st.expander("Read income basis and observed distribution evidence"):
        st.write(evidence.summary["income_limit"])
        st.write(
            "The proxy is initial capital × target weight × per-share distribution / previous close, summed over vendor ex-dates after the allocation date. It assumes constant dollar exposure, excludes trading and taxes, and is not a separate holdings/cash account. Split-exposed candidates are withheld pending an independent unit-convention review. Partial ledger rows must not be summed as a complete fund-income result."
        )
        show(selected, "Income proxy availability and explicit missing-input reasons")
        show(ledger, "Partial ex-date observations for eligible non-split exposures")
    download(ledger, f"{strategy}_income_proxy_ledger.csv")


def costs(evidence: ResearchEvidence):
    period = _period("lab_cost_period")
    strategy = st.selectbox(
        "Cost research portfolio",
        list(RESEARCH_PORTFOLIOS),
        format_func=RESEARCH_PORTFOLIOS.get,
        key="lab_cost_portfolio",
    )
    fee = st.selectbox(
        "Assumed additional annual admin fee (bps)", [0.0, 25.0, 50.0], key="lab_admin_fee"
    )
    frame = evidence.tables["cost_metrics"].query(
        "period == @period and strategy == @strategy and additional_annual_fee_bps == @fee"
    )
    show(
        pd.DataFrame(
            {
                "Gross-trade cost (bps)": frame.trade_cost_bps,
                "Ending value (USD)": frame.ending_value.map(money),
                "Annual return": frame.annualised_return.map(percent),
                "Trading costs (USD)": frame.total_transaction_cost.map(money),
                "Additional admin fees (USD)": frame.total_additional_fees.map(money),
            }
        ),
        "Same-target trading and additional administrative fee sensitivity",
    )
    st.line_chart(
        frame.set_index("trade_cost_bps").ending_value,
        x_label="Assumed gross-trade cost (bps)",
        y_label="Ending wealth (USD)",
        alt="Ending wealth under selected portfolio, period and assumed additional admin fee",
    )
    liquidity = evidence.tables["liquidity"].query("strategy == @strategy and period == @period")
    with st.expander("Read cost assumptions and lagged-volume liquidity evidence"):
        st.write(evidence.summary["cost_limit"])
        st.write(
            "The additional admin charge is a continuous annual rate deducted proportionally from NAV, separate from ETF expenses embedded in adjusted prices. No extra liquidation cost is assumed for that charge. Liquidity rows use the original policy-cost trades, not each counterfactual fee scenario. Participation is trade notional divided by the preceding 20 observed sessions' mean Close × Volume. Split units, intraday depth, actual spreads, taxes and calibrated market impact still require data/review."
        )
        show(
            liquidity,
            "Policy-cost trades relative to strictly prior daily volume; not an execution guarantee",
            column_config={"participation_proxy": st.column_config.NumberColumn(format="percent")},
        )
    download(frame, f"{period}_{strategy}_{fee:g}bps_cost_sensitivity.csv")


def render_research(evidence: ResearchEvidence, original_forecasts: pd.DataFrame | None = None):
    st.caption(
        "Retrospective research · human validation pending · separate from the committee recommendation."
    )
    with st.expander("Read research scope, sources and remaining gaps"):
        st.write(evidence.summary["design_status"])
        st.write(
            "Use the research controls below; the sidebar continues to describe the original frozen portfolios. These experiments do not replace final submission evidence or approve an allocation."
        )
        show(evidence.tables["availability"], "Research coverage and inputs still required")
        for source in evidence.summary["sources"]:
            st.markdown(f"[Methodology source]({source})")
    topic = st.selectbox(
        "Research question",
        [
            "Alternative allocations",
            "Allocation robustness",
            "Volatility and dependence",
            "Spending sustainability",
            "Distribution income",
            "Implementation costs",
        ],
        key="lab_topic",
    )
    panels = {
        "Alternative allocations": allocations,
        "Allocation robustness": robustness,
        "Spending sustainability": spending,
        "Distribution income": income,
        "Implementation costs": costs,
    }
    if topic == "Volatility and dependence":
        volatility(evidence, original_forecasts)
    else:
        panels[topic](evidence)


def research_lab_section(bundle: DashboardBundle):
    st.subheader("Portfolio research lab", anchor="portfolio-research")
    try:
        evidence = load_research(bundle.manifest_path.resolve().parents[3], bundle)
    except (DashboardDataError, OSError, ValueError) as exc:
        st.info(
            "Research lab unavailable. Prepare with the normal app launcher or: uv run --locked python commands/run_research.py"
        )
        st.caption(str(exc))
        return
    render_research(evidence, bundle.tables["backtest"]["forecasts"])
