from AlgorithmImports import *
from AlphaCreation.SymbolData import SymbolData

class MACrossMAFilterAlphaModel(AlphaModel):
    def __init__(self, fastPeriod, slowPeriod, trendPeriod, resolution, predictionResolution = Resolution.Hour, predictionPeriod = 1, movingAverageType = MovingAverageType.Simple):
        self.fastPeriod = fastPeriod
        self.slowPeriod = slowPeriod
        self.trendPeriod = trendPeriod
        self.resolution = resolution
        self.movingAverageType = movingAverageType
        self.predictionInterval = Time.Multiply(Extensions.ToTimeSpan(predictionResolution), predictionPeriod)
        self.symbolDataBySymbol = {}
        self.insightsTimeBySymbol = {}        

    def Update(self, algorithm, data):
        insights = []       
        insight = None         
        for symbol, symbolData in self.symbolDataBySymbol.items():
            if symbolData.Fast.IsReady and symbolData.Slow.IsReady and symbolData.Trend.IsReady:
                #Are fast and slow MA above the trend line
                symbolData.IsAboveTrendLine = symbolData.Fast > symbolData.Trend and symbolData.Slow > symbolData.Trend    

                #Has fast MA crossed over slow MA
                symbolData.FastIsOverSlow = symbolData.Fast > symbolData.Slow
                
                direction = InsightDirection.Flat

                #If fast MA has crossed slow MA and is above the trend line
                if symbolData.FastIsOverSlow and symbolData.IsAboveTrendLine:
                    direction = InsightDirection.Up
                #If slow MA has crossed fast MA and is below the trend line
                elif symbolData.SlowIsOverFast and symbolData.IsBelowTrendLine:
                    direction = InsightDirection.Down
                    
                if(symbolData.PreviousDirection == direction):
                    continue

                symbolData.PreviousDirection = direction
                insights.append(Insight.Price(symbolData.Symbol, self.predictionInterval, direction))
                #Reset indicators
                symbolData.Reset()

        return insights

    def OnSecuritiesChanged(self, algorithm, changes):
        for added in changes.AddedSecurities:
            symbolData = self.symbolDataBySymbol.get(added.Symbol)
            if symbolData is None:
                symbolData = SymbolData(added)
                self.symbolDataBySymbol[added.Symbol] = symbolData

                #Set moving average
                if(self.movingAverageType == MovingAverageType.Simple):
                    symbolData.Fast = algorithm.SMA(added.Symbol, self.fastPeriod, self.resolution)
                    symbolData.Slow = algorithm.SMA(added.Symbol, self.slowPeriod, self.resolution)
                    symbolData.Trend = algorithm.SMA(added.Symbol, self.trendPeriod, self.resolution)
                elif(self.movingAverageType == MovingAverageType.Exponential):
                    symbolData.Fast = algorithm.EMA(added.Symbol, self.fastPeriod, self.resolution)
                    symbolData.Slow = algorithm.EMA(added.Symbol, self.slowPeriod, self.resolution)
                    symbolData.Trend = algorithm.EMA(added.Symbol, self.trendPeriod, self.resolution)
                elif(self.movingAverageType == MovingAverageType.DoubleExponential):
                    symbolData.Fast = algorithm.DEMA(added.Symbol, self.fastPeriod, self.resolution)
                    symbolData.Slow = algorithm.DEMA(added.Symbol, self.slowPeriod, self.resolution)
                    symbolData.Trend = algorithm.DEMA(added.Symbol, self.trendPeriod, self.resolution)
                elif(self.movingAverageType == MovingAverageType.TripleExponential):
                    symbolData.Fast = algorithm.TEMA(added.Symbol, self.fastPeriod, self.resolution)
                    symbolData.Slow = algorithm.TEMA(added.Symbol, self.slowPeriod, self.resolution)
                    symbolData.Trend = algorithm.TEMA(added.Symbol, self.trendPeriod, self.resolution)
                else:
                    symbolData.Fast = algorithm.SMA(added.Symbol, self.fastPeriod, self.resolution)
                    symbolData.Slow = algorithm.SMA(added.Symbol, self.slowPeriod, self.resolution)
                    symbolData.Trend = algorithm.SMA(added.Symbol, self.trendPeriod, self.resolution)                
            else:
                symbolData.Reset()

