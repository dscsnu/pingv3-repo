from ping_game_theory import Strategy, StrategyTester, History, HistoryEntry, Move


class Bot(Strategy):
    def _init_(self) -> None:
        self.author_netid = "as677"  # Your netid here
        self.strategy_name = "winner"  # Name of your strategy here
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

        if(history[-1] == Move.DEFECT and history[-2] == Move.DEFECT):
            return(
                Move.DEFECT
            )
        
        else:
            return (
                Move.DEFECT
            ) 


tester = StrategyTester(Bot)
tester.run()
