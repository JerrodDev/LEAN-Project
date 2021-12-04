from AlgorithmImports import *

class InstantExecutionModel(ExecutionModel):
    def __init__(self):
        self.targetsCollection = PortfolioTargetCollection()

    def Execute(self, algorithm, targets):
        self.targetsCollection.AddRange(targets)

        if self.targetsCollection.Count > 0:
            for target in self.targetsCollection:
                unorderedQuantity = OrderSizing.GetUnorderedQuantity(algorithm, target)
                security = algorithm.Securities[target.Symbol]                                
                if unorderedQuantity != 0:
                    algorithm.MarketOrder(security, unorderedQuantity)
            self.targetsCollection.ClearFulfilled(algorithm)