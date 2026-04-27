from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import re
import numpy as np
from collections import defaultdict

class RuleBasedClassifier:
    def __init__(self, user_id: str, sessions: List[Dict], trades: List[Dict]):
        self.user_id = user_id
        # Sort sessions and trades chronologically
        self.sessions = sorted(sessions, key=lambda x: x.get('startedAt') or x.get('started_at', ''))
        self.trades = sorted(trades, key=lambda x: x.get('entryAt') or x.get('entry_at', ''))

    def parse_time(self, t_str: str) -> datetime:
        if not t_str:
            return datetime.now(timezone.utc)
        if isinstance(t_str, datetime):
            return t_str
        # Basic ISO 8601 parser
        try:
            return datetime.fromisoformat(t_str.replace('Z', '+00:00'))
        except ValueError:
            return datetime.now(timezone.utc)

    def generate_profile(self) -> Dict[str, Any]:
        dominant_pathologies = []
        
        # We will compute the probability/confidence for each pathology
        pathology_evaluators = [
            self._eval_revenge_trading,
            self._eval_overtrading,
            self._eval_fomo_entries,
            self._eval_plan_non_adherence,
            self._eval_premature_exit,
            self._eval_loss_running,
            self._eval_session_tilt,
            self._eval_time_of_day_bias,
            self._eval_position_sizing_inconsistency
        ]
        
        for evaluator in pathology_evaluators:
            res = evaluator()
            if res and res.get('confidence', 0) > 0.3:  # Threshold for reporting
                dominant_pathologies.append(res)
        
        # Sort by confidence
        dominant_pathologies.sort(key=lambda x: x['confidence'], reverse=True)
        
        return {
            "userId": self.user_id,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "dominantPathologies": dominant_pathologies,
            "strengths": self._detect_strengths(),
            "peakPerformanceWindow": self._detect_peak_performance()
        }

    def _eval_revenge_trading(self) -> Optional[Dict]:
        evidence_trades = []
        evidence_sessions = set()
        
        for i in range(1, len(self.trades)):
            prev_trade = self.trades[i-1]
            curr_trade = self.trades[i]
            
            # Condition: opened within 90 seconds of a losing close
            prev_exit_str = prev_trade.get('exitAt') or prev_trade.get('exit_at')
            curr_entry_str = curr_trade.get('entryAt') or curr_trade.get('entry_at')
            if not prev_exit_str or not curr_entry_str:
                continue
                
            prev_exit = self.parse_time(prev_exit_str)
            curr_entry = self.parse_time(curr_entry_str)
            diff = (curr_entry - prev_exit).total_seconds()
            
            outcome = prev_trade.get('outcome', '').lower()
            emotional = curr_trade.get('emotionalState') or curr_trade.get('emotional_state', '')
            revenge_flag = curr_trade.get('revengeFlag') or curr_trade.get('revenge_flag', False)
            
            if diff <= 90 and outcome == 'loss' and emotional.lower() in ['anxious', 'fearful'] and revenge_flag:
                trade_id = curr_trade.get('tradeId') or curr_trade.get('trade_id')
                session_id = curr_trade.get('sessionId') or curr_trade.get('session_id')
                if trade_id: evidence_trades.append(trade_id)
                if session_id: evidence_sessions.add(session_id)
                
        confidence = min(len(evidence_trades) / max(len(self.trades) * 0.1, 1.0), 1.0)
        return {
            "pathology": "revenge_trading",
            "confidence": round(confidence, 2),
            "evidenceSessions": list(evidence_sessions),
            "evidenceTrades": evidence_trades
        }

    def _eval_overtrading(self) -> Optional[Dict]:
        evidence_trades = []
        evidence_sessions = set()
        windows_count = 0
        
        # O(N^2) but N is small
        for i in range(len(self.trades)):
            start_time = self.parse_time(self.trades[i].get('entryAt') or self.trades[i].get('entry_at'))
            count = 0
            window_trades = []
            for j in range(i, len(self.trades)):
                curr_time = self.parse_time(self.trades[j].get('entryAt') or self.trades[j].get('entry_at'))
                if (curr_time - start_time).total_seconds() <= 1800: # 30 mins
                    count += 1
                    window_trades.append(self.trades[j])
                else:
                    break
            if count > 10:
                windows_count += 1
                for t in window_trades:
                    t_id = t.get('tradeId') or t.get('trade_id')
                    s_id = t.get('sessionId') or t.get('session_id')
                    if t_id and t_id not in evidence_trades: evidence_trades.append(t_id)
                    if s_id: evidence_sessions.add(s_id)
                    
        confidence = min(windows_count / 3.0, 1.0) if windows_count > 0 else 0.0
        return {
            "pathology": "overtrading",
            "confidence": round(confidence, 2),
            "evidenceSessions": list(evidence_sessions),
            "evidenceTrades": evidence_trades
        }

    def _eval_fomo_entries(self) -> Optional[Dict]:
        evidence_trades = []
        evidence_sessions = set()
        
        fomo_keywords = ['already moved', 'trying to catch', 'missed', 'too late', 'catching', 'jumping in']
        for t in self.trades:
            rationale = (t.get('entryRationale') or t.get('entry_rationale', '')).lower()
            adherence = t.get('planAdherence') or t.get('plan_adherence', 5)
            
            has_fomo_language = any(kw in rationale for kw in fomo_keywords)
            if has_fomo_language and int(adherence) <= 3:
                trade_id = t.get('tradeId') or t.get('trade_id')
                session_id = t.get('sessionId') or t.get('session_id')
                if trade_id: evidence_trades.append(trade_id)
                if session_id: evidence_sessions.add(session_id)
                
        confidence = min(len(evidence_trades) / max(len(self.trades) * 0.1, 1.0), 1.0)
        return {
            "pathology": "fomo_entries",
            "confidence": round(confidence, 2),
            "evidenceSessions": list(evidence_sessions),
            "evidenceTrades": evidence_trades
        }

    def _eval_plan_non_adherence(self) -> Optional[Dict]:
        evidence_trades = []
        evidence_sessions = set()
        
        non_plan_kws = ['not in plan', 'deviated', 'no plan', 'impulse', 'random']
        for t in self.trades:
            rationale = (t.get('entryRationale') or t.get('entry_rationale', '')).lower()
            adherence = t.get('planAdherence') or t.get('plan_adherence', 5)
            
            has_kw = any(kw in rationale for kw in non_plan_kws)
            if int(adherence) <= 2 and has_kw:
                trade_id = t.get('tradeId') or t.get('trade_id')
                session_id = t.get('sessionId') or t.get('session_id')
                if trade_id: evidence_trades.append(trade_id)
                if session_id: evidence_sessions.add(session_id)
                
        confidence = min(len(evidence_trades) / max(len(self.trades) * 0.1, 1.0), 1.0)
        return {
            "pathology": "plan_non_adherence",
            "confidence": round(confidence, 2),
            "evidenceSessions": list(evidence_sessions),
            "evidenceTrades": evidence_trades
        }

    def _eval_premature_exit(self) -> Optional[Dict]:
        evidence_trades = []
        evidence_sessions = set()
        
        winning_hold_times = []
        losing_hold_times = []
        for t in self.trades:
            entry = self.parse_time(t.get('entryAt') or t.get('entry_at'))
            exit_time_str = t.get('exitAt') or t.get('exit_at')
            if not exit_time_str: continue
            exit_t = self.parse_time(exit_time_str)
            hold = (exit_t - entry).total_seconds()
            if t.get('outcome') == 'win':
                winning_hold_times.append((t, hold))
            else:
                losing_hold_times.append((t, hold))
                
        if winning_hold_times and losing_hold_times:
            avg_win_hold = sum(x[1] for x in winning_hold_times) / len(winning_hold_times)
            avg_loss_hold = sum(x[1] for x in losing_hold_times) / len(losing_hold_times)
            
            for t, hold in winning_hold_times:
                emotional = (t.get('emotionalState') or t.get('emotional_state', '')).lower()
                if hold < avg_win_hold * 0.5 and emotional == 'fearful':
                    trade_id = t.get('tradeId') or t.get('trade_id')
                    session_id = t.get('sessionId') or t.get('session_id')
                    if trade_id: evidence_trades.append(trade_id)
                    if session_id: evidence_sessions.add(session_id)
                    
        confidence = min(len(evidence_trades) / max(len(self.trades) * 0.05, 1.0), 1.0)
        return {
            "pathology": "premature_exit",
            "confidence": round(confidence, 2),
            "evidenceSessions": list(evidence_sessions),
            "evidenceTrades": evidence_trades
        }

    def _eval_loss_running(self) -> Optional[Dict]:
        evidence_trades = []
        evidence_sessions = set()
        
        winning_hold_times = []
        losing_hold_times = []
        for t in self.trades:
            entry = self.parse_time(t.get('entryAt') or t.get('entry_at'))
            exit_time_str = t.get('exitAt') or t.get('exit_at')
            if not exit_time_str: continue
            exit_t = self.parse_time(exit_time_str)
            hold = (exit_t - entry).total_seconds()
            if t.get('outcome') == 'win':
                winning_hold_times.append(hold)
            else:
                losing_hold_times.append((t, hold))
                
        if winning_hold_times and losing_hold_times:
            avg_win_hold = sum(winning_hold_times) / len(winning_hold_times)
            
            for t, hold in losing_hold_times:
                emotional = (t.get('emotionalState') or t.get('emotional_state', '')).lower()
                rationale = (t.get('entryRationale') or t.get('entry_rationale', '')).lower()
                has_hope = 'hop' in rationale or 'come back' in rationale # hoping, hope
                if hold > avg_win_hold * 1.5 and emotional == 'fearful' and has_hope:
                    trade_id = t.get('tradeId') or t.get('trade_id')
                    session_id = t.get('sessionId') or t.get('session_id')
                    if trade_id: evidence_trades.append(trade_id)
                    if session_id: evidence_sessions.add(session_id)
                    
        confidence = min(len(evidence_trades) / max(len(self.trades) * 0.05, 1.0), 1.0)
        return {
            "pathology": "loss_running",
            "confidence": round(confidence, 2),
            "evidenceSessions": list(evidence_sessions),
            "evidenceTrades": evidence_trades
        }

    def _eval_session_tilt(self) -> Optional[Dict]:
        evidence_trades = []
        evidence_sessions = set()
        
        for session in self.sessions:
            s_id = session.get('sessionId') or session.get('session_id')
            s_trades = [t for t in self.trades if (t.get('sessionId') or t.get('session_id')) == s_id]
            s_trades.sort(key=lambda x: self.parse_time(x.get('entryAt') or x.get('entry_at')))
            
            consecutive_losses = 0
            for i in range(len(s_trades)):
                t = s_trades[i]
                    
                adherence = int(t.get('planAdherence') or t.get('plan_adherence', 5))
                if consecutive_losses >= 2 and adherence <= 2:
                    evidence_sessions.add(s_id)
                    trade_id = t.get('tradeId') or t.get('trade_id')
                    if trade_id: evidence_trades.append(trade_id)

                if t.get('outcome') == 'loss':
                    consecutive_losses += 1
                else:
                    consecutive_losses = 0
                    
        confidence = min(len(evidence_sessions) / max(len(self.sessions) * 0.2, 1.0), 1.0)
        return {
            "pathology": "session_tilt",
            "confidence": round(confidence, 2),
            "evidenceSessions": list(evidence_sessions),
            "evidenceTrades": evidence_trades
        }

    def _eval_time_of_day_bias(self) -> Optional[Dict]:
        evidence_trades = []
        evidence_sessions = set()
        
        hour_pnl = defaultdict(list)
        for t in self.trades:
            entry = self.parse_time(t.get('entryAt') or t.get('entry_at'))
            hour = entry.hour
            pnl = t.get('pnl') or 0
            hour_pnl[hour].append((pnl, t))
            
        confidence = 0.0
        for hr, pnl_trades in hour_pnl.items():
            if len(pnl_trades) >= 5:
                avg_pnl = sum(x[0] for x in pnl_trades) / len(pnl_trades)
                # If avg PNL is very negative for a specific hour
                if avg_pnl < -50:  # arbitrary heuristic threshold for negative impact
                    for _, t in pnl_trades:
                        trade_id = t.get('tradeId') or t.get('trade_id')
                        session_id = t.get('sessionId') or t.get('session_id')
                        if trade_id: evidence_trades.append(trade_id)
                        if session_id: evidence_sessions.add(session_id)
                    confidence = max(confidence, 0.8)
                    
        return {
            "pathology": "time_of_day_bias",
            "confidence": round(confidence, 2),
            "evidenceSessions": list(evidence_sessions),
            "evidenceTrades": evidence_trades
        }

    def _eval_position_sizing_inconsistency(self) -> Optional[Dict]:
        evidence_trades = []
        evidence_sessions = set()
        
        asset_classes = defaultdict(list)
        for t in self.trades:
            ac = t.get('assetClass') or t.get('asset_class')
            q = t.get('quantity')
            if ac and q is not None:
                asset_classes[ac].append((q, t))
                
        highest_cv = 0
        for ac, qt_list in asset_classes.items():
            if len(qt_list) > 3:
                quantities = [x[0] for x in qt_list]
                mean = np.mean(quantities)
                std = np.std(quantities)
                cv = std / mean if mean > 0 else 0
                highest_cv = max(highest_cv, cv)
                if cv > 0.5: # CV > 50% means high inconsistency
                    for _, t in qt_list:
                        trade_id = t.get('tradeId') or t.get('trade_id')
                        session_id = t.get('sessionId') or t.get('session_id')
                        if trade_id: evidence_trades.append(trade_id)
                        if session_id: evidence_sessions.add(session_id)
                        
        confidence = min(highest_cv, 1.0)
        return {
            "pathology": "position_sizing_inconsistency",
            "confidence": round(confidence, 2),
            "evidenceSessions": list(evidence_sessions),
            "evidenceTrades": evidence_trades
        }

    def _detect_strengths(self) -> List[str]:
        strengths = []
        high_adherence = sum(1 for t in self.trades if int(t.get('planAdherence') or t.get('plan_adherence', 0)) >= 4)
        if high_adherence / max(len(self.trades), 1) > 0.6:
            strengths.append("Generally follows trading plan in most trades.")
            
        win_rate = sum(1 for t in self.trades if t.get('outcome') == 'win') / max(len(self.trades), 1)
        if win_rate > 0.55:
            strengths.append("Maintains a positive win rate overall.")
            
        return strengths

    def _detect_peak_performance(self) -> Optional[Dict]:
        hour_stats = defaultdict(lambda: {"wins": 0, "total": 0})
        for t in self.trades:
            entry = self.parse_time(t.get('entryAt') or t.get('entry_at'))
            hour = entry.hour
            hour_stats[hour]["total"] += 1
            if t.get('outcome') == 'win':
                hour_stats[hour]["wins"] += 1
                
        best_hour = -1
        best_win_rate = 0
        for h, stats in hour_stats.items():
            if stats["total"] >= 3:
                wr = stats["wins"] / stats["total"]
                if wr > best_win_rate:
                    best_win_rate = wr
                    best_hour = h
                    
        if best_hour >= 0 and best_win_rate > 0.5:
            return {
                "startHour": best_hour,
                "endHour": (best_hour + 1) % 24,
                "winRate": round(best_win_rate, 2)
            }
        return None
