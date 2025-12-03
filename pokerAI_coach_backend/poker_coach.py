"""
Advanced Poker Coach Module
Provides strategic advice, pot odds, equity estimation, and position-aware recommendations.
"""

from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import random

RANKS = "23456789TJQKA"
SUITS = "shdc"


@dataclass
class CoachAdvice:
    """Structured coaching advice"""
    recommendation: str  # "fold", "check", "call", "bet", "raise"
    reasoning: str
    pot_odds: Optional[float] = None
    equity_estimate: Optional[float] = None
    hand_strength: Optional[str] = None
    outs: Optional[int] = None
    confidence: str = "medium"  # "low", "medium", "high"
    alternative: Optional[str] = None


class PokerCoach:
    """Advanced poker coaching system"""
    
    def __init__(self):
        # Position-based preflop ranges (simplified)
        self.preflop_ranges = self._build_preflop_ranges()
    
    def _build_preflop_ranges(self) -> Dict[str, set]:
        """Build position-based opening ranges"""
        return {
            "UTG": {  # Under the gun - tightest
                "AA", "KK", "QQ", "JJ", "TT", "99",
                "AKs", "AQs", "AJs", "AKo", "AQo"
            },
            "MP": {  # Middle position
                "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77",
                "AKs", "AQs", "AJs", "ATs", "KQs", "KJs", "QJs",
                "AKo", "AQo", "AJo", "KQo"
            },
            "CO": {  # Cutoff - wider
                "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55",
                "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A5s", "A4s", "A3s", "A2s",
                "KQs", "KJs", "KTs", "QJs", "QTs", "JTs", "T9s", "98s",
                "AKo", "AQo", "AJo", "ATo", "KQo", "KJo", "QJo"
            },
            "BTN": {  # Button - widest
                "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
                "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
                "KQs", "KJs", "KTs", "K9s", "QJs", "QTs", "Q9s", "JTs", "J9s", "T9s", "T8s", "98s", "87s", "76s",
                "AKo", "AQo", "AJo", "ATo", "A9o", "KQo", "KJo", "KTo", "QJo", "QTo", "JTo"
            },
            "SB": {  # Small blind vs BB
                "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
                "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
                "KQs", "KJs", "KTs", "K9s", "K8s", "QJs", "QTs", "Q9s", "JTs", "J9s", "T9s", "T8s", "98s", "87s",
                "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "KQo", "KJo", "KTo", "QJo"
            }
        }
    
    def get_advice(self, hero_hand: List[str], community_cards: List[str],
                   pot: int, current_bet: int, hero_contribution: int,
                   hero_stack: int, position: str, street: str,
                   num_opponents: int) -> CoachAdvice:
        """
        Main method to get coaching advice
        
        Args:
            hero_hand: List of 2 hole cards like ['Ah', 'Kd']
            community_cards: List of board cards
            pot: Current pot size
            current_bet: Current bet to call
            hero_contribution: What hero has put in this street
            hero_stack: Hero's remaining stack
            position: "UTG", "MP", "CO", "BTN", "SB", "BB"
            street: "preflop", "flop", "turn", "river"
            num_opponents: Number of active opponents
        """
        
        if street == "preflop":
            return self._preflop_advice(hero_hand, pot, current_bet, hero_contribution,
                                       hero_stack, position, num_opponents)
        else:
            return self._postflop_advice(hero_hand, community_cards, pot, current_bet,
                                        hero_contribution, hero_stack, position, street,
                                        num_opponents)
    
    def _preflop_advice(self, hero_hand: List[str], pot: int, current_bet: int,
                       hero_contribution: int, hero_stack: int, position: str,
                       num_opponents: int) -> CoachAdvice:
        """Preflop strategy advice"""
        
        if len(hero_hand) != 2:
            return CoachAdvice("fold", "Invalid hand", confidence="high")
        
        hand_code = self._hand_to_code(hero_hand[0], hero_hand[1])
        to_call = current_bet - hero_contribution
        
        # Get position range
        pos_range = self.preflop_ranges.get(position, self.preflop_ranges["MP"])
        
        # Basic hand strength
        strength = self._preflop_hand_strength(hero_hand)
        
        # Facing a raise?
        facing_raise = to_call > 0 and current_bet > pot * 0.1
        
        if facing_raise:
            # Tighten up when facing aggression
            if hand_code in ["AA", "KK", "QQ", "AKs", "AKo"]:
                return CoachAdvice(
                    "raise",
                    f"Premium hand ({hand_code}). 3-bet for value. You have ~{int(strength*100)}% equity advantage.",
                    equity_estimate=strength,
                    hand_strength="Premium",
                    confidence="high",
                    alternative="Call to trap occasionally with AA/KK"
                )
            elif hand_code in ["JJ", "TT", "AQs", "AQo", "KQs"]:
                pot_odds = to_call / (pot + to_call) if pot + to_call > 0 else 0
                return CoachAdvice(
                    "call",
                    f"Strong hand ({hand_code}). Call to see flop. Pot odds: {pot_odds:.1%}, estimated equity: ~{int(strength*100)}%",
                    pot_odds=pot_odds,
                    equity_estimate=strength,
                    hand_strength="Strong",
                    confidence="medium",
                    alternative="3-bet as a bluff occasionally"
                )
            elif strength > 0.4:
                pot_odds = to_call / (pot + to_call) if pot + to_call > 0 else 0
                if pot_odds < 0.35 and num_opponents <= 2:
                    return CoachAdvice(
                        "call",
                        f"Decent hand ({hand_code}). Pot odds {pot_odds:.1%} are favorable for speculative call.",
                        pot_odds=pot_odds,
                        equity_estimate=strength,
                        hand_strength="Marginal",
                        confidence="medium"
                    )
                else:
                    return CoachAdvice(
                        "fold",
                        f"Hand ({hand_code}) too weak facing raise from {num_opponents} opponent(s). Pot odds {pot_odds:.1%} unfavorable.",
                        pot_odds=pot_odds,
                        confidence="medium"
                    )
            else:
                return CoachAdvice(
                    "fold",
                    f"Weak hand ({hand_code}). Clear fold facing aggression.",
                    confidence="high"
                )
        
        # Unopened pot - should we open?
        elif to_call == 0:
            if hand_code in pos_range:
                bet_size = max(pot * 2.5, hero_stack * 0.15)
                return CoachAdvice(
                    "bet",
                    f"Strong hand for {position} ({hand_code}). Open-raise to build pot and take initiative.",
                    hand_strength="In range",
                    confidence="high",
                    alternative=f"Suggested bet size: ~${int(bet_size)}"
                )
            else:
                return CoachAdvice(
                    "fold",
                    f"Hand ({hand_code}) below opening range for {position}. Fold and wait for better spot.",
                    confidence="high",
                    alternative="Could consider limping in SB/BB"
                )
        
        # Facing small bet/blind
        else:
            pot_odds = to_call / (pot + to_call) if pot + to_call > 0 else 0
            if strength > pot_odds or pot_odds < 0.25:
                return CoachAdvice(
                    "call",
                    f"Getting good pot odds ({pot_odds:.1%}). Hand strength ~{int(strength*100)}%. Call to see flop.",
                    pot_odds=pot_odds,
                    equity_estimate=strength,
                    confidence="medium"
                )
            else:
                return CoachAdvice(
                    "fold",
                    f"Pot odds ({pot_odds:.1%}) don't justify call with weak hand.",
                    pot_odds=pot_odds,
                    confidence="medium"
                )
    
    def _postflop_advice(self, hero_hand: List[str], community_cards: List[str],
                        pot: int, current_bet: int, hero_contribution: int,
                        hero_stack: int, position: str, street: str,
                        num_opponents: int) -> CoachAdvice:
        """Postflop strategy advice"""
        
        to_call = current_bet - hero_contribution
        
        # Analyze hand strength
        hand_analysis = self._analyze_postflop_hand(hero_hand, community_cards)
        strength = hand_analysis["strength"]
        made_hand = hand_analysis["made_hand"]
        draw_type = hand_analysis["draw_type"]
        outs = hand_analysis["outs"]
        
        # Calculate pot odds if facing bet
        pot_odds = to_call / (pot + to_call) if (pot + to_call > 0 and to_call > 0) else 0
        
        # Calculate implied odds based on remaining cards
        cards_to_come = 2 if street == "flop" else 1
        win_probability = self._outs_to_probability(outs, cards_to_come)
        
        # No bet to call - check or bet?
        if to_call == 0:
            if made_hand in ["Straight", "Flush", "Full House", "Quads", "Straight Flush"]:
                return CoachAdvice(
                    "bet",
                    f"Strong made hand ({made_hand}). Bet for value to build pot.",
                    equity_estimate=strength,
                    hand_strength=made_hand,
                    confidence="high",
                    alternative=f"Suggested bet: {int(pot * 0.6)}-{int(pot * 0.75)} (60-75% pot)"
                )
            elif made_hand in ["Three of a Kind", "Two Pair"]:
                return CoachAdvice(
                    "bet",
                    f"Good hand ({made_hand}). Bet for value and protection.",
                    equity_estimate=strength,
                    hand_strength=made_hand,
                    confidence="high",
                    alternative=f"Suggested bet: {int(pot * 0.5)} (50% pot)"
                )
            elif made_hand == "Pair" and strength > 0.4:
                return CoachAdvice(
                    "bet",
                    f"Decent pair. Consider betting for thin value or as bluff. Fold equity against {num_opponents} opponent(s).",
                    equity_estimate=strength,
                    hand_strength=made_hand,
                    confidence="medium",
                    alternative="Check is also fine to control pot size"
                )
            elif draw_type and outs >= 8:
                return CoachAdvice(
                    "bet",
                    f"Strong draw ({draw_type}, ~{outs} outs). Semi-bluff to win now or improve. Win probability: {win_probability:.1%}",
                    equity_estimate=win_probability,
                    hand_strength=draw_type,
                    outs=outs,
                    confidence="medium",
                    alternative=f"You improve on ~{win_probability:.1%} of run-outs"
                )
            else:
                return CoachAdvice(
                    "check",
                    f"Weak holding ({made_hand or 'High card'}). Check and see if you can improve cheaply.",
                    equity_estimate=strength,
                    hand_strength=made_hand or "Weak",
                    confidence="medium"
                )
        
        # Facing a bet - call, raise, or fold?
        else:
            # Strong made hands
            if made_hand in ["Straight", "Flush", "Full House", "Quads", "Straight Flush"]:
                if to_call < hero_stack * 0.3:
                    return CoachAdvice(
                        "raise",
                        f"Very strong hand ({made_hand}). Raise for value. Pot odds: {pot_odds:.1%}",
                        pot_odds=pot_odds,
                        equity_estimate=0.85,
                        hand_strength=made_hand,
                        confidence="high"
                    )
                else:
                    return CoachAdvice(
                        "call",
                        f"Strong hand ({made_hand}). Call and consider raising later streets.",
                        pot_odds=pot_odds,
                        equity_estimate=0.85,
                        hand_strength=made_hand,
                        confidence="high"
                    )
            
            # Medium strength hands
            elif made_hand in ["Three of a Kind", "Two Pair"]:
                if pot_odds < 0.4:
                    return CoachAdvice(
                        "call",
                        f"Good hand ({made_hand}). Pot odds {pot_odds:.1%} are favorable. Call and reassess.",
                        pot_odds=pot_odds,
                        equity_estimate=strength,
                        hand_strength=made_hand,
                        confidence="high"
                    )
                else:
                    return CoachAdvice(
                        "fold",
                        f"Hand ({made_hand}) likely behind. Pot odds {pot_odds:.1%} too expensive.",
                        pot_odds=pot_odds,
                        confidence="medium"
                    )
            
            # Draws
            elif draw_type and outs >= 8:
                if pot_odds < win_probability:
                    return CoachAdvice(
                        "call",
                        f"Strong {draw_type} (~{outs} outs, {win_probability:.1%} to improve). Pot odds {pot_odds:.1%} < equity {win_probability:.1%}. Profitable call!",
                        pot_odds=pot_odds,
                        equity_estimate=win_probability,
                        hand_strength=draw_type,
                        outs=outs,
                        confidence="high"
                    )
                elif pot_odds < win_probability * 1.3:  # Some implied odds
                    return CoachAdvice(
                        "call",
                        f"{draw_type} ({outs} outs). Close to pot odds ({pot_odds:.1%} vs {win_probability:.1%}). Consider implied odds.",
                        pot_odds=pot_odds,
                        equity_estimate=win_probability,
                        hand_strength=draw_type,
                        outs=outs,
                        confidence="medium",
                        alternative="Fold if bet is very large relative to stack"
                    )
                else:
                    return CoachAdvice(
                        "fold",
                        f"{draw_type} ({outs} outs, {win_probability:.1%}). Pot odds {pot_odds:.1%} too expensive without implied odds.",
                        pot_odds=pot_odds,
                        equity_estimate=win_probability,
                        outs=outs,
                        confidence="medium"
                    )
            
            # Weak hands
            else:
                if pot_odds < 0.15 and num_opponents == 1:
                    return CoachAdvice(
                        "call",
                        f"Weak hand but getting great pot odds ({pot_odds:.1%}). Speculative call heads-up.",
                        pot_odds=pot_odds,
                        equity_estimate=strength,
                        hand_strength=made_hand or "Weak",
                        confidence="low"
                    )
                else:
                    return CoachAdvice(
                        "fold",
                        f"Weak holding ({made_hand or 'High card'}). Pot odds {pot_odds:.1%} don't justify call.",
                        pot_odds=pot_odds,
                        confidence="high"
                    )
    
    def _preflop_hand_strength(self, hand: List[str]) -> float:
        """Estimate preflop hand strength (0-1)"""
        if len(hand) != 2:
            return 0.0
        
        c1, c2 = hand
        r1, s1 = c1[0], c1[1]
        r2, s2 = c2[0], c2[1]
        
        i1 = RANKS.index(r1)
        i2 = RANKS.index(r2)
        
        # Base on high card
        base = max(i1, i2) / (len(RANKS) - 1)
        
        # Bonuses
        if r1 == r2:  # Pocket pair
            base += 0.35
        if s1 == s2:  # Suited
            base += 0.08
        if abs(i1 - i2) <= 3:  # Connected
            base += 0.05
        
        # Both cards high
        if i1 >= 8 and i2 >= 8:  # Both J or better
            base += 0.1
        
        return min(1.0, max(0.0, base))
    
    def _analyze_postflop_hand(self, hero_hand: List[str], 
                               community_cards: List[str]) -> Dict:
        """Analyze postflop hand strength"""
        
        all_cards = hero_hand + community_cards
        
        # Count ranks and suits
        rank_counts = {}
        suit_counts = {}
        ranks = []
        
        for card in all_cards:
            r, s = card[0], card[1]
            rank_counts[r] = rank_counts.get(r, 0) + 1
            suit_counts[s] = suit_counts.get(s, 0) + 1
            ranks.append(RANKS.index(r))
        
        ranks.sort(reverse=True)
        
        # Check for made hands
        max_same_rank = max(rank_counts.values()) if rank_counts else 0
        max_same_suit = max(suit_counts.values()) if suit_counts else 0
        
        # Simple hand detection
        made_hand = None
        strength = 0.0
        
        if max_same_rank == 4:
            made_hand = "Quads"
            strength = 0.95
        elif max_same_rank == 3:
            if len([v for v in rank_counts.values() if v >= 2]) >= 2:
                made_hand = "Full House"
                strength = 0.9
            else:
                made_hand = "Three of a Kind"
                strength = 0.65
        elif max_same_suit >= 5:
            made_hand = "Flush"
            strength = 0.8
        elif self._has_straight(ranks):
            made_hand = "Straight"
            strength = 0.75
        elif len([v for v in rank_counts.values() if v == 2]) >= 2:
            made_hand = "Two Pair"
            strength = 0.55
        elif max_same_rank == 2:
            made_hand = "Pair"
            # Strength depends on pair rank
            for r, count in rank_counts.items():
                if count == 2:
                    pair_rank = RANKS.index(r)
                    strength = 0.25 + (pair_rank / len(RANKS)) * 0.25
        else:
            made_hand = "High Card"
            strength = ranks[0] / len(RANKS) * 0.2
        
        # Check for draws
        draw_type = None
        outs = 0
        
        # Flush draw
        if max_same_suit == 4:
            draw_type = "Flush Draw"
            outs = 9
        
        # Straight draw (simplified)
        if not made_hand or made_hand in ["Pair", "High Card"]:
            if self._has_open_ended_straight_draw(ranks):
                if draw_type:
                    draw_type = "Combo Draw (Flush + Straight)"
                    outs = 15
                else:
                    draw_type = "Open-Ended Straight Draw"
                    outs = 8
            elif self._has_gutshot_draw(ranks):
                if draw_type:
                    draw_type = "Flush Draw + Gutshot"
                    outs = 12
                else:
                    draw_type = "Gutshot Straight Draw"
                    outs = 4
        
        return {
            "strength": strength,
            "made_hand": made_hand,
            "draw_type": draw_type,
            "outs": outs
        }
    
    def _has_straight(self, ranks: List[int]) -> bool:
        """Check if ranks contain a straight"""
        unique_ranks = sorted(set(ranks), reverse=True)
        
        # Check for wheel (A-2-3-4-5)
        if set([12, 0, 1, 2, 3]).issubset(set(unique_ranks)):
            return True
        
        # Check for regular straights
        for i in range(len(unique_ranks) - 4):
            if unique_ranks[i] - unique_ranks[i+4] == 4:
                return True
        
        return False
    
    def _has_open_ended_straight_draw(self, ranks: List[int]) -> bool:
        """Check for open-ended straight draw"""
        unique_ranks = sorted(set(ranks), reverse=True)
        
        for i in range(len(unique_ranks) - 3):
            if unique_ranks[i] - unique_ranks[i+3] == 3:
                return True
        
        return False
    
    def _has_gutshot_draw(self, ranks: List[int]) -> bool:
        """Check for gutshot straight draw (simplified)"""
        unique_ranks = sorted(set(ranks), reverse=True)
        
        # Very simplified - just check for 4-card sequences with one gap
        for i in range(len(unique_ranks) - 3):
            span = unique_ranks[i] - unique_ranks[i+3]
            if span == 4:  # e.g., 10-9-7-6 (missing 8)
                return True
        
        return False
    
    def _outs_to_probability(self, outs: int, cards_to_come: int) -> float:
        """Convert outs to win probability"""
        if cards_to_come == 2:
            # Flop to river (rule of 4)
            return min(1.0, outs * 4 / 100)
        elif cards_to_come == 1:
            # Turn to river (rule of 2)
            return min(1.0, outs * 2 / 100)
        return 0.0
    
    def _hand_to_code(self, card1: str, card2: str) -> str:
        """Convert two cards to hand code like 'AKs', 'TT', '72o'"""
        r1, s1 = card1[0], card1[1]
        r2, s2 = card2[0], card2[1]
        
        if r1 == r2:
            return r1 + r2
        
        # Sort by rank
        if RANKS.index(r1) > RANKS.index(r2):
            hi, lo = r1, r2
            s_hi, s_lo = s1, s2
        else:
            hi, lo = r2, r1
            s_hi, s_lo = s2, s1
        
        suited = (s_hi == s_lo)
        return hi + lo + ("s" if suited else "o")


# Convenience function for easy import
def get_poker_advice(hero_hand: List[str], community_cards: List[str],
                    pot: int, current_bet: int, hero_contribution: int,
                    hero_stack: int, position: str, street: str,
                    num_opponents: int) -> CoachAdvice:
    """
    Get poker coaching advice
    
    Example usage:
        advice = get_poker_advice(
            hero_hand=["Ah", "Kd"],
            community_cards=["Qh", "Jh", "Th"],
            pot=100,
            current_bet=50,
            hero_contribution=0,
            hero_stack=500,
            position="BTN",
            street="flop",
            num_opponents=2
        )
        print(advice.recommendation)  # "raise"
        print(advice.reasoning)  # Full explanation
    """
    coach = PokerCoach()
    return coach.get_advice(hero_hand, community_cards, pot, current_bet,
                           hero_contribution, hero_stack, position, street,
                           num_opponents)