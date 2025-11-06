from ping_game_theory import Strategy, StrategyTester, History, HistoryEntry, Move

class Bot(Strategy):
    """
    ModePoison Exploiter

    - Rounds 1..calibration_window: defect every `defect_every_k`-th round (approx 1/defect_every_k fraction).
      This keeps observed opponent defect-rate in a mid band so some adaptive opponents pick a "wsls/pavlov" style.
    - After calibration_window: always DEFECT to exploit opponents that occasionally flip to C when stuck in DD.
    """

    def __init__(self) -> None:
        self.author_netid = "aa740"
        self.strategy_name = "ModePoison Exploiter"
        self.strategy_desc = (
            "Poison calibration with ~25% defections early, then defect forever to exploit WSLS/Pavlov "
            "strategies that break DD occasionally."
        )

        # configuration
        self.calibration_window = 30
        self.defect_every_k = 4

    def begin(self) -> Move:
        # start cooperative so early rounds mostly appear cooperative and avoid immediate 'punish' classifications
        return Move.COOPERATE

    def turn(self, history: History) -> Move:
        # round number about to play (1-indexed)
        round_num = len(history) + 1

        if round_num <= self.calibration_window:
            # defect every k-th round during calibration, otherwise cooperate
            return Move.DEFECT if (round_num % self.defect_every_k == 0) else Move.COOPERATE

        # after calibration: defect forever
        return Move.DEFECT


if __name__ == "__main__":
    tester = StrategyTester(Bot)
    tester.run()
