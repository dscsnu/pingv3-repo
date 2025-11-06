from ping_game_theory import Strategy, StrategyTester, History, HistoryEntry, Move
import random, math
from collections import deque, Counter

class OmegaBot(Strategy):
    """Universal dominator: detects periodic calibrators, patterns, punishers, noisy, coop, and adapts."""
    def _init_(self) -> None:
        self.author_netid = "hb969"
        self.strategy_name = "OmegaBot_MetaDominator"
        self.strategy_desc = "Adaptive universal bot: detect periodic, pattern, punisher, coop, noisy; exploit safely."

        # parameters
        self.trust_build = 6
        self.detect_window = 120
        self.short_window = 50
        self.pattern_check_lengths = range(2, 8)
        self.max_exploit_frac = 0.02    # max fraction of total rounds we may exploit pure cooperators
        self.base_exploit = 0.002
        self.max_exploit_rate = 0.06
        self.forgive_prob = 0.02
        self.randomize_rate = 0.005
        self.endgame_start = 9900

        # state
        self.opp_bits = deque(maxlen=2000)   # 0 coop, 1 defect
        self.my_bits = deque(maxlen=2000)
        self.cc = self.cd = self.dc = self.dd = 0
        self.total_seen = 0
        self.pattern_seq = None
        self.pattern_conf = 0.0
        self.exploit_budget = 0
        self.exploit_used = 0
        self.mode = "UNKNOWN"
        self.last_move = None

        # periodic-calibrator detection
        self.periodic_k = None
        self.periodic_conf = 0.0
        self.calibration_phase_detected = False
        self.calibration_window_max = 40  # ModePoison used 30; cover up to 40
        self.calibration_min_samples = 10

    def begin(self) -> Move:
        # reset
        self.opp_bits.clear(); self.my_bits.clear()
        self.cc = self.cd = self.dc = self.dd = 0
        self.total_seen = 0
        self.pattern_seq = None; self.pattern_conf = 0.0
        self.exploit_budget = 0; self.exploit_used = 0
        self.mode = "UNKNOWN"
        self.periodic_k = None; self.periodic_conf = 0.0
        self.calibration_phase_detected = False
        self.last_move = None
        # open cooperative to attract cooperators
        self.last_move = Move.COOPERATE
        return Move.COOPERATE

    # ---------- utils ----------
    def _update_counts(self, my_move: Move, opp_move: Move):
        if my_move == Move.COOPERATE and opp_move == Move.COOPERATE: self.cc += 1
        elif my_move == Move.COOPERATE and opp_move == Move.DEFECT: self.cd += 1
        elif my_move == Move.DEFECT and opp_move == Move.COOPERATE: self.dc += 1
        else: self.dd += 1
        self.my_bits.append(0 if my_move == Move.COOPERATE else 1)
        self.opp_bits.append(0 if opp_move == Move.COOPERATE else 1)
        self.total_seen += 1

    def _opp_coop_rate(self, window=None):
        if window is None: window = len(self.opp_bits)
        if window == 0: return 0.5
        seq = list(self.opp_bits)[-window:]
        return seq.count(0) / len(seq)

    def _recent_defect_rate(self, window):
        if len(self.opp_bits) == 0: return 0.0
        seq = list(self.opp_bits)[-window:] if len(self.opp_bits) >= window else list(self.opp_bits)
        return seq.count(1) / len(seq)

    # ---------- pattern detection ----------
    def _detect_short_pattern(self):
        history = list(self.opp_bits)
        if len(history) < 8:
            self.pattern_seq = None; self.pattern_conf = 0.0; return
        for L in self.pattern_check_lengths:
            if len(history) < 2*L: continue
            recent = history[-L:]; prev = history[-2*L:-L]
            matches = sum(1 for a,b in zip(recent, prev) if a==b)
            corr = matches / L
            if corr >= 0.88:
                self.pattern_seq = recent[:]
                self.pattern_conf = corr
                return
        # decay
        self.pattern_conf *= 0.85
        if self.pattern_conf < 0.05:
            self.pattern_seq = None; self.pattern_conf = 0.0

    def _predict_pattern(self):
        if not self.pattern_seq or self.pattern_conf < 0.5: return None
        idx = len(self.opp_bits) % len(self.pattern_seq)
        bit = self.pattern_seq[idx]
        return Move.COOPERATE if bit == 0 else Move.DEFECT

    # ---------- periodic calibrator detection (ModePoison-like) ----------
    def _detect_periodic_k(self):
        """Detect if opponent defects in a periodic schedule during early rounds.
           We search k from 2..8 and check if defects are concentrated at positions mod k."""
        hist = list(self.opp_bits)
        n = len(hist)
        if n < self.calibration_min_samples: 
            self.periodic_k = None; self.periodic_conf = 0.0; return
        best_k, best_conf = None, 0.0
        for k in range(2,9):
            # count defects at each residue
            counts = [0]*k
            totals = [0]*k
            for i,bit in enumerate(hist):
                r = (i+1) % k  # round indices (1-based) modulo k
                totals[r] += 1
                if bit==1: counts[r]+=1
            # find residue with highest defect fraction
            fracs = [(counts[r]/totals[r] if totals[r]>0 else 0.0) for r in range(k)]
            max_frac = max(fracs)
            # confidence: how concentrated defect mass is at that residue
            other_frac = (sum(fracs)-max_frac)/(k-1) if k>1 else 0.0
            conf = max_frac - other_frac
            # prefer larger sample sizes for significant conf
            if conf > best_conf and totals[fracs.index(max_frac)] >= max(6, n//(2*k)):
                best_conf = conf; best_k = k
        if best_conf > 0.45 and best_k is not None:
            self.periodic_k = best_k
            self.periodic_conf = best_conf
            # mark as calibration if we are still in early stage (<= calibration_window)
            if self.total_seen <= self.calibration_window_max:
                self.calibration_phase_detected = True
        else:
            # decay
            self.periodic_conf *= 0.85
            if self.periodic_conf < 0.05:
                self.periodic_k = None; self.periodic_conf = 0.0

    # ---------- classification ----------
    def _classify(self):
        n = len(self.opp_bits)
        if n < 6: return "UNKNOWN"
        full = list(self.opp_bits)
        coop_rate = full.count(0)/n
        changes = sum(1 for i in range(1,n) if full[i]!=full[i-1])
        stability = 1 - (changes / max(1, n-1))
        if coop_rate > 0.95: return "COOPERATOR"
        if coop_rate < 0.05: return "DEFECTOR"
        if stability > 0.8 and coop_rate > 0.6: return "TIT_FOR_TAT"
        if self.pattern_conf > 0.6: return "PATTERN"
        bias = abs(coop_rate-0.5)
        if bias < 0.08 and (changes / max(1,n-1)) > 0.4: return "NOISY"
        return "ADAPTIVE"

    def _set_exploit_budget(self):
        if self.exploit_budget==0:
            remaining = max(1, 10000 - self.total_seen)
            self.exploit_budget = math.ceil(self.max_exploit_frac * remaining)

    # ---------- core decision ----------
    def turn(self, history: History) -> Move:
        # normalize history: get last round pair if exists
        if history is None:
            history = tuple()
        if len(history)>0:
            last = history[-1]
            my_last = getattr(last, "self", None)
            opp_last = getattr(last, "other", None)
            if my_last is None or opp_last is None:
                # maybe tuple
                try:
                    my_last, opp_last = last
                except Exception:
                    pass
            if isinstance(my_last, Move) and isinstance(opp_last, Move):
                self._update_counts(my_last, opp_last)

        # early trust
        if self.total_seen < self.trust_build:
            self.last_move = Move.COOPERATE
            return Move.COOPERATE

        # detect periodic calibrator and patterns
        self._detect_periodic_k()
        self._detect_short_pattern()
        cls = self._classify()
        recent_def = self._recent_defect_rate(self.short_window)
        overall_coop = self._opp_coop_rate()

        # Immediately handle obvious always-defector
        if cls == "DEFECTOR" or overall_coop < 0.05:
            self.last_move = Move.DEFECT
            return Move.DEFECT

        # If periodic calibrator detected and we're in its calibration window (early), exploit schedule
        if self.calibration_phase_detected and self.periodic_k is not None and self.total_seen <= self.calibration_window_max:
            k = self.periodic_k
            # find residue r where defects concentrate
            # compute residue defect fractions
            hist = list(self.opp_bits)
            counts=[0]*k; totals=[0]*k
            for i,bit in enumerate(hist):
                r=(i+1)%k
                totals[r]+=1
                if bit==1: counts[r]+=1
            fracs = [ (counts[r]/totals[r]) if totals[r]>0 else 0.0 for r in range(k)]
            rmax = max(range(k), key=lambda r: fracs[r])
            # our schedule: DEFECT on rounds whose residue != rmax (i.e., when they likely cooperate),
            # COOPERATE when their residue == rmax (they likely defect) to avoid mutual D on those indices.
            current_round_index = self.total_seen + 1
            res = current_round_index % k
            if res != rmax:
                # defect to exploit their cooperation
                self.last_move = Move.DEFECT
                return Move.DEFECT
            else:
                # avoid being defected against, play cooperate
                self.last_move = Move.COOPERATE
                return Move.COOPERATE

        # if pure cooperator -> bounded exploitation
        if cls == "COOPERATOR" or overall_coop > 0.92:
            self._set_exploit_budget()
            # compute coop streak
            coop_streak = 0
            for b in reversed(self.opp_bits):
                if b==0: coop_streak+=1
                else: break
            exploit_rate = min(self.max_exploit_rate, self.base_exploit + 0.02*max(0, coop_streak-3))
            remaining = max(1, 10000 - self.total_seen)
            prob_use = min(exploit_rate, max(0.0, (self.exploit_budget - self.exploit_used)/remaining))
            if random.random() < prob_use:
                self.exploit_used += 1
                self.last_move = Move.DEFECT
                return Move.DEFECT
            self.last_move = Move.COOPERATE
            return Move.COOPERATE

        # pattern opponents: predict and exploit predicted cooperations
        if cls == "PATTERN" and self.pattern_seq is not None:
            pred = self._predict_pattern()
            if pred == Move.COOPERATE:
                # exploit with high probability (but add small randomness)
                if random.random() < 0.9:
                    self.last_move = Move.DEFECT
                    return Move.DEFECT
                else:
                    self.last_move = Move.COOPERATE
                    return Move.COOPERATE
            else:
                # predicted defect -> defend
                self.last_move = Move.DEFECT
                return Move.DEFECT

        # Tit-for-tat / punitive players: mirror to maintain cooperation
        if cls == "TIT_FOR_TAT" or (cls=="ADAPTIVE" and recent_def < 0.25):
            # mirror last opponent move
            if len(self.opp_bits)==0:
                self.last_move = Move.COOPERATE
            else:
                self.last_move = Move.COOPERATE if self.opp_bits[-1]==0 else Move.DEFECT
            # occasional forgiveness
            if self.last_move==Move.DEFECT and random.random() < self.forgive_prob:
                self.last_move = Move.COOPERATE
            # tiny randomization
            if random.random() < self.randomize_rate:
                self.last_move = Move.COOPERATE if random.random()<0.5 else Move.DEFECT
            return self.last_move

        # noisy opponents: be stable and avoid wild swings
        if cls == "NOISY":
            if recent_def > 0.45:
                self.last_move = Move.DEFECT
            else:
                self.last_move = Move.COOPERATE
            if random.random() < self.forgive_prob:
                self.last_move = Move.COOPERATE
            return self.last_move

        # fallback: compute immediate expected values using conditional estimates
        pc_if_c = self.cc / max(1, self.cc + self.cd)
        pc_if_d = self.dc / max(1, self.dc + self.dd)
        exp_c = 3 * pc_if_c
        exp_d = 5 * pc_if_d + 1 * (1 - pc_if_d)

        # endgame aggression
        if self.total_seen >= self.endgame_start:
            if random.random() < 0.9:
                self.last_move = Move.DEFECT
                return Move.DEFECT

        if abs(exp_d - exp_c) < 0.06:
            self.last_move = Move.COOPERATE if random.random() < 0.92 else Move.DEFECT
        elif exp_d > exp_c:
            self.last_move = Move.DEFECT
        else:
            self.last_move = Move.COOPERATE

        # small randomization to prevent meta-learning exploitation
        if random.random() < self.randomize_rate:
            self.last_move = Move.COOPERATE if random.random()<0.5 else Move.DEFECT

        return self.last_move

# If you want to quickly test: 
# tester = StrategyTester(OmegaBot)
# tester.run()