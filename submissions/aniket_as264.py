from ping_game_theory import Strategy, StrategyTester, History, Move
import random

class Bot(Strategy):
    def __init__(self) -> None:
        self.author_netid = "as264@snu.edu.in"
        self.strategy_name = "Meta-Proof Greedy Forgiver"
        self.strategy_desc = (
            "Analyzes opponent type (Cooperator, Punisher, Noisy, Defector) "
            "and dynamically switches between peaceful, exploitative, and defensive behaviors. "
            "Forgives occasionally, exploits wisely, and ends aggressively."
        )

        # parameters

        self.window = 100                 # behavior detection window
        self.forgive_prob = 0.015         # forgiveness to recover from D-D
        self.base_exploit = 0.002         # base exploit rate
        self.max_exploit = 0.05           # max exploit rate vs pure cooperators
        self.endgame_start = 9900         # final 100 rounds
        self.trust_build = 10             # initial pure cooperation rounds

    def begin(self) -> Move:
        return Move.COOPERATE

    # classify opponent type every few hundred rounds
    def classify_opponent(self, opponent_moves):
        n = len(opponent_moves)
        if n < 50:
            return "UNKNOWN"
        defect_rate = opponent_moves.count(Move.DEFECT) / n

        # detect consistency of behavior
        changes = sum(1 for i in range(1, n) if opponent_moves[i] != opponent_moves[i - 1])
        stability = 1 - (changes / n)

        if defect_rate < 0.05 and stability > 0.8:
            return "COOPERATOR"
        elif defect_rate < 0.35 and stability < 0.6:
            return "NOISY"
        elif defect_rate > 0.5:
            return "DEFECTOR"
        elif stability > 0.85 and defect_rate > 0.1:
            return "PUNISHER"
        else:
            return "BALANCED"

    def turn(self, history: History) -> Move:
        rounds = len(history)

        # early cooperation
        if rounds < self.trust_build:
            return Move.COOPERATE

        opponent_moves = [h.other for h in history]
        my_moves = [h.self for h in history]

        # detect opponent type
        opponent_type = self.classify_opponent(opponent_moves)

        # calculate recent defect rate
        recent = opponent_moves[-self.window:] if rounds >= self.window else opponent_moves
        defect_rate_recent = recent.count(Move.DEFECT) / len(recent)

        # forgiveness
        if random.random() < self.forgive_prob:
            return Move.COOPERATE

        # endgame aggression
        if rounds >= self.endgame_start:
            return Move.DEFECT if random.random() < 0.9 else Move.COOPERATE

        # --- Strategy decisions based on classification ---
        if opponent_type == "COOPERATOR":
            # exploit increasing over time
            exploit_rate = min(self.max_exploit, self.base_exploit + 0.001 * rounds / 100)
            if random.random() < exploit_rate:
                return Move.DEFECT
            return Move.COOPERATE

        elif opponent_type == "PUNISHER":
            # be careful: defect only if they defect first
            return Move.COOPERATE if opponent_moves[-1] == Move.COOPERATE else Move.DEFECT

        elif opponent_type == "NOISY":
            # ignore random one-offs, defect only on sustained pattern
            if defect_rate_recent > 0.4:
                return Move.DEFECT
            return Move.COOPERATE

        elif opponent_type == "DEFECTOR":
            # mirror defection rate to avoid sucker payoff
            return Move.DEFECT

        else:  # BALANCED or UNKNOWN
            # adaptive logic similar to earlier bot
            if defect_rate_recent < 0.25:
                return Move.COOPERATE if opponent_moves[-1] == Move.COOPERATE else Move.DEFECT
            elif defect_rate_recent > 0.7:
                return Move.DEFECT
            else:
                coop_prob = max(0.3, 1 - defect_rate_recent)
                return Move.COOPERATE if random.random() < coop_prob else Move.DEFECT


if __name__ == "__main__":
    tester = StrategyTester(Bot)
    tester.run()
