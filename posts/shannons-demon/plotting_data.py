
import numpy as np
import pandas as pd
import scipy.stats as ss

from coin_flip_with_riskless_asset_model import CoinFlipWithRisklessAssetModel




def generate_arithmetic_vs_geometric_data(
    coin_flip_model: CoinFlipWithRisklessAssetModel,
    num_points: int = 1001,
) -> pd.DataFrame:
    """Arithmetic vs geometric portfolio return across the allocation f.

    For each fraction f in [0, 1] placed in the risky asset (the rest in
    the riskless asset), tabulates the competing return notions. The
    arithmetic-geometric gap -- the volatility drag, and the subject of
    the post -- is log(E[Y]) - E[log Y] >= 0 by Jensen's inequality.

    The returned df has columns:
    arithmetic_gross_return: E[Y]
    growth_rate: E[log Y]
    geometric_gross_return: exp(E[log Y])
    growth_rate_ceiling: log(E[Y])
    arithmetic_geometric_gap: log(E[Y]) - E[log Y]

    Returns a tidy frame, one row per f, indexed by f.
    """
    f = np.linspace(0.0, 1.0, num_points)
    rows = []
    for fi in f:
        weights = np.array([1 - fi, fi])
        arithmetic = coin_flip_model.arithmetic_portfolio_gross_return(weights)  # E[Y]
        growth_rate = coin_flip_model.expected_log_portfolio_gross_return(weights)  # E[log Y]
        rows.append((arithmetic, growth_rate))

    df = pd.DataFrame(rows, columns=["Arithmetic Gross Return", "Growth Rate"])
    df.insert(0, "f", f)
    # Geometric return and ceiling are transforms of the two columns above:
    df["Geometric Gross Return"] = np.exp(df["Growth Rate"])      # exp(E[log Y])
    df["Growth Rate Ceiling"] = np.log(df["Arithmetic Gross Return"])  # log(E[Y]), Jensen
    df["Arithmetic-Geometric Gap"] = df["Growth Rate Ceiling"] - df["Growth Rate"]
    return df.set_index("f")


def generate_no_loss_probability_data(
    coin_flip_model: CoinFlipWithRisklessAssetModel,
    num_periods: int,
) -> pd.DataFrame:
    """P(no loss) = P(S_n >= 1) over n = 1..num_periods, exact and bounded.

    The path avoids a loss iff the number of heads k in n flips is at least
    ``ceil(cut * n)``, where ``cut`` is the critical fraction of heads needed
    for a non-negative growth rate (the post's ``c``). Two series, indexed by
    period n:

    Exact:           the exact tail probability P(k >= ceil(cut * n)) via the
                     binomial survival function.
    Chernoff bound:  the large-deviation upper bound exp(-n * D_KL) -- the
                     dominant (exponential) factor of Sanov's bound, without
                     the loose (n+1)^2 prefactor. This is the Chernoff bound
                     for a binomial tail; it upper-bounds the exact probability
                     for every n while decaying at the same rate Sanov captures.

    D_KL is evaluated at the exact break-even fraction ``cut`` rather than at
    the integer-corrected ``ceil(cut*n)/n``: the no-loss event is {k/n >= cut},
    so exp(-n * D(cut || p)) is a valid bound at every n with a single rate --
    a straight line in log space -- at the price of being very slightly weaker
    than the per-n integer bound. Matches the value quoted in the post.
    """
    p = coin_flip_model.p
    cut = -np.log(coin_flip_model.gamma_tails) / (
        np.log(coin_flip_model.gamma_heads) - np.log(coin_flip_model.gamma_tails)
    )
    n = np.arange(1, num_periods + 1)
    heads_needed = np.ceil(cut * n)
    exact = ss.binom.sf(heads_needed - 1, n, p)   # P(k >= heads_needed)

    D_KL = cut * np.log(cut / p) + (1 - cut) * np.log((1 - cut) / (1 - p))
    chernoff = np.exp(-n * D_KL)

    return pd.DataFrame(
        {"Exact": exact, "Chernoff bound": chernoff},
        index=pd.RangeIndex(1, num_periods + 1, name="period"),
    )