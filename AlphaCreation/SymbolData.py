from AlgorithmImports import *

class SymbolData:
    def __init__(self, security):
        self.Security = security
        self.Symbol = security.Symbol
        self.Fast = None
        self.Slow = None
        self.Trend = None
        self.FastIsOverSlow = False
        self.IsAboveTrendLine = False
        self.PreviousDirection = None
        
    @property
    def SlowIsOverFast(self):
        return not self.FastIsOverSlow

    @property
    def IsBelowTrendLine(self):
        return not self.IsAboveTrendLine
    
    def Reset(self):
        self.Fast.Reset()
        self.Slow.Reset()
        self.Trend.Reset()
