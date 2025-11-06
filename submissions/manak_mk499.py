from ping_game_theory import Strategy, StrategyTester, History, HistoryEntry, Move


class Bot(Strategy):
    def __init__(self) -> None:
        self.author_netid = "mk499"  # Your netid here
        self.strategy_name = "Tit for tat greedy"  # Name of your strategy here
        self.strategy_desc = ""  # Description of your strategy here

    def begin(self) -> Move:
        
        return Move.DEFECT 
    
    def turn(self, history: History) -> Move:
        if(len(history) >= 10):
            flag = False
            for i in range(-1, -11, -1):
                if(history[i] != Move.COOPERATE):
                    flag = True
                    break

            if(flag == False):
                return (
                    Move.DEFECT
                )

        if(history[-1].other == Move.DEFECT):
            return(
                Move.DEFECT
            )
        
        else:
            return (
                Move.COOPERATE
            ) 


tester = StrategyTester(Bot)
tester.run()
