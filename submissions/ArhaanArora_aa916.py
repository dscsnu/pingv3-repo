import random
from collections import deque

from ping_game_theory import History, HistoryEntry, Move, Strategy, StrategyTester


class Bot(Strategy):
    def __init__(self) -> None:
        self.author_netid = "aa916"
        self.strategy_name = "Adaptive Predator Bot (Tournament Final)"
        self.strategy_desc = (
            "An evolved adaptive strategy that begins cooperatively, classifies opponents dynamically, and adapts "
            "throughout the game. It punishes exploiters, rewards cooperation, resists deception, forgives noise, "
            "and randomizes thresholds and reactions to avoid predictability. Optimized for robustness in both "
            "deterministic and probabilistic environments, including long-horizon play."
        )

        self.base_window_size = 24
        self.base_recheck_interval = 8
        self.window_size = self.base_window_size
        self.recheck_interval = self.base_recheck_interval

        self.randomize = True
        self.random_flip_prob = random.uniform(0.01, 0.03)
        self.adaptive_threshold_variation = random.uniform(-0.05, 0.05)

        self.opponent_defections = 0
        self.opponent_cooperations = 0
        self.consecutive_opponent_defections = 0
        self.max_consecutive_defections = 0

        self.is_sucker = False
        self.is_bully = False
        self.is_tit_for_tat = False
        self.is_alternator = False
        self.classification_complete = False

        self.exploitation_mode = False
        self.defense_mode = False

        self.defection_streak = 0
        self.forgiveness_attempt = 0
        self.last_forgiveness_turn = -10

        self.window = deque(maxlen=self.window_size)
        self.my_window = deque(maxlen=self.window_size)
        self.exploit_marks = deque(maxlen=self.window_size)
        self.last_recheck = 0

        self.total_rounds_known = 999
        self.endgame_soft_start = 12
        self.endgame_hard_start = 6

    def begin(self) -> Move:
        random.seed()
        self.random_flip_prob = random.uniform(0.01, 0.03)
        self.adaptive_threshold_variation = random.uniform(-0.05, 0.05)

        self.opponent_defections = 0
        self.opponent_cooperations = 0
        self.consecutive_opponent_defections = 0
        self.max_consecutive_defections = 0

        self.is_sucker = False
        self.is_bully = False
        self.is_tit_for_tat = False
        self.is_alternator = False
        self.classification_complete = False

        self.exploitation_mode = False
        self.defense_mode = False

        self.defection_streak = 0
        self.forgiveness_attempt = 0
        self.last_forgiveness_turn = -10

        self.window.clear()
        self.my_window.clear()
        self.exploit_marks.clear()
        self.last_recheck = 0

        return Move.COOPERATE

    def _maybe_randomize(self, move: Move) -> Move:
        if not self.randomize:
            return move
        if random.random() < self.random_flip_prob:
            return Move.DEFECT if move == Move.COOPERATE else Move.COOPERATE
        return move

    def turn(self, history: History) -> Move:
        t = len(history)
        if t == 0:
            return self._maybe_randomize(Move.COOPERATE)

        last_entry: HistoryEntry = history[-1]
        opponent_last_move = last_entry.other
        my_last_move = last_entry.self

        if opponent_last_move == Move.DEFECT:
            self.opponent_defections += 1
            self.consecutive_opponent_defections += 1
            self.max_consecutive_defections = max(
                self.max_consecutive_defections, self.consecutive_opponent_defections
            )
        else:
            self.opponent_cooperations += 1
            self.consecutive_opponent_defections = 0

        self.window.append(opponent_last_move)
        self.my_window.append(my_last_move)
        self.exploit_marks.append(
            1
            if (opponent_last_move == Move.DEFECT and my_last_move == Move.COOPERATE)
            else 0
        )

        if t <= 5 and not self.classification_complete:
            move = self._classify_and_respond(
                history, t, opponent_last_move, my_last_move
            )
            if t == 5:
                self.classification_complete = True
            return self._maybe_randomize(move)

        if (t - self.last_recheck) >= self.recheck_interval:
            self._soft_reclassify(history)
            self.last_recheck = t

        remaining = self.total_rounds_known - t
        if remaining <= self.endgame_soft_start:
            end_move = self._endgame_policy(history, remaining)
            if end_move is not None:
                return self._maybe_randomize(end_move)

        if self.is_bully or self.defense_mode:
            return self._maybe_randomize(Move.DEFECT)

        if self.is_sucker or self.exploitation_mode:
            if self.opponent_defections == 0 and len(history) >= 20:
                return self._maybe_randomize(Move.COOPERATE)
            return self._maybe_randomize(Move.DEFECT)

        if self.is_tit_for_tat:
            return self._maybe_randomize(Move.COOPERATE)

        if self.is_alternator:
            if self._last_two_opponent_defected():
                return self._maybe_randomize(Move.DEFECT)
            return self._maybe_randomize(Move.COOPERATE)

        move = self._generous_tit_for_two_tats(history)
        return self._maybe_randomize(move)

    def _classify_and_respond(
        self, history: History, t: int, opp_last: Move, my_last: Move
    ) -> Move:
        if t == 1:
            return Move.COOPERATE
        if t == 2:
            if self.opponent_defections == 2:
                self.is_bully = True
                self.defense_mode = True
                return Move.DEFECT
            if self.opponent_cooperations == 2:
                if self.opponent_defections == 0:
                    return Move.COOPERATE
                return Move.DEFECT
            return Move.COOPERATE
        if t == 3:
            if self.is_bully:
                return Move.DEFECT
            if history[-1].self == Move.DEFECT and opp_last == Move.COOPERATE:
                if self.opponent_defections == 0 and len(history) >= 3:
                    return Move.COOPERATE
                self.is_sucker = True
                self.exploitation_mode = True
                return Move.DEFECT
            if self._tft_score() >= 0.75:
                self.is_tit_for_tagt = True
                return Move.COOPERATE
            return Move.COOPERATE
        if t in (4, 5):
            if self.opponent_defections >= 4:
                self.is_bully = True
                self.defense_mode = True
                return Move.DEFECT
            if self.is_sucker and opp_last == Move.COOPERATE:
                if self.opponent_defections == 0 and len(history) >= 5:
                    return Move.COOPERATE
                return Move.DEFECT
            if self._alternator_score() >= 0.92:
                self.is_alternator = True
                return Move.COOPERATE
            if self._tft_score() >= 0.85:
                self.is_tit_for_tat = True
                return Move.COOPERATE
            return Move.COOPERATE
        return Move.COOPERATE

    def _soft_reclassify(self, history: History) -> None:
        recent = list(self.window)
        n = len(recent)
        coop_count = recent.count(Move.COOPERATE)
        recent_rate = (coop_count / n) if n > 0 else 1.0

        self.is_bully = recent_rate <= 0.10
        self.defense_mode = self.is_bully
        self.is_sucker = recent_rate >= 0.97
        self.exploitation_mode = self.is_sucker
        self.is_tit_for_tat = len(history) >= 6 and self._tft_score() >= 0.87
        self.is_alternator = self._alternator_score() >= 0.92

        if n >= 14:
            prev = recent[:-7]
            last = recent[-7:]
            if len(prev) >= 7:
                prev_rate = prev.count(Move.COOPERATE) / len(prev)
                last_rate = last.count(Move.COOPERATE) / len(last)
                if (
                    prev_rate >= 0.8
                    and last_rate <= 0.4
                    and self.opponent_defections >= 2
                ):
                    self.is_bully = True
                    self.defense_mode = True
                    self.is_sucker = False
                    self.is_tit_for_tat = False
                    self.is_alternator = False
                    return

        if self.is_bully:
            self.is_sucker = self.is_tit_for_tat = self.is_alternator = False
            return
        if self.is_sucker:
            self.is_tit_for_tat = self.is_alternator = False
            return
        if self.is_tit_for_tat:
            self.is_alternator = False

    def _tft_score(self) -> float:
        L = min(len(self.window), len(self.my_window))
        if L < 2:
            return 0.0
        matches = sum(
            1 for i in range(1, L) if self.window[-i] == self.my_window[-(i + 1)]
        )
        return matches / (L - 1)

    def _alternator_score(self) -> float:
        seq = list(self.window)
        if len(seq) < 8:
            return 0.0
        ok = sum(1 for i in range(2, len(seq)) if seq[i] == seq[i - 2])
        return ok / (len(seq) - 2)

    def _last_two_opponent_defected(self) -> bool:
        return (
            len(self.window) >= 2
            and self.window[-1] == Move.DEFECT
            and self.window[-2] == Move.DEFECT
        )

    def _generous_tit_for_two_tats(self, history: History) -> Move:
        if self._last_two_opponent_defected():
            self.defection_streak += 1
            return Move.DEFECT

        if len(self.window) >= 1 and self.window[-1] == Move.DEFECT:
            total = self.opponent_cooperations + self.opponent_defections
            defect_ratio = (self.opponent_defections / total) if total > 0 else 0.0
            exploit_pressure = sum(self.exploit_marks)
            adaptive_threshold = (
                0.5
                + min(0.3, exploit_pressure / 20.0)
                + self.adaptive_threshold_variation
            )
            if exploit_pressure >= 2 or defect_ratio >= adaptive_threshold:
                return Move.DEFECT
            return Move.COOPERATE

        self.defection_streak = 0
        self.forgiveness_attempt = 0
        return Move.COOPERATE

    def _endgame_policy(self, history: History, remaining: int):
        recent_len = len(self.window)
        recent_coop = sum(1 for m in self.window if m == Move.COOPERATE)
        recent_rate = (recent_coop / recent_len) if recent_len > 0 else 1.0
        never_defected = self.opponent_defections == 0

        if never_defected:
            if remaining > 1:
                return None
            if remaining == 1:
                return Move.DEFECT

        if remaining <= self.endgame_hard_start and recent_rate < 0.9:
            return Move.DEFECT

        if recent_rate >= 0.9:
            if remaining <= 2 and not self.is_tit_for_tat:
                return Move.DEFECT
            if remaining == 1:
                return Move.DEFECT
            return None

        if remaining <= self.endgame_soft_start:
            if self.opponent_defections > 0:
                return Move.DEFECT
            return None

        return None


tester = StrategyTester(Bot)
tester.run()
