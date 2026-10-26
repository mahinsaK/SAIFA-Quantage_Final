# Committee evidence and spending methodology

Implemented 26 October 2026. Research proposal only; human recommendation, scenario approval and client policy approval remain separate.

## Evidence and decision

The comparison reuses the verified Phase 09 bundle: same three target allocations, 3 January 2022 to 22 October 2026 costed performance, fixed-USD-10m next-session risk, dated forecasts and retrospective stress replays. No model is refitted or selected to make evaluation tests pass. All 90/95/99% forecasts are retained; the written report emphasises the brief's 95%/99% results.

Proposed decision: **defer implementation under the current proposed mandate**. Retain minimum volatility as a conditional discussion candidate because its development variance objective aligns with preservation. This preference is proposed after viewing evaluation evidence, not an untouched validation result. It does not establish suitability. Every candidate breaches the proposed 15% drawdown review level in 2008 and 2022; every 1.5x hypothetical shock exceeds the separate 10% review level. Coverage/clustering failures and missing actual spending/inflation evidence prevent unconditional acceptance.

The recommendation does not raise risk limits to hide breaches, approve a revised portfolio, or convert research levels into client instructions. Committee responses include reconsidering objectives, researching a different design with fresh validation, or declining the mandate as posed.

## Inflation is absent from the frozen input

`fred.csv` contains `observation_date,DGS3MO`, not CPI. The original policy proposes a disclosed FRED US CPI series, but acquiring it would change the input set and is outside this frozen-data phase. Observed real wealth and actual objective attainment therefore remain **unavailable** (JSON null plus reason).

The sensitivity explicitly assumes constant annual inflation of **0%, 2%, and 4%**. These illustrative rates are not measured inflation, forecasts, client instructions or an exhaustive range of possible outcomes. They are chosen to expose the dependence of remaining purchasing power on inflation. No actual ten-year projection or spending-survival probability is produced.

## Cash-flow rules

- Initial funding is USD 10m. Underlying paths include opening and monthly-rebalance costs at 10 bps on gross buys plus sells.
- Pay on the first observed XNYS session on or after each anniversary of the funding date. First payment: 3% of initial capital, USD 300,000. No payment at inception and no pro-rata withdrawal for the final partial year.
- In this dataset the four payment dates are 3 January 2023, 3 January 2024, 3 January 2025 and 5 January 2026.
- The assumed deflator is `(1 + inflation) ** (days since funding / 365.25)`.
- Subsequent requested payments equal `300000 * deflator(payment date) / deflator(first payment date)`. This fixes the first payment at USD 300,000 and indexes later payments; slight leap-year/holiday effects are explicit.
- Apply the day's return and any scheduled monthly rebalance first. Then liquidate every holding proportionally at that close. The two events are separate, with no assumed trade netting.
- To deliver net cash `W` with sale-cost rate `c`, sell `S = W / (1-c)`; sale fee is `c*S`. Identity: `pre-withdrawal NAV = post-withdrawal NAV + cash paid + sale fee`.
- If net liquidation proceeds are insufficient, pay at most `NAV*(1-c)`, liquidate fully, record the shortfall and leave NAV at zero. Never borrow or silently skip the requested cash flow.

Because liquidations are proportional, weights are unchanged. With fractional holdings and proportional costs, the strategy is homogeneous in capital: future net percentage return factors match the existing strategy, while dollar rebalance costs scale with remaining capital. The spending model reuses that identity rather than refitting or rewriting the original portfolio engine. An independent holdings simulation tests the identity, including a same-day rebalance and withdrawal. Fixed commissions, minimum lots, taxes, liquidity impact and externally imposed cash buffers would invalidate this simplification.

Adjusted prices reinvest distributions. Sales fund the spending scenario; cash dividends are not counted a second time. This is not a dividend-income forecast.

## Interpretation of wealth and objective

For each portfolio/scenario the exports include no-spending nominal and scenario-real wealth, post-spending nominal and scenario-real wealth, total nominal/real payouts, costs, shortfall and remaining-capital growth.

`scenario real NAV = nominal NAV / assumed deflator`.

`annualised real remaining-capital growth = (ending scenario real NAV / initial capital) ** (365.25 / elapsed days) - 1`.

This is growth of capital left in the fund, not a time-weighted investment return or money-weighted return. The before-withdrawal 3% policy objective and the additional stricter after-withdrawal 3% sensitivity remain distinct. Passing an assumed-inflation historical case does not establish actual real-growth attainment or ten-year sustainability.

The legacy performance-ratio module excludes the opening allocation row. Its drawdown/Calmar denominator differs slightly from funded-NAV drawdown, which includes original capital. The report explains this basis difference and preserves both source outputs.

## Reproduction and integrity

```bash
uv sync --locked
uv run --locked python commands/run_app_data.py
uv run --locked python commands/run_submission.py
uv run --locked streamlit run app.py
```

If the Phase 09 bundle is already complete, only the submission command is needed. It does not download data or rebuild forecasts. Outputs:

- `output/decision/<snapshot>/`: comparison, full-period test and traffic-light tables, spending summary, dated paths/payments, decision summary and manifest.
- `output/pdf/<snapshot>/`: investment report, executive tear sheet, committee recommendation, matching readable Markdown and artifact manifest.

The decision extension records the base-bundle digest, Python source hashes and lockfile/policy hash. It also records Git HEAD and dirty state when `.git` is available; a submission ZIP without Git records those two fields as unavailable and remains runnable. The Portfolio page verifies the bundle and source hashes before showing the extension; missing or stale evidence produces a reason and rebuild command while preserving the five original pages. Base inputs remain checked by the original bundle loader. The report uses that same extension; its additional ADF table is checked against the verified data-stage hash. PDFs are deterministic for unchanged content and dependencies.

Generated outputs remain Git-ignored. Package the rebuilt PDFs with the final submission; the reproducible source and included market snapshot remain tracked. A new source/code change requires rebuilding the decision extension. Human review records are not inferred from test results.
