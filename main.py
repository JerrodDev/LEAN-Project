from datetime import timedelta
from AlgorithmImports import *
from Execution.InstantExecutionModel import InstantExecutionModel 
from AlphaCreation.MACrossMAFilterAlphaModel import MACrossMAFilterAlphaModel
from PortfolioConstruction.StaticWeightPortfolioConstructionModel import StaticWeightPortfolioConstructionModel

class sutulpy(QCAlgorithm):  
    def Initialize(self):            
        #Set backtesting variables
        initialCash = 100000
        self.SetStartDate(2010, 1, 1)
        self.SetEndDate(2020, 1, 1)
        self.SetCash(initialCash)
        self.SetWarmUp(timedelta(days = 20))

        #Set Universe Selection
        self.universe = []
        self.USDJPY = self.AddForex('USDJPY', Resolution.Hour)
        self.SetUniverseSelection(ManualUniverseSelectionModel(self.USDJPY))
        
        #Alpha Creation
        self.AddAlpha(MACrossMAFilterAlphaModel(
            fastPeriod = 25,
            slowPeriod = 50,
            trendPeriod = 200,
            resolution = Resolution.Daily,
            predictionResolution = Resolution.Hour,
            predictionPeriod = 1,
            movingAverageType = MovingAverageType.Exponential)) 
        
        #Portfolio Construction
        self.SetPortfolioConstruction(StaticWeightPortfolioConstructionModel(
            portfolioBias = PortfolioBias.LongShort,
            positionWeight = 0.01
        ))

        #Risk Management
        #Register ATR Indicator
        symbol = self.USDJPY.Symbol
        self.symbolQuoteBarWindow = {}
        self.symbolStopLevel = {}
        self.symbolTriggerBarATR = {}
        self.symbolRunningATR = {}
        self.atrMultiplier = 1
        self.atr = self.ATR(symbol, 14, MovingAverageType.Simple, Resolution.Daily)
        self.RegisterIndicator(symbol, self.atr, Resolution.Daily)
        self.symbolQuoteBarWindow[symbol.Value] = RollingWindow[QuoteBar](3)
        self.SetRiskManagement(NullRiskManagementModel())
        
        #Execution       
        self.SetExecution(InstantExecutionModel()) 

    
    def OnData(self, data):  
        if self.IsWarmingUp: return

        # Manage all current securities        
        for kvp in self.Securities:
            # Get underlying symbol  
            symbol = kvp.Key
            
            # Get stop level if we have it
            stopLevel = 0.0
            if symbol in self.symbolStopLevel:
                stopLevel = self.symbolStopLevel[symbol]

            # If data slice contains this symbol
            if data.ContainsKey(symbol):           
                # Add QuoteBar to RollingWindow collection     
                self.symbolQuoteBarWindow[symbol.Value].Add(data[symbol])

                # Initialize trigger bar for symbol
                if not symbol in self.symbolTriggerBarATR:
                    atrValue = self.atr.Current.Value * self.atrMultiplier
                    self.symbolTriggerBarATR[symbol.Value] = atrValue

                # Initialize stop level for symbol
                if not symbol in self.symbolStopLevel:
                    stopLevel = data[symbol].Low - self.symbolTriggerBarATR[symbol.Value]

                # Only apply lookback logic if we have enough records
                if self.symbolQuoteBarWindow[symbol.Value].Count is 3:    
                    onePeriodBackBar = self.symbolQuoteBarWindow[symbol.Value][1]  
                    twoPeriodBackBar = self.symbolQuoteBarWindow[symbol.Value][2]                     

                    # If the new low on the previous candle is higher than the low before that,
                    # then the stop level calculation will use this new low
                    if onePeriodBackBar.Low > twoPeriodBackBar.Low:      
                        stopLevel = onePeriodBackBar.Low - self.symbolTriggerBarATR[symbol.Value]    

                    # If current price crosses over the stop level, liquidate
                    if self.Securities[symbol].Price <= stopLevel:
                        self.Liquidate(symbol)

                    # Add/update stop level in dictionary
                    self.symbolStopLevel[symbol.Value] = stopLevel              
                else:
                    pass

                
            else:
                continue

