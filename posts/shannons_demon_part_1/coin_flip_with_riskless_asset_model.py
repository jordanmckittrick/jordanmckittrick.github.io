

from dataclasses import dataclass
import warnings

import numpy as np
import scipy.optimize as opt



@dataclass(frozen=True)
class CoinFlipWithRisklessAssetModel:

    '''
    A dataclass to hold the parameters of a two-asset portfolio, containing
    one riskless asset and one risky asset, which is modeled as a coin flip. 
    The risky asset has two possible gross returns, gamma_heads and gamma_tails, 
    which occur with probabilities p and 1 - p, respectively. The riskless asset
    has a gross return of r. The parameter alpha is used to determine the gross
    return of the risky asset in the tails state, which is given by 1/(alpha*gamma_heads).

    We consider the random variable 
    X = (gross_return_of_riskless_asset, gross_return_of_risky_asset). The portfolio
    gross return Y is given by the dot product of the weights vector [1 - f, f]
    and the returns vector [r, gamma_heads] if heads occurs, and by the dot 
    product of the weights vector [1 - f, f] and the returns vector
    [r, gamma_tails] if tails occurs. In other words, Y = weights_vector . X.
    '''

    gamma_heads: float # gross returns of heads
    p: float # probability of heads
    alpha: float=0.0
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
        if not self.alpha > (self.gamma_heads)**-2:
            raise ValueError(f"alpha is {self.alpha}, which is not greater than (gamma_heads)^-2 = {(self.gamma_heads)**-2}. alpha should be greater than (gamma_heads)^-2 in order for gamma_heads > gamma_tails.")
        if not self.r > 0:
            raise ValueError(f"r must be greater than 0, but got {self.r}.")
        if self.gamma_heads < self.r/self.p:
            if self.alpha >= (1 - self.p)/(self.gamma_heads*(self.r - self.p*self.gamma_heads)):
                warnings.warn(f"When gamma_heads < r/p, alpha must be less than {(1 - self.p)/(self.gamma_heads*(self.r - self.p*self.gamma_heads))} for the expected gross return of the risky asset to be greater than r, but got {self.alpha}. Are you sure you want to proceed?")

    @property
    def gamma_tails(self) -> float:
        '''Returns 1/(alpha * gamma_heads).'''
        return 1/(self.alpha*self.gamma_heads)
    @property
    def probabilities_vector(self) -> np.ndarray:
        '''Returns [1 - p, p].'''
        return np.array([1 - self.p, self.p])
    @property
    def expected_gross_return_of_risky_asset(self) -> float:
        '''Returns p*gamma_heads + (1 - p)*gamma_tails.'''
        return self.p*self.gamma_heads + (1 - self.p)*self.gamma_tails
    @property
    def gross_returns_vector_if_heads(self) -> np.ndarray:
        '''Returns X when X = [r, gamma_heads].'''
        return np.array([self.r, self.gamma_heads])
    @property
    def gross_returns_vector_if_tails(self) -> np.ndarray:
        '''Returns X when X = [r, gamma_tails].'''
        return np.array([self.r, self.gamma_tails])
    @property
    def expected_gross_returns_vector(self) -> np.ndarray:
        '''Returns mu, which is the mean of the gross returns vector, given by p*[r, gamma_heads] + (1 - p)*[r, gamma_tails].'''
        return self.p*self.gross_returns_vector_if_heads + (1 - self.p)*self.gross_returns_vector_if_tails

    def return_expected_gross_return_of_portfolio(self, weights_vector: np.ndarray) -> float:
        '''Returns E[Y] = E[weights_vector . X] = weights_vector dot E[X].'''
        return np.dot(weights_vector, self.expected_gross_returns_vector)

    def return_portfolio_gross_return_if_heads(self, weights_vector: np.ndarray) -> float:
        '''Returns the dot product of the weights_vector and the returns vector [r, gamma_heads].'''
        return np.dot(weights_vector, self.gross_returns_vector_if_heads)
    
    def return_portfolio_gross_return_if_tails(self, weights_vector: np.ndarray) -> float:
        '''Returns the dot product of the weights_vector and the returns vector [r, gamma_tails].'''
        return np.dot(weights_vector, self.gross_returns_vector_if_tails)        
    
    def return_log_portfolio_gross_returns(self, weights_vector: np.ndarray) -> np.ndarray:
        '''Returns the log of the portfolio gross returns for tails and heads, which is a length-2 vector.'''
        t = self.return_portfolio_gross_return_if_tails(weights_vector)
        h = self.return_portfolio_gross_return_if_heads(weights_vector)
        return np.log(np.array([t, h]))

    def return_expected_log_portfolio_gross_return(self, weights_vector: np.ndarray) -> float:
        '''Returns E[log(Y)] = E[log(weights_vector . X)]'''
        return np.dot(self.probabilities_vector, self.return_log_portfolio_gross_returns(weights_vector))

    def return_growth_rate(self, weights_vector: np.ndarray) -> float:
        '''An alias for return_expected_log_portfolio_gross_return.'''
        return self.return_expected_log_portfolio_gross_return(weights_vector)

    def return_expected_portfolio_gross_return(self, weights_vector: np.ndarray) -> float:
        '''Returns E[Y] = E[weights_vector . X] = weights_vector . E[X].'''
        return np.dot(weights_vector, self.expected_gross_returns_vector)       

    def return_arithmetic_portfolio_gross_return(self, weights_vector: np.ndarray) -> float:
        '''An alias for return_expected_portfolio_gross_return.'''
        return self.return_expected_portfolio_gross_return(weights_vector)

    def return_geometric_portfolio_gross_return(self, weights_vector: np.ndarray) -> float:
        '''Returns exp(E[log(Y)])'''
        return np.exp(self.return_growth_rate(weights_vector))
    
    def solve_growth_rate_maximization_problem(self) -> opt.OptimizeResult:
        return opt.minimize_scalar(
            lambda f: -self.return_growth_rate(np.array([1-f, f])),
            bounds=(0.0, 1.0),
            method='bounded'
            )     # type: ignore
    

