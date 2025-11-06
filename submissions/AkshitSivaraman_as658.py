import json
import math
import os
import urllib.request

from ping_game_theory import History, HistoryEntry, Move, Strategy, StrategyTester


class Bot(Strategy):
    """Three-phase Iterated Prisoner's Dilemma bot with quantum-random openings."""

    def __init__(self) -> None:
        # Required metadata
        self.author_netid = "as658"
        self.strategy_name = "Retard"
        self.strategy_desc = "Pretend to be stupid and then become smart and then become stupid again i guess"

        # Core match state
        self.round = 0
        self.phase = 1
        self.last_move = None
        self.last_opp_move = None

        # Transition counters
        self.cc = 0
        self.cd = 0
        self.dc = 0
        self.dd = 0

        # Quantum randomness tracking
        self.qrng_ok = False
        self.qrand_buffer = []
        self.qrand_index = 0

        # Opening behavior
        self.opening_mode = 0
        self.opening_index = 0

        # Opponent modeling buffers
        self.opp_history_bits = []
        self.pattern_guess = None
        self.pattern_confidence = 0.0
        self.pattern_sequence = []
        self.mirror_count = 0
        self.total_pairs = 0
        self.retaliation_flag = False

        # Online perceptron predictor for opponent cooperation
        self.perceptron_dim = 10
        self.perceptron_weights = [0.0] * self.perceptron_dim
        self.perceptron_bias = 0.0
        self.pending_features = None
        self.my_history_bits = []

    # ------------------------------------------------------------------
    # Randomness utilities
    # ------------------------------------------------------------------
    def fetch_quantum_randoms(self, n: int = 512):
        """Attempt to pull quantum randomness, falling back to os.urandom locally."""
        try:
            url = f"https://qrng.anu.edu.au/API/jsonI.php?length={n}&type=uint8"
            with urllib.request.urlopen(url, timeout=3) as response:
                payload = response.read().decode()
            data = json.loads(payload)
            self.qrng_ok = True
            return data["data"]
        except Exception:
            self.qrng_ok = False
            return [int.from_bytes(os.urandom(1), "big") for _ in range(n)]

    def _random_byte(self) -> int:
        """Return the next random byte, refreshing the buffer when depleted."""
        if self.qrand_index >= len(self.qrand_buffer):
            self.qrand_buffer = self.fetch_quantum_randoms(1024)
            self.qrand_index = 0
        value = int(self.qrand_buffer[self.qrand_index]) & 0xFF
        self.qrand_index += 1
        return value

    def true_random_bit(self) -> int:
        """Return a single random bit sourced from quantum entropy when available."""
        return self._random_byte() % 2

    def _random_threshold(self, threshold) -> bool:
        """Return True if randomness falls below the provided threshold."""
        if isinstance(threshold, (float, int)) and float(threshold) <= 1.0:
            probability = max(0.0, min(1.0, float(threshold)))
            high = (self._random_byte() << 8) | self._random_byte()
            return high < int(probability * 65536)
        value = int(threshold)
        return self._random_byte() < value

    # ------------------------------------------------------------------
    # Core strategy interface
    # ------------------------------------------------------------------
    def begin(self) -> Move:
        """Reset match state and produce the first deceptive move."""
        self.round = 0
        self.phase = 1
        self.last_move = None
        self.last_opp_move = None

        # Reset transition counters
        self.cc = self.cd = self.dc = self.dd = 0

        # Seed quantum randomness and pick an opening script
        self.qrand_buffer = self.fetch_quantum_randoms(1024)
        self.qrand_index = 0

        # Use two bits to expand mode choices before applying modulo 3.
        mode_bits = (self.true_random_bit() << 1) | self.true_random_bit()
        self.opening_mode = mode_bits % 3
        self.opening_index = 0

        # Reset opponent modeling
        self.opp_history_bits = []
        self.pattern_guess = None
        self.pattern_confidence = 0.0
        self.pattern_sequence = []
        self.mirror_count = 0
        self.total_pairs = 0
        self.retaliation_flag = False
        self.my_history_bits = []
        self.perceptron_weights = [0.0] * self.perceptron_dim
        self.perceptron_bias = 0.0
        self.pending_features = None

        first_move = self._opening_move(self.opening_index)
        self.opening_index += 1
        self.last_move = first_move
        return first_move

    def turn(self, history: History) -> Move:
        """Main decision function executed each round after the opener."""
        self.round += 1

        my_last, opp_last = self._extract_last_round(history)

        # Update transition counts using the most recent outcome.
        if my_last is not None and opp_last is not None:
            self._update_transitions(my_last, opp_last)
            self.last_move = my_last
            self.last_opp_move = opp_last

        features = self._build_features()
        if features is not None:
            coop_prob = self._perceptron_predict(features)
            self.pending_features = features[:]
        else:
            coop_prob = 0.5
            self.pending_features = None

        # Determine current phase.
        if self.round < 30:
            self.phase = 1
        elif self.round < 9500:
            self.phase = 2
        else:
            self.phase = 3

        context = self._gather_context()

        if self.phase == 1:
            early_tag = context["tag"]
            override_tags = {"ALWAYS_DEF", "ALWAYS_COOP", "RANDOM", "PATTERN", "REACTIVE"}
            threshold = 3 if early_tag in {"ALWAYS_DEF", "ALWAYS_COOP"} else 5
            if self.round >= threshold and early_tag in override_tags:
                original_phase = self.phase
                self.phase = 2
                move = self._adaptive_move(coop_prob, context)
                self.phase = original_phase
            else:
                move = self._opening_move(self.opening_index)
                if not context["retaliated"] and self.round >= 7 and self.round % 7 == 0:
                    move = Move.DEFECT
                self.opening_index += 1
        else:
            move = self._adaptive_move(coop_prob, context)

        self.last_move = move
        return move

    # ------------------------------------------------------------------
    # Phase behaviors
    # ------------------------------------------------------------------
    def _opening_move(self, index: int) -> Move:
        """Return the next move inside the deceptive opening phase."""
        if index < 4:
            return Move.COOPERATE
        if self.opening_mode == 0:
            # Mostly cooperate, defect every 10th round.
            if (index + 1) % 10 == 0:
                return Move.DEFECT
            return Move.COOPERATE
        if self.opening_mode == 1:
            # Alternate cooperation and defection.
            return Move.COOPERATE if index % 2 == 0 else Move.DEFECT
        # Mode 2: 80% cooperate, 20% defect.
        return Move.COOPERATE if self._random_threshold(204) else Move.DEFECT

    def _adaptive_move(self, coop_prob: float, context: dict) -> Move:
        """Compute the move for phase 2 or 3 based on learned statistics."""
        opp_coop_rate = context["opp_coop_rate"]
        pc_given_c = context["pc_given_c"]
        pc_given_d = context["pc_given_d"]
        randomness_indicator = context["entropy"]
        forgiveness = context["forgiveness"]
        pattern_prediction = context["pattern_prediction"]
        opponent_tag = context["tag"]
        retaliated = context["retaliated"]

        coop_prob = 0.85 * coop_prob + 0.15 * forgiveness

        if self._is_random_opponent(opp_coop_rate, randomness_indicator):
            return Move.DEFECT

        if not retaliated and self.round % 7 == 0:
            return Move.DEFECT

        move = None
        if opponent_tag == "ALWAYS_COOP":
            move = Move.DEFECT if (self.round % 8 != 0) else Move.COOPERATE
        elif opponent_tag == "ALWAYS_DEF":
            move = Move.DEFECT
        elif opponent_tag == "RANDOM":
            move = Move.DEFECT
        elif opponent_tag == "PATTERN":
            predicted = pattern_prediction or self._predict_pattern_move()
            move = self._pattern_based_counter(
                predicted or Move.COOPERATE, opp_coop_rate, self.phase == 3
            )
        elif opponent_tag == "FORGIVING":
            adjusted = min(1.0, coop_prob + 0.2)
            move = Move.COOPERATE if self._random_threshold(adjusted) else Move.DEFECT
        elif opponent_tag == "REACTIVE":
            if self.last_move is None or self.last_opp_move is None:
                move = Move.COOPERATE
            elif self.last_move == Move.COOPERATE and self.last_opp_move == Move.COOPERATE:
                move = Move.COOPERATE
            elif self.last_move == Move.COOPERATE and self.last_opp_move == Move.DEFECT:
                move = Move.DEFECT if self._random_threshold(0.7) else Move.COOPERATE
            elif self.last_move == Move.DEFECT and self.last_opp_move == Move.COOPERATE:
                move = Move.COOPERATE
            else:  # mutual defection
                move = Move.COOPERATE if self._random_threshold(0.8) else Move.DEFECT
        else:  # ADAPTIVE meta-learner
            if self.round in (1000, 3000, 7000):
                move = Move.DEFECT if self.true_random_bit() == 0 else Move.COOPERATE
            else:
                move = Move.COOPERATE if coop_prob > 0.5 else Move.DEFECT

        if move is None:
            move = Move.COOPERATE if coop_prob >= 0.45 else Move.DEFECT

        if self.phase == 2 and opponent_tag in {"ADAPTIVE", "PATTERN"}:
            if pattern_prediction is not None and self.pattern_confidence >= 0.6:
                move = self._pattern_based_counter(
                    pattern_prediction, opp_coop_rate, False
                )
            elif self.round % 10 == 0 and self.true_random_bit() == 1:
                move = Move.COOPERATE if move == Move.DEFECT else Move.DEFECT

        if self.phase == 3 and opponent_tag not in {"ALWAYS_DEF", "ALWAYS_COOP", "RANDOM"}:
            entropy = randomness_indicator
            bias = 0.5 + 0.25 * (1.0 - entropy)
            chaos_intensity = min(max((self.round - 9000) / 1000.0, 0.0), 1.0)
            chaos_move = Move.COOPERATE if self._random_threshold(bias) else Move.DEFECT
            if self._random_threshold(chaos_intensity):
                move = chaos_move
            epsilon = 0.05 + 0.25 * chaos_intensity
            if self._random_threshold(epsilon):
                move = Move.COOPERATE if move == Move.DEFECT else Move.DEFECT

        return move

    def _phase_two_decision(
        self,
        opp_coop_rate: float,
        pc_given_c: float,
        pc_given_d: float,
        coop_prob: float,
    ) -> Move:
        """Determine the phase-two move following the specified heuristics."""
        if opp_coop_rate > 0.7:
            return Move.COOPERATE
        if opp_coop_rate < 0.3:
            return Move.DEFECT

        # Win-Stay / Lose-Shift variant with conditional cooperation checks.
        if self.last_move == Move.COOPERATE and self.last_opp_move == Move.COOPERATE:
            return Move.COOPERATE
        if self.last_move == Move.COOPERATE and self.last_opp_move == Move.DEFECT:
            return Move.DEFECT
        if (
            self.last_move == Move.DEFECT
            and self.last_opp_move == Move.COOPERATE
            and pc_given_d > 0.5
        ):
            return Move.COOPERATE
        if coop_prob >= 0.65:
            return Move.COOPERATE
        if coop_prob <= 0.35:
            return Move.DEFECT
        return Move.DEFECT

    # ------------------------------------------------------------------
    # History and transition helpers
    # ------------------------------------------------------------------
    def _classify_opponent(
        self,
        opp_coop_rate: float,
        pc_given_c: float,
        pc_given_d: float,
        entropy: float,
        forgiveness: float,
        pattern_confidence: float,
        total_rounds: int,
        cd_ratio: float,
        dc_ratio: float,
        coop_samples: int,
        def_samples: int,
        mirror_ratio: float,
        retaliated: bool,
    ) -> str:
        """Tag the opponent based on aggregate statistics."""
        bias = abs(opp_coop_rate - 0.5)
        if (
            total_rounds >= 12
            and opp_coop_rate > 0.9
            and cd_ratio < 0.05
            and def_samples >= 3
            and not retaliated
        ):
            return "ALWAYS_COOP"
        if (
            total_rounds >= 12
            and opp_coop_rate < 0.1
            and dc_ratio < 0.05
            and pc_given_c < 0.4
            and coop_samples >= 6
        ):
            return "ALWAYS_DEF"
        if entropy > 0.7 and bias < 0.15 and pattern_confidence < 0.6:
            return "RANDOM"
        if mirror_ratio > 0.75 and total_rounds >= 8:
            return "REACTIVE"
        if abs(pc_given_c - pc_given_d) > 0.3 and mirror_ratio > 0.6:
            return "REACTIVE"
        if pattern_confidence > 0.6:
            return "PATTERN"
        if forgiveness > 0.4 and opp_coop_rate > 0.6:
            return "FORGIVING"
        return "ADAPTIVE"

    def _gather_context(self) -> dict:
        """Collect aggregate statistics for the current opponent."""
        total = max(1, self.cc + self.cd + self.dc + self.dd)
        opp_coop_rate = (self.cc + self.dc) / total
        pc_given_c = self.cc / max(1, self.cc + self.cd)
        pc_given_d = self.dc / max(1, self.dc + self.dd)
        entropy = self._randomness_indicator()
        forgiveness = self.dc / max(1, self.dc + self.dd)
        pattern_prediction = self._predict_pattern_move()
        cd_ratio = self.cd / total
        dc_ratio = self.dc / total
        coop_samples = self.cc + self.cd
        def_samples = self.dc + self.dd
        mirror_ratio = self.mirror_count / max(1, self.total_pairs)
        tag = self._classify_opponent(
            opp_coop_rate,
            pc_given_c,
            pc_given_d,
            entropy,
            forgiveness,
            self.pattern_confidence,
            total,
            cd_ratio,
            dc_ratio,
            coop_samples,
            def_samples,
            mirror_ratio,
            self.retaliation_flag,
        )
        return {
            "opp_coop_rate": opp_coop_rate,
            "pc_given_c": pc_given_c,
            "pc_given_d": pc_given_d,
            "entropy": entropy,
            "forgiveness": forgiveness,
            "pattern_prediction": pattern_prediction,
            "tag": tag,
            "pattern_confidence": self.pattern_confidence,
            "total_rounds": total,
            "mirror_ratio": mirror_ratio,
            "retaliated": self.retaliation_flag,
        }

    def _extract_last_round(self, history: History):
        """Return the (my_move, opp_move) pair from the latest history entry."""
        if history is None:
            return self.last_move, self.last_opp_move
        try:
            if len(history) == 0:
                return self.last_move, self.last_opp_move
            entry = history[-1]
        except (TypeError, IndexError):
            return self.last_move, self.last_opp_move

        my_move = self._extract_move(entry, True)
        opp_move = self._extract_move(entry, False)
        return my_move, opp_move

    def _extract_move(self, entry: HistoryEntry, mine: bool):
        """Normalize different HistoryEntry representations into Move values."""
        attr = "self" if mine else "other"
        candidate = getattr(entry, attr, None)

        if candidate is None and isinstance(entry, (list, tuple)):
            try:
                candidate = entry[0 if mine else 1]
            except IndexError:
                candidate = None

        if isinstance(candidate, Move):
            return candidate
        if isinstance(candidate, str):
            candidate = candidate.lower()
            if candidate.startswith("c"):
                return Move.COOPERATE
            if candidate.startswith("d"):
                return Move.DEFECT
            return None
        if candidate is None:
            return None
        if isinstance(candidate, int):
            return Move.COOPERATE if candidate == 0 else Move.DEFECT
        if hasattr(candidate, "value"):
            value = candidate.value
            if value in (0, 1):
                return Move.COOPERATE if value == 0 else Move.DEFECT
        return None

    def _update_transitions(self, my_last: Move, opp_last: Move) -> None:
        """Update transition counts using the latest outcome."""
        if self.pending_features is not None:
            self._perceptron_learn(self.pending_features, opp_last)
            self.pending_features = None
        if my_last is not None and opp_last is not None:
            self.total_pairs += 1
            if my_last == opp_last:
                self.mirror_count += 1
        if my_last == Move.COOPERATE and opp_last == Move.COOPERATE:
            self.cc += 1
        elif my_last == Move.COOPERATE and opp_last == Move.DEFECT:
            self.cd += 1
            self.retaliation_flag = True
        elif my_last == Move.DEFECT and opp_last == Move.COOPERATE:
            self.dc += 1
        else:
            self.dd += 1
        self._record_recent_history(my_last, opp_last)

    def _record_recent_history(self, my_last: Move, opp_last: Move) -> None:
        """Track recent moves for pattern detection and random profiling."""
        opp_bit = 0 if opp_last == Move.COOPERATE else 1
        my_bit = 0 if my_last == Move.COOPERATE else 1
        self.opp_history_bits.append(opp_bit)
        self.my_history_bits.append(my_bit)
        if len(self.opp_history_bits) > 600:
            self.opp_history_bits.pop(0)
        if len(self.my_history_bits) > 600:
            self.my_history_bits.pop(0)
        self._update_pattern_guess()

    def _update_pattern_guess(self) -> None:
        """Attempt to identify short repeating patterns in opponent play."""
        history = self.opp_history_bits
        updated = False
        for length in range(2, 7):
            required = length * 2
            if len(history) < required:
                continue
            recent = history[-length:]
            previous = history[-2 * length : -length]
            matches = sum(1 for a, b in zip(recent, previous) if a == b)
            correlation = matches / length
            if correlation >= 0.9:
                self.pattern_sequence = recent[:]
                self.pattern_guess = recent[:]
                self.pattern_confidence = correlation
                updated = True
                break
        if not updated:
            self.pattern_confidence *= 0.85
            if self.pattern_confidence < 0.05:
                self.pattern_guess = None
                self.pattern_sequence = []

    def _predict_pattern_move(self):
        """Predict opponent's next move using the learned repeating pattern."""
        sequence = self.pattern_sequence or self.pattern_guess
        if not sequence or self.pattern_confidence < 0.5:
            return None
        length = len(sequence)
        index = len(self.opp_history_bits) % length
        predicted_bit = sequence[index]
        return Move.COOPERATE if predicted_bit == 0 else Move.DEFECT

    def _pattern_based_counter(
        self, predicted_move: Move, opp_coop_rate: float, phase_three: bool
    ) -> Move:
        """Respond to detected patterns while balancing exploitation and cooperation."""
        if predicted_move == Move.COOPERATE:
            if opp_coop_rate > 0.85 and not phase_three and self.round % 7 != 0:
                return Move.COOPERATE
            if phase_three and self.round % 9 == 0:
                return Move.COOPERATE
            return Move.DEFECT
        # Predicted defection → defend by defecting, with occasional surprise.
        if not phase_three and self.round % 13 == 0:
            return Move.COOPERATE
        return Move.DEFECT

    def _is_random_opponent(self, opp_coop_rate: float, randomness_indicator: float) -> bool:
        """Detect near-uniform opponents to switch into pure defection mode."""
        if self.round < 60:
            return False
        bias = abs(opp_coop_rate - 0.5)
        # Low bias and coin-flip transitions imply random or noise-driven play.
        if bias < 0.07 and randomness_indicator < 0.28:
            return True
        if bias < 0.12 and randomness_indicator < 0.2 and self.round > 200:
            return True
        return False

    def _build_features(self):
        """Construct feature vector for the perceptron based on recent history."""
        if not self.opp_history_bits:
            return None
        opp_bits = self.opp_history_bits
        my_bits = self.my_history_bits
        last_opp = float(opp_bits[-1])
        prev_opp = float(opp_bits[-2]) if len(opp_bits) > 1 else last_opp
        last_my = float(my_bits[-1]) if my_bits else 0.0
        prev_my = float(my_bits[-2]) if len(my_bits) > 1 else last_my

        recent_opp_len = max(1, min(5, len(opp_bits)))
        recent_my_len = max(1, min(5, len(my_bits)))
        opp_recent = sum(opp_bits[-recent_opp_len:]) / recent_opp_len
        my_recent = sum(my_bits[-recent_my_len:]) / recent_my_len

        total = max(1, self.cc + self.cd + self.dc + self.dd)
        opp_coop_rate = (self.cc + self.dc) / total
        pc_given_c = self.cc / max(1, self.cc + self.cd)
        pc_given_d = self.dc / max(1, self.dc + self.dd)
        randomness = self._randomness_indicator()

        features = [
            last_opp,
            last_my,
            prev_opp,
            prev_my,
            opp_recent,
            my_recent,
            opp_coop_rate,
            pc_given_c,
            pc_given_d,
            randomness,
        ]
        return features

    def _perceptron_predict(self, features) -> float:
        """Predict probability of opponent cooperation using logistic regression."""
        if features is None:
            return 0.5
        activation = self.perceptron_bias
        for weight, feature in zip(self.perceptron_weights, features):
            activation += weight * feature
        activation = max(min(activation, 20.0), -20.0)
        return 1.0 / (1.0 + math.exp(-activation))

    def _perceptron_learn(self, features, opp_move: Move) -> None:
        """Online update for the perceptron using logistic loss."""
        if features is None:
            return
        target = 1.0 if opp_move == Move.COOPERATE else 0.0
        prediction = self._perceptron_predict(features)
        error = target - prediction
        eta_t = 0.2 / math.sqrt(1.0 + 0.0005 * max(1, self.round))
        decay = 0.9995
        for i, feature in enumerate(features):
            self.perceptron_weights[i] = (
                self.perceptron_weights[i] * decay + eta_t * error * feature
            )
        self.perceptron_bias = (
            self.perceptron_bias * decay + eta_t * error
        )

    def _randomness_indicator(self) -> float:
        """Estimate how uniform the opponent's recent moves appear."""
        window = self.opp_history_bits[-60:]
        if len(window) < 30:
            return 1.0
        ones = sum(window)
        zeros = len(window) - ones
        balance = abs(ones - zeros) / len(window)
        # Examine transition frequency for additional structure.
        transitions = 0
        changes = 0
        for i in range(1, len(window)):
            transitions += 1
            if window[i] != window[i - 1]:
                changes += 1
        change_rate = changes / max(1, transitions)
        uniformity = (abs(change_rate - 0.5) + balance) / 2
        return uniformity


if __name__ == "__main__":
    tester = StrategyTester(Bot)
    tester.run()
