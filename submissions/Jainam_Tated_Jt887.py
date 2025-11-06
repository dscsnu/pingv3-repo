import random
from collections import deque
from ping_game_theory import Strategy, Move, History

class Bot(Strategy):
    def __init__(self):
        self.author_netid = "jt887"
        self.strategy_name = "AdaptiveRandomBot"
        self.strategy_desc = (
            "Mostly random, but detects if opponent defects too often. "
            "Switches to always defect when exploited, returns to random when cooperation resumes."
        )

        # Track opponent behavior
        self.window = 30
        self.opp_hist = deque(maxlen=self.window)
        self.mode = "RANDOM"  # modes: "RANDOM" or "DEFECT"

        # thresholds
        self.defect_threshold = 0.8
        self.coop_threshold = 0.6

    def _coop_rate(self):
        if not self.opp_hist:
            return 0.5
        return sum(1 for m in self.opp_hist if m == Move("COOPERATE")) / len(self.opp_hist)

    def begin(self) -> Move:
        self.opp_hist.clear()
        self.mode = "RANDOM"
        return Move("COOPERATE") if random.random() < 0.5 else Move("DEFECT")

    def turn(self, history: History) -> Move:
        if len(history) >= 1:
            self.opp_hist.append(history[-1].other)

        coop_rate = self._coop_rate()

        # Detect if opponent is defecting too much
        if self.mode == "RANDOM" and coop_rate < (1 - self.defect_threshold):
            self.mode = "DEFECT"

        # Detect if opponent is cooperating again
        elif self.mode == "DEFECT" and coop_rate > self.coop_threshold:
            self.mode = "RANDOM"

        # Choose move based on current mode
        if self.mode == "DEFECT":
            return Move("DEFECT")
        else:
            return Move("COOPERATE") if random.random() < 0.5 else Move("DEFECT")


if __name__ == "__main__":
    from ping_game_theory import StrategyTester
    tester = StrategyTester(Bot)
    tester.run()
