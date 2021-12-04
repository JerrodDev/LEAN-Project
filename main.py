from datetime import timedelta
from AlgorithmImports import *
from SymbolData import SymbolData


class sutulpy(QCAlgorithm):  
    def Initialize(self):            
        #Set backtesting variables
        initialCash = 250000
        self.SetStartDate(2010, 1, 1)
        self.SetEndDate(2020, 1, 1)
        self.SetCash(initialCash)
        self.SetWarmUp(timedelta(days = 20))
        
        #Build a universe set to send to ManualUniverseSelectionModel 
        self.universe = {}       
        self.resolution = Resolution.Daily
        self.SYMBOL = self.AddForex('USDJPY', Resolution.Hour).Symbol
        universeSelection = {
            self.SYMBOL
        }
        self.SetUniverseSelection(ManualUniverseSelectionModel(universeSelection))
        
        #Alpha Creation        
        self.fastPeriod = 25
        self.slowPeriod = 50
        self.trendPeriod = 250
        self.movingAverageType = MovingAverageType.Simple
        self.predictionInterval = Time.Multiply(Extensions.ToTimeSpan(self.resolution), self.fastPeriod)
        
        #Portfolio Construction
        self.portfolioBias = PortfolioBias.LongShort
        self.positionWeight = 0.01

        #Risk Management
        self.atrMultiplier = 1        
        

    # This method gets called at the end of each time slice. A time slice will cover
    # the last available time period of the lowest data resolution subscription 
    def OnData(self, data):  
        #Skip warm up period
        if self.IsWarmingUp: return

        # Manage risk on all current securities  
        symbolData = None      
        for kvp in self.Securities:
            # Get underlying symbol  
            symbol = kvp.Key
            security = kvp.Value

            #Get symbol data
            if symbol in self.universe:
                symbolData = self.universe[symbol]
            if symbolData is None:
                symbolData = SymbolData(security)

            # If current price crosses over the stop level, liquidate
            if symbolData.StopLevel is not None:
                if self.Securities[symbol].Price <= symbolData.StopLevel:
                    self.Liquidate(symbol, 'Liquidated - Stop Level Hit')  

            # If data slice contains this symbol
            if security.Invested and data.ContainsKey(symbol):
                # Initialize trigger bar for symbol on first available data slice, only runs once per symbol instance
                if symbolData.TriggerBarATR is None and symbolData.AverageTrueRange.IsReady:
                    symbolData.TriggerBarATR = symbolData.AverageTrueRange.Current.Value * self.atrMultiplier

                # Initialize stop level for symbol on first available data slice, only runs once per symbol instance
                if symbolData.StopLevel is None and symbolData.TriggerBarATR is not None:
                    symbolData.StopLevel = data[symbol].Low - symbolData.TriggerBarATR

                if security.Type is SecurityType.Forex:
                    # Add QuoteBar to RollingWindow collection 
                    symbolData.QuoteBarWindow[symbol].Add(data[symbol])

                    # Only apply lookback logic if we have enough records
                    if symbolData.QuoteBarWindow[symbol].Count is 3:
                        # If the new low on the previous candle is higher than the low before that,
                        # then the stop level calculation will use this new low
                        if symbolData.QuoteBarWindow[symbol][1].Low > symbolData.QuoteBarWindow[symbol][2].Low:   
                            if symbolData.TriggerBarATR is not None:   
                                symbolData.StopLevel = symbolData.QuoteBarWindow[symbol][1].Low - symbolData.TriggerBarATR 
                elif security.Type is SecurityType.Equity:
                    # Add QuoteBar to RollingWindow collection 
                    symbolData.TradeBarWindow[symbol].Add(data[symbol])

                    # Only apply lookback logic if we have enough records
                    if symbolData.TradeBarWindow[symbol].Count is 3:
                        # If the new low on the previous candle is higher than the low before that,
                        # then the stop level calculation will use this new low
                        if symbolData.TradeBarWindow[symbol][1].Low > symbolData.TradeBarWindow[symbol][2].Low:   
                            if symbolData.TriggerBarATR is not None:   
                                symbolData.StopLevel = symbolData.TradeBarWindow[symbol][1].Low - symbolData.TriggerBarATR
                else:
                    pass                        
            else:
                pass

            #Emit insights for each symbol in the current universe dictionary
            #Ensure indicators are ready
            if symbolData.Fast is not None and symbolData.Slow is not None and symbolData.Trend is not None and symbolData.AverageTrueRange is not None:
                if symbolData.Fast.IsReady and symbolData.Slow.IsReady and symbolData.Trend.IsReady and symbolData.AverageTrueRange.IsReady:    
                    orderFlag = False

                    #If we do not have a direction value yet, create one. If we do have data, grab it
                    if symbolData.Direction is None:
                        symbolData.Direction = InsightDirection.Flat
                        symbolData.LastInsight = self.UtcTime
                        symbolData.FastIsOverSlow = symbolData.Fast > symbolData.Slow
                        symbolData.IsAboveTrendLine = symbolData.Fast > symbolData.Trend and symbolData.Slow > symbolData.Trend           

                    symbolData.IsAboveTrendLine = symbolData.Fast > symbolData.Trend and symbolData.Slow > symbolData.Trend 

                    #If fast MA has crossed slow MA and is above the trend line
                    if symbolData.Fast > symbolData.Slow and symbolData.IsAboveTrendLine:
                        if symbolData.FastIsOverSlow and symbolData.Direction is not InsightDirection.Up:
                            symbolData.Direction = InsightDirection.Up
                            orderFlag = True
                    #If slow MA has crossed fast MA and is below the trend line
                    elif symbolData.Slow > symbolData.Fast and symbolData.IsBelowTrendLine:
                        if symbolData.SlowIsOverFast and symbolData.Direction is not InsightDirection.Down:                                                 
                            symbolData.Direction = InsightDirection.Down
                            orderFlag = True
                    
                    if orderFlag:
                        self.Liquidate(symbol, 'Liquidated - Price Action Change')
                        target = PortfolioTarget.Percent(self, symbol, (symbolData.Direction if self.RespectPortfolioBias(symbolData) else InsightDirection.Flat) * 0.01)
                        quantity = OrderSizing.GetUnorderedQuantity(self, target)
                        self.MarketOrder(symbol, quantity)

                    #Reset comparators for next step
                    symbolData.FastIsOverSlow = symbolData.Fast > symbolData.Slow                     

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
            if added.Type is SecurityType.Forex:
                symbolData.QuoteBarWindow[added.Symbol] = RollingWindow[QuoteBar](3)
            elif added.Type is SecurityType.Equity:
                symbolData.TradeBarWindow[added.Symbol] = RollingWindow[TradeBar](3)
            else:
                pass

            #Add this symbol data to the universe dictionary
            self.universe[added.Symbol] = symbolData

    def RespectPortfolioBias(self, symbolData):
        return self.portfolioBias == PortfolioBias.LongShort or symbolData.Direction == self.portfolioBias