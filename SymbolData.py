from AlgorithmImports import *

class SymbolData:
    def __init__(self, security):
        self.Security = security
        self.Symbol = security.Symbol
        self.Fast = None
        self.Slow = None
        self.Trend = None
        self.AverageTrueRange = None
        self.TriggerBarATR = None
        self.StopLevel = None
        self.PredictionInterval = None
        self.QuoteBarWindow = {}
        self.FastIsOverSlow = False
        self.IsAboveTrendLine = False
        self.Direction = None

    def ResetComparators(self):
        #Has fast MA crossed over slow MA
        self.FastIsOverSlow = self.Fast > self.Slow
        
        #Are fast and slow MA above the trend line
        self.IsAboveTrendLine = self.Fast > self.Trend and self.Slow > self.Trend  

    @property
    def SlowIsOverFast(self):
        return not self.FastIsOverSlow

    @property
    def IsBelowTrendLine(self):
        return not self.IsAboveTrendLine


