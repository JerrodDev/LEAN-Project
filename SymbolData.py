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
        self.LastInsight = None
        self.QuoteBarWindow = {}
        self.TradeBarWindow = {}
        self.FastIsOverSlow = False
        self.IsAboveTrendLine = False
        self.Direction = None

    @property
    def SlowIsOverFast(self):
        return not self.FastIsOverSlow

    @property
    def IsBelowTrendLine(self):
        return not self.IsAboveTrendLine


