from datetime import timedelta
from AlgorithmImports import *
from QuantConnect.Algorithm.Framework.Alphas.Analysis import InsightManager
from Execution.InstantExecutionModel import InstantExecutionModel 
from PortfolioConstruction.StaticWeightPortfolioConstructionModel import StaticWeightPortfolioConstructionModel
from SymbolData import SymbolData


class sutulpy(QCAlgorithm):  
    def Initialize(self):            
        #Set backtesting variables
        initialCash = 100000
        self.SetStartDate(2018, 1, 1)
        self.SetEndDate(2020, 1, 1)
        self.SetCash(initialCash)
        self.SetWarmUp(timedelta(days = 20))

        #Build a universe set to send to ManualUniverseSelectionModel 
        self.universe = {}       
        self.resolution = Resolution.Daily
        self.USDJPY = self.AddForex('USDJPY', Resolution.Hour).Symbol
        universeSelection = {
            self.USDJPY
        }
        self.SetUniverseSelection(ManualUniverseSelectionModel(universeSelection))
        
        #Alpha Creation        
        self.fastPeriod = 25
        self.slowPeriod = 50
        self.trendPeriod = 200
        self.movingAverageType = MovingAverageType.Exponential

        #Portfolio Construction
        self.positionSize = initialCash * .01

        #Risk Management
        self.atrMultiplier = 1        
        

    # This method gets called at the end of each time slice. A time slice will cover
    # the last available time period of the lowest data resolution subscription 
    def OnData(self, data):  
        #Skip warm up period
        if self.IsWarmingUp: return

        # Manage risk on all current securities        
        for kvp in self.Securities:
            # Get underlying symbol  
            symbol = kvp.Key
            security = kvp.Value

            #Get symbol data
            symbolData = self.universe[symbol]
            if symbolData is None:
                symbolData = SymbolData(security)

            # If data slice contains this symbol
            if data.ContainsKey(symbol):   
                # Add QuoteBar to RollingWindow collection 
                symbolData.QuoteBarWindow[symbol].Add(data[symbol])

                # Initialize trigger bar for symbol on first available data slice, only runs once per symbol instance
                if symbolData.TriggerBarATR is None and symbolData.AverageTrueRange.IsReady:
                    symbolData.TriggerBarATR = symbolData.AverageTrueRange.Current.Value * self.atrMultiplier

                # Initialize stop level for symbol on first available data slice, only runs once per symbol instance
                if symbolData.StopLevel is None and symbolData.TriggerBarATR is not None:
                    symbolData.StopLevel = data[symbol].Low - symbolData.TriggerBarATR

                # Only apply lookback logic if we have enough records
                if symbolData.QuoteBarWindow[symbol].Count is 3:
                    # If the new low on the previous candle is higher than the low before that,
                    # then the stop level calculation will use this new low
                    if symbolData.QuoteBarWindow[symbol][1].Low > symbolData.QuoteBarWindow[symbol][2].Low:   
                        if symbolData.TriggerBarATR is not None:   
                            symbolData.StopLevel = symbolData.QuoteBarWindow[symbol][1].Low - symbolData.TriggerBarATR    

                    # If current price crosses over the stop level, liquidate
                    if symbolData.StopLevel is not None:
                        if self.Securities[symbol].Price <= symbolData.StopLevel:
                            self.Liquidate(symbol)                 
            else:
                pass

            #Emit insights for each symbol in the current universe dictionary
            #Ensure indicators are ready
            if symbolData.Fast is not None and symbolData.Slow is not None and symbolData.Trend is not None and symbolData.AverageTrueRange is not None:
                if symbolData.Fast.IsReady and symbolData.Slow.IsReady and symbolData.Trend.IsReady and symbolData.AverageTrueRange.IsReady:                
                    #If we do not have a direction value yet, create one. If we do have data, grab it
                    if symbolData.Direction is None:
                        symbolData.Direction = InsightDirection.Flat
                
                    #Reset comparators for next step
                    symbolData.ResetComparators()

                    #If fast MA has crossed slow MA and is above the trend line
                    if symbolData.FastIsOverSlow and symbolData.IsAboveTrendLine:
                        if symbolData.Direction is InsightDirection.Up:
                            symbolData.Direction = InsightDirection.Up
                    #If slow MA has crossed fast MA and is below the trend line
                    elif symbolData.SlowIsOverFast and symbolData.IsBelowTrendLine:
                        if symbolData.Direction is not InsightDirection.Down:
                            symbolData.Direction = InsightDirection.Down

                    #If we are not invested
                    if not security.Invested:
                        #Create market order for this symbol
                        quantity = (self.positionSize / symbolData.Security.Price) * symbolData.Direction
                        self.MarketOrder(symbol, quantity)

                else:
                    pass        

                # Add/update symbol data in dictionary
                self.universe[symbol] = symbolData    


    def OnSecuritiesChanged(self, changes):
        #Clean up removed securities
        universe = None
        for removed in changes.RemovedSecurities:
            #If this symbol exists in the universe collection, remove it
            if removed.Symbol in self.universe:
                #Confirm this symbol does not exist in any Universe
                if not self.UniverseManager.TryGetValue(removed.Symbol, universe):
                    #Remove symbol from universe
                    self.universe.pop(removed.Symbol)
            else:
                continue

        #Create symbol data for new securities
        for added in changes.AddedSecurities:
            #If we have already initialized this symbol, move on
            if added.Symbol in self.universe:
                continue

            #Initialize symbol data
            symbolData = SymbolData(added)

            #Set fast, slow, and trend moving average indicators
            if(self.movingAverageType == MovingAverageType.Simple):
                symbolData.Fast = self.SMA(added.Symbol, self.fastPeriod, self.resolution)
                symbolData.Slow = self.SMA(added.Symbol, self.slowPeriod, self.resolution)
                symbolData.Trend = self.SMA(added.Symbol, self.trendPeriod, self.resolution)
            elif(self.movingAverageType == MovingAverageType.Exponential):
                symbolData.Fast = self.EMA(added.Symbol, self.fastPeriod, self.resolution)
                symbolData.Slow = self.EMA(added.Symbol, self.slowPeriod, self.resolution)
                symbolData.Trend = self.EMA(added.Symbol, self.trendPeriod, self.resolution)
            elif(self.movingAverageType == MovingAverageType.DoubleExponential):
                symbolData.Fast = self.DEMA(added.Symbol, self.fastPeriod, self.resolution)
                symbolData.Slow = self.DEMA(added.Symbol, self.slowPeriod, self.resolution)
                symbolData.Trend = self.DEMA(added.Symbol, self.trendPeriod, self.resolution)
            elif(self.movingAverageType == MovingAverageType.TripleExponential):
                symbolData.Fast = self.TEMA(added.Symbol, self.fastPeriod, self.resolution)
                symbolData.Slow = self.TEMA(added.Symbol, self.slowPeriod, self.resolution)
                symbolData.Trend = self.TEMA(added.Symbol, self.trendPeriod, self.resolution)
            else:
                symbolData.Fast = self.EMA(added.Symbol, self.fastPeriod, self.resolution)
                symbolData.Slow = self.EMA(added.Symbol, self.slowPeriod, self.resolution)
                symbolData.Trend = self.EMA(added.Symbol, self.trendPeriod, self.resolution)    

            #Initialize AverageTrueRange indicator
            symbolData.AverageTrueRange = self.ATR(added.Symbol, 14, MovingAverageType.Wilders, self.resolution)

            #Initialize symbol data properties
            symbolData.QuoteBarWindow[added.Symbol] = RollingWindow[QuoteBar](3)

            #Add this symbol data to the universe dictionary
            self.universe[added.Symbol] = symbolData

