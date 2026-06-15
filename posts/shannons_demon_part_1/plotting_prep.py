
import numpy as np
import pandas as pd

from coin_flip_with_riskless_asset_model import CoinFlipWithRisklessAssetModel
from finlib.ensemble_of_returns_paths import EnsembleOfReturnsPaths



 
def growth_rate_summary(paths: EnsembleOfReturnsPaths) -> pd.DataFrame:
    return paths.summarize_across_paths(paths.running_growth_rate, threshold=0.0)
 
 
def wealth_summary(paths: EnsembleOfReturnsPaths) -> pd.DataFrame:
    return paths.summarize_across_paths(paths.running_wealth_ratio, threshold=1.0)



def generate_arithmetic_vs_geometric_data(
    coin_flip_model: CoinFlipWithRisklessAssetModel,
    num_points: int = 1001,
) -> pd.DataFrame:
    """Arithmetic vs geometric portfolio return across the allocation f.

    For each fraction f in [0, 1] placed in the risky asset (the rest in
    the riskless asset), tabulates the competing return notions. The
    arithmetic-geometric gap -- the volatility drag, and the subject of
    the post -- is log(E[Y]) - E[log Y] >= 0 by Jensen's inequality.

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