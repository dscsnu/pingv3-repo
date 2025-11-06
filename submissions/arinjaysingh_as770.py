from ping_game_theory import Strategy, StrategyTester, History, Move

class Bot(Strategy):
    def __init__(self) -> None:
        self.author_netid = "as770"
        self.strategy_name = "the_winning_strategy"
        self.strategy_desc = "i like howie mandel"
        self.sequence = [Move.DEFECT, Move.COOPERATE, Move.DEFECT]  # initial 3 moves
        self.index = 0
        self.current_pattern = self.sequence.copy()  # start pattern

    def begin(self) -> Move:
        self.index = 0
        return self.current_pattern[self.index]

    def turn(self, history: History) -> Move:
        # Increment turn counter
        self.index += 1

        # If we're still in the initial pattern
        if len(history) < 3:
            return self.sequence[len(history)]

        # If we've reached the end of the current pattern, decide next sequence
        if self.index >= len(self.current_pattern):
            last_move = self.current_pattern[-1]  # what our last move was

            # Build next pattern based on last move
            if last_move == Move.DEFECT:
                self.current_pattern = [Move.DEFECT]  # if third move was defect → defect
            elif last_move == Move.COOPERATE:
                self.current_pattern = [Move.COOPERATE, Move.DEFECT]  # if fourth move was cooperate → cooperate, defect
            else:
                self.current_pattern = [Move.DEFECT, Move.DEFECT]  # otherwise → defect, defect

            # Reset index to start of new pattern
            self.index = 0

        # Return the move in the current pattern
        return self.current_pattern[self.index]


# Test your bot
tester = StrategyTester(Bot)
tester.run()
