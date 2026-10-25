# 40/60 baseline portfolio methodology

Implemented: 23 October 2026. This baseline is a transparent comparator, not an optimised allocation or final investment recommendation.

## Assumptions

| Item | Baseline convention |
|---|---|
| Starting capital | USD 10,000,000 |
| Target allocation | 40% SPY, 60% AGG |
| Price input | Frozen adjusted prices from the selected data snapshot |
| Buy-and-hold comparator | Initial 40/60 purchase, then no rebalancing |
| Monthly comparator | Trade after the close of each complete calendar month's final XNYS session |
| Final partial month | No rebalance |
| Costed comparator | 10 basis points (0.10%) on gross traded notional: absolute buys plus absolute sells |
| Initial funding | Opening purchases incur cost in the costed strategy; no borrowing to pay it |
| Fractional holdings | Allowed through value-based accounting |
| Income | Adjusted-price total returns assume distributions are reinvested |

The three output strategies are `buy_and_hold_no_cost`, `monthly_rebalanced_no_cost`, and `monthly_rebalanced_10bps`. The first two isolate rebalancing from transaction cost. The second and third isolate the effect of cost under otherwise identical monthly trading.

## Daily accounting

Holdings are tracked as dollar values. On each new date, each holding is multiplied by its adjusted-price ratio. This allows weights to drift with market performance. If the date is a scheduled rebalance, trades occur after applying that day's returns and at that day's close.

For no-cost rebalancing, each post-trade asset value is its target weight multiplied by pre-trade NAV. For cost rate c, pre-trade values v and target weights w, post-cost NAV x solves:

`x + c * sum(abs(w * x - v)) = sum(v)`

The trade in each asset is `w * x - v`. Gross traded notional is the sum of absolute trades, and transaction cost is c times that gross notional. The resulting identities are checked in code:

- post-cost NAV + transaction cost = pre-trade NAV;
- sum of trades = negative transaction cost;
- post-trade weights equal the target weights.

The opening costed allocation uses investable NAV `initial capital / (1 + c)`, because every opening trade is a purchase. Opening NAV plus opening cost therefore equals USD 10m exactly.

## Metrics

- Cumulative return: ending NAV / USD 10m - 1.
- Annualised return: geometric return using actual calendar days between first and last prices.
- Annualised volatility: sample standard deviation of daily portfolio returns multiplied by square root of 252. The opening purchase cost is excluded; recurring rebalance costs remain in daily returns.
- Maximum drawdown: lowest NAV / prior high-water mark - 1, using USD 10m as the opening high-water mark.

The first daily row records the initial allocation. In the costed strategy its return and drawdown reflect the opening transaction cost. This keeps the economic result measured against the full USD 10m funding amount.

## Output files

Running `uv run --locked python commands/run_portfolio.py` first reproduces the selected data snapshot and then writes files under `output/portfolio/<snapshot-id>/`:

- `portfolio_daily.csv`: daily NAV, return, drawdown, asset values/weights, costs and rebalance flag for all strategies.
- `portfolio_metrics.csv`: comparison metrics.
- `monthly_weights.csv`: weights at the initial date and complete month-ends.
- `transactions.csv`: opening purchases and every scheduled rebalance, including signed trades and costs.
- `baseline_report.md`: readable observed results and limitations.
- `summary.json`: assumptions, source snapshot, output hashes and human-validation status.
- `status.json`: complete/failed pipeline state.

Generated outputs are ignored by Git because the selected frozen snapshot and code reproduce them. The source implementation is in `src/saifa/models/portfolio.py`; orchestration is in `src/saifa/application/portfolio_pipeline.py`; configuration is in `src/saifa/domain/config.py`; automated examples are in `tests/test_portfolio.py`.

## Limitations

This is a full-history descriptive comparison. It does not establish that 40/60 is suitable, optimised or likely to repeat. It does not model taxes, variable bid-ask spreads, price impact, management fees, integer shares, external cash flows or the endowment's actual spending schedule. Ten basis points is a proposed assumption, not a broker quote. Adjusted prices represent reinvested distributions rather than spendable cash income. Later model comparisons must use fixed development/test rules and must not select a portfolio using final test outcomes.

Human accounting validation remains pending until a named team member independently completes and records the [manual accounting check](03-manual-accounting-check.md).
