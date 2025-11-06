from ping_game_theory import Strategy, StrategyTester, History, HistoryEntry, Move
import random


class Bot(Strategy):
    def __init__(self) -> None:
        self.author_netid = "sj993"  # Your netid here
        self.strategy_name = "FIWB"  # Name of your strategy here
        self.strategy_desc = "it does what a bot does"  # Description of your strategy here
        self.defects = 0

    def begin(self) -> Move:
        # Make your initial move here
        return Move.DEFECT  # Example: always starts with COOPERATE (modify it to implement your strategy)

    def turn(self, history: History) -> Move:
        rounds = len(history)
        if history[-1].other == Move.DEFECT:
           self.defects += 1
           
        ratio = self.defects / rounds

        if rounds > 10:
            if ratio > 0.3:
                return Move.DEFECT
        

        if history[-1].other == Move.COOPERATE and history[-1].self == Move.COOPERATE:
            return Move.COOPERATE
        
        elif history[-1].other == Move.DEFECT and history[-1].self == Move.COOPERATE:
            return Move.DEFECT
        
        elif history[-1].other == Move.COOPERATE and history[-1].self == Move.DEFECT:
            return Move.DEFECT
        
        elif history[-1].other == Move.DEFECT and history[-1].self == Move.DEFECT:
            return Move.COOPERATE
        else:
            return Move.DEFECT


tester = StrategyTester(Bot)
tester.run()
