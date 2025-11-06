from ping_game_theory import Strategy, History, Move
import random

class MaaKaBharosa(Strategy):
    def __init__(self) -> None:
        self.author_netid = "aa557@snu.edu.in"
        self.strategy_name = "maa-ka-bharosa"
        self.strategy_desc = (
            "Enhanced adaptive strategy with dynamic exploitation, adaptive forgiveness, "
            "contextual endgame aggression, and refined opponent classification."
        )

        self.window = 100
        self.base_exploit = 0.002
        self.max_exploit = 0.05
        self.endgame_start = 9900
        self.trust_build = 10

    def begin(self) -> Move:
        return Move.COOPERATE

    def classify_opponent(self, opponent_moves):
        n = len(opponent_moves)
        if n < 50:
            return "UNKNOWN"
        defect_rate = opponent_moves.count(Move.DEFECT) / n
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

    def dynamic_exploit_rate(self, rounds, coop_streak):
        base_rate = self.base_exploit
        if coop_streak >= 10:
            rate = min(self.max_exploit, base_rate + 0.02 * (coop_streak - 9))
        else:
            rate = base_rate
        return max(0, rate)

    def turn(self, history: History) -> Move:
        rounds = len(history)
        if rounds < self.trust_build:
            return Move.COOPERATE

        # Use tuple indexing for history
        opponent_moves = [h[1] for h in history]
        my_moves = [h[0] for h in history]
        opponent_type = self.classify_opponent(opponent_moves)

        recent = opponent_moves[-self.window:] if rounds >= self.window else opponent_moves
        defect_rate_recent = recent.count(Move.DEFECT) / len(recent)

        coop_streak = 0
        for move in reversed(opponent_moves):
            if move == Move.COOPERATE:
                coop_streak += 1
            else:
                break

        forgiveness_prob = 0.015 + 0.05 * (coop_streak / self.window)
        if random.random() < forgiveness_prob:
            return Move.COOPERATE

        exploit_rate = self.dynamic_exploit_rate(rounds, coop_streak)

        if rounds >= self.endgame_start:
            if opponent_type in ["COOPERATOR", "BALANCED"]:
                return Move.DEFECT if random.random() < 0.95 else Move.COOPERATE
            else:
                return Move.DEFECT

        if opponent_type == "COOPERATOR":
            if random.random() < exploit_rate:
                return Move.DEFECT
            return Move.COOPERATE
        elif opponent_type == "PUNISHER":
            return Move.COOPERATE if opponent_moves[-1] == Move.COOPERATE else Move.DEFECT
        elif opponent_type == "NOISY":
            if defect_rate_recent > 0.4:
                return Move.DEFECT
            return Move.COOPERATE
        elif opponent_type == "DEFECTOR":
            return Move.DEFECT
        else:  # BALANCED or UNKNOWN
            if defect_rate_recent < 0.25:
                return Move.COOPERATE if opponent_moves[-1] == Move.COOPERATE else Move.DEFECT
            elif defect_rate_recent > 0.7:
                return Move.DEFECT
            else:
                coop_prob = max(0.3, 1 - defect_rate_recent)
                return Move.COOPERATE if random.random() < coop_prob else Move.DEFECT

class AdaptiveBot(Strategy):
    def __init__(self) -> None:
        self.author_netid = "aa557"
        self.strategy_name = "maa_ka_bharosaa"
        self.strategy_desc = "Adaptive sliding window IPD strategy"
        self.last_forced_defect = -100

    def begin(self) -> Move:
        return Move.COOPERATE

    def classify_opponent(self, history, window=100):
        h = history[-window:] if len(history) >= window else history
        my_moves = [x[0] for x in h]
        opp_moves = [x[1] for x in h]
        N = len(h)
        if N < 6:
            return "unknown"
        if all(om == Move.COOPERATE for om in opp_moves):
            return "always_cooperate"
        if all(om == Move.DEFECT for om in opp_moves):
            return "always_defect"
        tit_for_tat_like = sum(
            opp_moves[t] == my_moves[t-1] if t > 0 else True for t in range(N)
        ) / N > 0.8
        if tit_for_tat_like:
            return "tit_for_tat"
        retaliatory = (
            sum(
                opp_moves[t] == Move.DEFECT and my_moves[t-1] == Move.DEFECT
                for t in range(1, N)
            ) / max(1, sum(my_moves[t-1] == Move.DEFECT for t in range(1, N)))
        ) > 0.75
        if retaliatory:
            return "retaliator"
        coop_rate = opp_moves.count(Move.COOPERATE) / N
        if coop_rate > 0.7:
            return "cooperative"
        return "random"

    def turn(self, history: History) -> Move:
        N = len(history)
        if N == 0:
            return Move.COOPERATE

        my_moves = [h[0] for h in history]
        opp_moves = [h[1] for h in history]

        window = min(100, max(6, N // 10))
        exploration_prob = 0.05
        forgiveness_prob = 0.5

        opp_type = self.classify_opponent(history, window=window)

        if random.random() < exploration_prob and (N - self.last_forced_defect > 2):
            self.last_forced_defect = N
            return Move.DEFECT

        if opp_type == "tit_for_tat":
            return opp_moves[-1]
        elif opp_type in ["always_cooperate", "cooperative"]:
            return Move.DEFECT if random.random() < 0.7 else Move.COOPERATE
        elif opp_type == "always_defect":
            return Move.DEFECT
        elif opp_type == "retaliator":
            if opp_moves[-1] == Move.DEFECT:
                if my_moves[-1] == Move.DEFECT and random.random() < forgiveness_prob:
                    return Move.COOPERATE
                return Move.DEFECT
            else:
                return Move.COOPERATE
        elif opp_type == "random":
            if N > 10 and sum(om == Move.DEFECT for om in opp_moves[-10:]) > 7:
                return Move.DEFECT
            return opp_moves[-1]
        else:
            return Move.DEFECT if opp_moves[-1] == Move.DEFECT else Move.COOPERATE

def get_scores(m1, m2):
    if m1 == Move.COOPERATE and m2 == Move.COOPERATE:
        return 3, 3
    elif m1 == Move.COOPERATE and m2 == Move.DEFECT:
        return 0, 5
    elif m1 == Move.DEFECT and m2 == Move.COOPERATE:
        return 5, 0
    else:
        return 1, 1

if __name__ == "__main__":
    rounds = 10000
    bot1 = MaaKaBharosa()
    bot2 = AdaptiveBot()

    history1 = []
    history2 = []

    score1 = 0
    score2 = 0

    move1 = bot1.begin()
    move2 = bot2.begin()
    history1.append((move1, move2))
    history2.append((move2, move1))
    s1, s2 = get_scores(move1, move2)
    score1 += s1
    score2 += s2

    for _ in range(1, rounds):
        move1 = bot1.turn(history1)
        move2 = bot2.turn(history2)
        history1.append((move1, move2))
        history2.append((move2, move1))
        s1, s2 = get_scores(move1, move2)
        score1 += s1
        score2 += s2

    print(f"Total rounds played: {rounds}")
    print(f"{bot1.strategy_name} score: {score1}")
    print(f"{bot2.strategy_name} score: {score2}")

    if score1 > score2:
        print(f"Winner: {bot1.strategy_name} by {score1 - score2} points")
    elif score2 > score1:
        print(f"Winner: {bot2.strategy_name} by {score2 - score1} points")
    else:
        print("It's a tie!")
