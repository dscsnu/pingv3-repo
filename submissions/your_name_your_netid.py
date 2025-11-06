from ping_game_theory import Strategy, StrategyTester, History, HistoryEntry, Move


class Bot(Strategy):
    def __init__(self) -> None:
        self.author_netid = "at612"  # Your netid here
        self.strategy_name = "I_like_money"  # Name of your strategy here
        self.strategy_desc = "always defect"  # Description of your strategy here

    def begin(self) -> Move:
        # Make your initial move here
        return Move.DEFECT  # Example: always starts with COOPERATE (modify it to implement your strategy)

    def turn(self, history: History) -> Move:
        # Make your move based on the history
        return (
            Move.DEFECT
        )  # Example: always plays DEFECT (modify it to implement your strategy)


tester = StrategyTester(Bot)
tester.run()
