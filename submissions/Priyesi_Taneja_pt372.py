import random 
from ping_game_theory import Strategy, StrategyTester, History, HistoryEntry, Move


class Bot(Strategy):
    def __init__(self) -> None:
        self.author_netid = "pt372"  # Your netid here
        self.strategy_name = "KarmaBot"  # Name of your strategy here
        self.strategy_desc = "in 5% of the time it gives a random output. rest for the 95% of the time if karma is positive it gives COOPERATE and if it is negative it gives DEFECT"  # Description of your strategy here

    def begin(self) -> Move:
        '''Make your initial move here'''
        self.karma=0
        return Move.COOPERATE  # Example: always starts with COOPERATE (modify it to implement your strategy)

    def turn(self, history: History) -> Move:
        if len(history)>0:
            last_round=history[-1]
            if last_round.other==Move.COOPERATE:
               self.karma+=4
            else:
                self.karma+=-5
        if random.random()<0.02:
            return random.choice([Move.DEFECT, Move.COOPERATE])
        if self.karma>0:
            return Move.COOPERATE 
        else:
            return Move.DEFECT # Example: always plays DEFECT (modify it to implement your strategy)


tester = StrategyTester(Bot)
tester.run()
