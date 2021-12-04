from datetime import timedelta
from AlgorithmImports import *

class StaticWeightPortfolioConstructionModel(PortfolioConstructionModel):
    def __init__(self, portfolioBias = PortfolioBias.LongShort, positionWeight = 0.01):
        self.portfolioBias = portfolioBias
        self.positionWeight = positionWeight

    def CreateTargets(self, algorithm, insights):
        targets = []
        for insight in insights:
            if self.RespectPortfolioBias(insight):
                weight = self.positionWeight * insight.Direction
                targets.append(PortfolioTarget.Percent(algorithm, insight.Symbol, weight))
        return targets

    def RespectPortfolioBias(self, insight):
        return self.portfolioBias == PortfolioBias.LongShort or insight.Direction == self.portfolioBias
    