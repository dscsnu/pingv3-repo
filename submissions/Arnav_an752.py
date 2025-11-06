from ping_game_theory import Strategy, StrategyTester, History, HistoryEntry, Move


class Bot(Strategy):
    def __init__(self) -> None:
        self.author_netid = "an752"  # Your netid here
        self.strategy_name = "Everything (sponsored by voidtools)"  # Name of your strategy here
        self.strategy_desc = "i have plans. i have plans i cannot share lest the opps find out."  # Description of your strategy here

    def begin(self) -> Move:
        return Move.DEFECT  

    def turn(self, history: History) -> Move:

        return (
            Move.DEFECT
        )  


tester = StrategyTester(Bot)
tester.run()
