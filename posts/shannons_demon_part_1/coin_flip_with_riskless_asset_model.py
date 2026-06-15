from dataclasses import dataclass
import warnings
from numpy.typing import NDArray

import numpy as np
import scipy.optimize as opt


@dataclass(frozen=True)
class CoinFlipWithRisklessAssetModel:

    '''
    A dataclass to hold the parameters of a two-asset portfolio, containing
    one riskless asset and one risky asset, which is modeled as a coin flip.
    The risky asset has two possible gross returns, gamma_heads and gamma_tails,
    which occur with probabilities p and 1 - p, respectively. The riskless asset
    has a gross return of r. The parameter alpha determines the risky asset's
    tails gross return via gamma_tails = alpha / gamma_heads.

    Equivalently, alpha = gamma_heads * gamma_tails is the gross return of a
    single heads-then-tails round trip, so alpha = 1 is the "fair" coin
    (gamma_heads * gamma_tails = 1, i.e. the risky asset has zero geometric
    drift when p = 1/2), and larger alpha is a more favourable risky asset. We
    require 0 < alpha < gamma_heads**2 so that gamma_tails > 0 and
    gamma_heads > gamma_tails.

    We consider the random variable
    X = (gross_return_of_riskless_asset, gross_return_of_risky_asset). The portfolio
    gross return Y is given by the dot product of the weights vector [1 - f, f]
    and the returns vector [r, gamma_heads] if heads occurs, and by the dot
    product of the weights vector [1 - f, f] and the returns vector
    [r, gamma_tails] if tails occurs. In other words, Y = CRP . X.

    NB: The probability vector and the CRP are ordered such that the first element
    corresponds to tails and the second element corresponds to heads.
    '''

    gamma_heads: float # gross returns of heads
    p: float # probability of heads
    alpha: float=1.0 # determines the gross return of tails via gamma_tails = alpha/gamma_heads
    r: float=1.0 # gross returns of riskless asset

    def __post_init__(self):

        if not self.gamma_heads > 0:
            raise ValueError(f"gamma_heads must be greater than 0, but got {self.gamma_heads}.")
        if not self.gamma_heads > 1:
            warnings.warn(f"gamma_heads is {self.gamma_heads}, which is not greater than 1. Typically, gamma_heads should be greater than 1. Are you sure you want to proceed?")
        if not 0 <= self.p <= 1:
            raise ValueError(f"p must be in the interval [0, 1], but got {self.p}.")
        if not self.alpha > 0:
            raise ValueError(f"alpha must be greater than 0, but got {self.alpha}.")
        if not self.alpha < self.gamma_heads**2:
            raise ValueError(f"alpha is {self.alpha}, which is not less than (gamma_heads)^2 = {self.gamma_heads**2}. alpha should be less than (gamma_heads)^2 in order for gamma_heads > gamma_tails.")
        if not self.r > 0:
            raise ValueError(f"r must be greater than 0, but got {self.r}.")
        # The E[risky] > r check only concerns a genuine coin (both outcomes
        # possible), and the 0 < p < 1 guard also avoids dividing by p or by
        # (1 - p) below when p hits an endpoint.
        if 0 < self.p < 1 and self.gamma_heads < self.r/self.p:
            min_alpha_for_favourable_risky = self.gamma_heads*(self.r - self.p*self.gamma_heads)/(1 - self.p)
            if self.alpha <= min_alpha_for_favourable_risky:
                warnings.warn(f"When gamma_heads < r/p, alpha must be greater than {min_alpha_for_favourable_risky} for the expected gross return of the risky asset to be greater than r, but got {self.alpha}. Are you sure you want to proceed?")

    @property
    def gamma_tails(self) -> float:
        '''Returns alpha / gamma_heads.'''
        return self.alpha/self.gamma_heads
    @property
    def probabilities_vector(self) -> NDArray[np.float64]:
        '''Returns [1 - p, p].'''
        return np.array([1 - self.p, self.p])
    @property
    def expected_gross_return_of_risky_asset(self) -> float:
        '''Returns p*gamma_heads + (1 - p)*gamma_tails.'''
        return self.p*self.gamma_heads + (1 - self.p)*self.gamma_tails
    @property
    def gross_returns_vector_if_heads(self) -> NDArray[np.float64]:
        '''Returns X when X = [r, gamma_heads].'''
        return np.array([self.r, self.gamma_heads])
    @property
    def gross_returns_vector_if_tails(self) -> NDArray[np.float64]:
        '''Returns X when X = [r, gamma_tails].'''
        return np.array([self.r, self.gamma_tails])
    @property
    def expected_gross_returns_vector(self) -> NDArray[np.float64]:
        '''Returns mu, which is the mean of the gross returns vector, given by p*[r, gamma_heads] + (1 - p)*[r, gamma_tails].'''
        return self.p*self.gross_returns_vector_if_heads + (1 - self.p)*self.gross_returns_vector_if_tails

    def expected_gross_return_of_portfolio(self, CRP: NDArray[np.float64]) -> float:
        '''Returns E[Y] = E[CRP . X] = CRP dot E[X].'''
        return (CRP @ self.expected_gross_returns_vector).item()

    def portfolio_gross_return_if_heads(self, CRP: NDArray[np.float64]) -> float:
        '''Returns the dot product of the CRP and the returns vector [r, gamma_heads].'''
        return (CRP @ self.gross_returns_vector_if_heads).item()

    def portfolio_gross_return_if_tails(self, CRP: NDArray[np.float64]) -> float:
        '''Returns the dot product of the CRP and the returns vector [r, gamma_tails].'''
        return (CRP @ self.gross_returns_vector_if_tails).item()

    def log_portfolio_gross_returns(self, CRP: NDArray[np.float64]) -> NDArray[np.float64]:
        '''Returns the log of the portfolio gross returns for tails and heads, which is a length-2 vector.'''
        t = self.portfolio_gross_return_if_tails(CRP)
        h = self.portfolio_gross_return_if_heads(CRP)
        return np.log(np.array([t, h]))

    def expected_log_portfolio_gross_return(self, CRP: NDArray[np.float64]) -> float:
        '''Returns E[log(Y)] = E[log(CRP . X)]'''
        return (self.probabilities_vector @ self.log_portfolio_gross_returns(CRP)).item()

    def growth_rate(self, CRP: NDArray[np.float64]) -> float:
        '''An alias for expected_log_portfolio_gross_return.'''
        return self.expected_log_portfolio_gross_return(CRP)

    def arithmetic_portfolio_gross_return(self, CRP: NDArray[np.float64]) -> float:
        '''An alias for expected_gross_return_of_portfolio.'''
        return self.expected_gross_return_of_portfolio(CRP)

    def geometric_portfolio_gross_return(self, CRP: NDArray[np.float64]) -> float:
        '''Returns exp(E[log(Y)])'''
        return float(np.exp(self.growth_rate(CRP)))

    def solve_growth_rate_maximization_problem(self) -> opt.OptimizeResult:
        # Bounds f to [0, 1]: the optimal Kelly fraction is sought with no
        # leverage (f <= 1) and no shorting of either asset (f >= 0).
        return opt.minimize_scalar(
            lambda f: -self.growth_rate(np.array([1 - f, f])),
            bounds=(0.0, 1.0),
            method='bounded'
            )     # type: ignore

    def generate_random_gross_returns(self, rng: np.random.Generator, num_periods: int, num_paths: int=1) -> NDArray[np.float64]:
        '''
        Generates a 3D array of shape (num_paths, 2, num_periods) containing random gross returns for the riskless and risky
        assets. The gross returns for the risky asset are generated according to the coin flip model, while the gross returns
        for the riskless asset are constant and equal to r. The gross return at position (i, j, k) corresponds to the gross
        return of asset j in path i at time k.
        '''
        random_coin_flip_gross_returns = rng.choice([self.gamma_tails, self.gamma_heads], size=(num_paths, num_periods), p=self.probabilities_vector)
        riskless_asset_gross_returns = np.full((num_paths, num_periods), self.r)
        return np.stack((riskless_asset_gross_returns, random_coin_flip_gross_returns), axis=1)