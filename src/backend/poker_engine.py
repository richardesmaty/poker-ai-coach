from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
import random

# ---------- Cards & Deck ----------

RANKS = "23456789TJQKA"
SUITS = "shdc"  # spades, hearts, diamonds, clubs


def create_deck() -> List[str]:
    """Create and shuffle a standard 52-card deck."""
    deck = [r + s for r in RANKS for s in SUITS]
    random.shuffle(deck)
    return deck


# ---------- BOT PERSONALITIES ----------

@dataclass
class BotProfile:
    name: str
    looseness: float   # 0 = very tight, 1 = very loose
    aggression: float  # 0 = passive, 1 = maniac
    bluffiness: float  # 0 = never bluff, 1 = bluffs a lot


BOT_PROFILES: Dict[str, BotProfile] = {
    "Crusher Carl": BotProfile("Crusher Carl", looseness=0.25, aggression=0.65, bluffiness=0.15),
    "LAG Lucy": BotProfile("LAG Lucy", looseness=0.75, aggression=0.85, bluffiness=0.50),
    "Nit Neil": BotProfile("Nit Neil", looseness=0.15, aggression=0.30, bluffiness=0.05),
    "Reckless Rafa": BotProfile("Reckless Rafa", looseness=0.90, aggression=0.95, bluffiness=0.80),
    "Station Sam": BotProfile("Station Sam", looseness=0.80, aggression=0.25, bluffiness=0.10),
    "Balanced Ben": BotProfile("Balanced Ben", looseness=0.50, aggression=0.60, bluffiness=0.30),
    "Gambler Grace": BotProfile("Gambler Grace", looseness=0.80, aggression=0.70, bluffiness=0.60),
}


# ---------- Data Structures ----------

@dataclass
class Player:
    id: int
    name: str
    is_human: bool
    stack: int
    seat: int
    hole_cards: List[str] = field(default_factory=list)
    in_hand: bool = True
    has_folded: bool = False
    has_all_in: bool = False
    contribution_this_round: int = 0  # chips put in on this betting street
    total_contribution: int = 0      # chips put in this hand

    starting_stack: int = 1000
    mood: str = "neutral"  # "neutral" | "heater" | "tilt"

    @property
    def profile(self) -> Optional[BotProfile]:
        return BOT_PROFILES.get(self.name)

    def reset_for_new_hand(self):
        self.hole_cards = []
        self.in_hand = self.stack > 0
        self.has_folded = False
        self.has_all_in = False
        self.contribution_this_round = 0
        self.total_contribution = 0


@dataclass
class Action:
    player_id: int
    action_type: str  # "fold" | "check" | "call" | "bet" | "raise" | "all-in"
    amount: int       # amount put in NOW (not total)
    street: str       # "preflop" | "flop" | "turn" | "river"


@dataclass
class GameState:
    players: List[Player]
    small_blind_amount: int
    big_blind_amount: int

    deck: List[str] = field(default_factory=list)
    community_cards: List[str] = field(default_factory=list)
    pot: int = 0
    button_seat: int = 0
    current_bet: int = 0  # highest bet amount this street
    last_raiser_seat: Optional[int] = None
    betting_round: str = "preflop"  # preflop, flop, turn, river, finished
    action_history: List[Action] = field(default_factory=list)
    current_player_seat: Optional[int] = None

    def active_players(self) -> List[Player]:
        return [p for p in self.players if p.in_hand and not p.has_folded]

    def player_by_seat(self, seat: int) -> Player:
        for p in self.players:
            if p.seat == seat:
                return p
        raise ValueError(f"No player at seat {seat}")


# ---------- Poker Game Engine (web-friendly) ----------

class PokerGame:
    """
    Engine for 1 human vs up to 7 bots.
    No input() calls – everything is driven by the UI.
    """

    def __init__(self, player_names: List[str], starting_stack: int = 1000,
                 small_blind: int = 5, big_blind: int = 10):
        if not 2 <= len(player_names) <= 8:
            raise ValueError("Game supports 2 to 8 players.")

        seats = list(range(len(player_names)))
        random.shuffle(seats)

        players: List[Player] = []
        for i, name in enumerate(player_names):
            players.append(
                Player(
                    id=i,
                    name=name,
                    is_human=(name == "HUMAN"),
                    stack=starting_stack,
                    seat=seats[i],
                    starting_stack=starting_stack,
                )
            )

        self.state = GameState(
            players=players,
            small_blind_amount=small_blind,
            big_blind_amount=big_blind,
        )
        self.state.button_seat = random.choice(seats)

        self.last_event: str = "Game created."
        self.last_winner: Optional[str] = None

    # ----- Handy properties for UI -----

    @property
    def hero(self) -> Player:
        return next(p for p in self.state.players if p.is_human)

    def blind_seats(self) -> Tuple[int, int]:
        """
        Return (small_blind_seat, big_blind_seat) for display.
        """
        s = self.state
        sb_seat = self._next_occupied_seat(s.button_seat)
        bb_seat = self._next_occupied_seat(sb_seat)
        return sb_seat, bb_seat

    def total_chips(self) -> int:
        """
        Pot + all stacks – should stay constant over time.
        """
        return self.state.pot + sum(p.stack for p in self.state.players)

    # ----- Public API called from UI -----

    def start_new_hand(self):
        """Reset state and deal a new hand."""
        s = self.state
        for p in s.players:
            p.reset_for_new_hand()

        s.deck = create_deck()
        s.community_cards = []
        s.pot = 0
        s.current_bet = 0
        s.last_raiser_seat = None
        s.betting_round = "preflop"
        s.action_history = []
        self.last_winner = None

        # Move button
        self._advance_button()
        # Post blinds + deal
        self._post_blinds()
        self._deal_hole_cards()

        self.last_event = "New hand started."

    def run_street_with_human_choice(self, human_choice: str, human_amount: Optional[int] = None):
        """
        Run ONE betting street:
        - human_choice: 'check_call', 'bet_raise', or 'fold'
        - human_amount: desired bet/raise-to amount (total for this street)
        We loop around the table once (simple model), then either
        go to next street or finish the hand.
        """
        s = self.state

        if s.betting_round == "finished":
            self.last_event = "Hand already finished. Start a new hand."
            return

        street_before = s.betting_round

        # Reset street contributions (blinds are already in total_contribution/pot)
        self._reset_street_for_players()

        active_players = [p for p in s.players if p.in_hand and not p.has_folded]
        if len(active_players) <= 1:
            self._handle_showdown_or_win()
            s.betting_round = "finished"
            return

        active_seats = sorted({p.seat for p in active_players})
        if s.current_player_seat in active_seats:
            start_index = active_seats.index(s.current_player_seat)
        else:
            start_index = 0
        ordered_seats = active_seats[start_index:] + active_seats[:start_index]

        for seat in ordered_seats:
            player = s.player_by_seat(seat)
            if not player.in_hand or player.has_folded or player.has_all_in:
                continue

            if player.is_human:
                action_type, amount = self._human_choice_to_action(player, human_choice, human_amount)
            else:
                action_type, amount = self._bot_decision(player)

            self._apply_action(player, action_type, amount)

        active_after = s.active_players()
        if len(active_after) <= 1 or s.betting_round == "river":
            self._handle_showdown_or_win()
            s.betting_round = "finished"
        else:
            if s.betting_round == "preflop":
                self._deal_flop()
                s.betting_round = "flop"
            elif s.betting_round == "flop":
                self._deal_turn()
                s.betting_round = "turn"
            elif s.betting_round == "turn":
                self._deal_river()
                s.betting_round = "river"

        self.last_event = f"On {street_before.upper()}, you chose {human_choice.replace('_', '/').upper()}."

    # ----- Internal mechanics -----

    def _advance_button(self):
        s = self.state
        seats = [p.seat for p in s.players]
        min_seat, max_seat = min(seats), max(seats)

        next_seat = s.button_seat
        while True:
            next_seat += 1
            if next_seat > max_seat:
                next_seat = min_seat
            if any(p.seat == next_seat and p.stack > 0 for p in s.players):
                s.button_seat = next_seat
                break

    def _post_blinds(self):
        s = self.state
        sb_seat = self._next_occupied_seat(s.button_seat)
        bb_seat = self._next_occupied_seat(sb_seat)

        sb_player = s.player_by_seat(sb_seat)
        bb_player = s.player_by_seat(bb_seat)

        sb_amount = min(sb_player.stack, s.small_blind_amount)
        bb_amount = min(bb_player.stack, s.big_blind_amount)

        self._take_bet(sb_player, sb_amount)
        self._record_action(sb_player, "bet", sb_amount, "preflop")

        self._take_bet(bb_player, bb_amount)
        self._record_action(bb_player, "bet", bb_amount, "preflop")

        # Blinds sit in pot & total_contribution; per-street contributions
        # will be reset before betting.
        s.current_bet = s.big_blind_amount
        s.last_raiser_seat = bb_seat

    def _deal_hole_cards(self):
        s = self.state
        for _ in range(2):
            for p in s.players:
                if p.stack > 0:
                    card = s.deck.pop()
                    p.hole_cards.append(card)

    def _deal_flop(self):
        s = self.state
        s.deck.pop()
        s.community_cards.extend([s.deck.pop(), s.deck.pop(), s.deck.pop()])

    def _deal_turn(self):
        s = self.state
        s.deck.pop()
        s.community_cards.append(s.deck.pop())

    def _deal_river(self):
        s = self.state
        s.deck.pop()
        s.community_cards.append(s.deck.pop())

    def _first_to_act_preflop(self) -> int:
        s = self.state
        bb_seat = self._find_big_blind_seat()
        return self._next_occupied_seat(bb_seat)

    def _first_to_act_postflop(self) -> int:
        s = self.state
        return self._next_occupied_seat(s.button_seat)

    def _reset_street_for_players(self):
        s = self.state
        for p in s.players:
            p.contribution_this_round = 0
        s.current_bet = 0
        s.last_raiser_seat = None

        if s.betting_round == "preflop":
            s.current_player_seat = self._first_to_act_preflop()
        else:
            s.current_player_seat = self._first_to_act_postflop()

    def _apply_action(self, player: Player, action_type: str, amount: int):
        s = self.state

        if action_type == "fold":
            player.has_folded = True
            player.in_hand = False
            self._record_action(player, "fold", 0, s.betting_round)
            return

        if action_type == "check":
            self._record_action(player, "check", 0, s.betting_round)
            return

        if action_type in ("call", "bet", "raise", "all-in"):
            to_put_in = min(amount, player.stack)
            self._take_bet(player, to_put_in)
            self._record_action(player, action_type, to_put_in, s.betting_round)

            if action_type in ("bet", "raise", "all-in"):
                s.current_bet = max(s.current_bet, player.contribution_this_round)
                s.last_raiser_seat = player.seat

    def _take_bet(self, player: Player, amount: int):
        s = self.state
        player.stack -= amount
        player.contribution_this_round += amount
        player.total_contribution += amount
        s.pot += amount
        if player.stack == 0:
            player.has_all_in = True

    def _record_action(self, player: Player, action_type: str, amount: int, street: str):
        self.state.action_history.append(
            Action(
                player_id=player.id,
                action_type=action_type,
                amount=amount,
                street=street,
            )
        )

    def _next_occupied_seat(self, seat: int) -> int:
        s = self.state
        active_seats = sorted({p.seat for p in s.players if p.in_hand and not p.has_folded})
        if not active_seats:
            raise RuntimeError("No active players remaining.")
        if seat not in active_seats:
            return active_seats[0]
        idx = active_seats.index(seat)
        next_idx = (idx + 1) % len(active_seats)
        return active_seats[next_idx]

    def _find_big_blind_seat(self) -> int:
        s = self.state
        sb_seat = self._next_occupied_seat(s.button_seat)
        bb_seat = self._next_occupied_seat(sb_seat)
        return bb_seat

    def _handle_showdown_or_win(self):
        s = self.state
        active = s.active_players()
        if len(active) == 0:
            self.last_winner = None
            return
        if len(active) == 1:
            winner = active[0]
            winner.stack += s.pot
            s.pot = 0
            self.last_winner = winner.name
            return

        # TODO: plug in real hand evaluation.
        winner = random.choice(active)
        winner.stack += s.pot
        s.pot = 0
        self.last_winner = winner.name

    # ---------- Hand strength + decisions ----------

    def _hand_strength(self, player: Player) -> float:
        if len(player.hole_cards) < 2:
            return 0.0
        c1, c2 = player.hole_cards
        r1, s1 = c1[0], c1[1]
        r2, s2 = c2[0], c2[1]

        i1 = RANKS.index(r1)
        i2 = RANKS.index(r2)
        base = max(i1, i2) / (len(RANKS) - 1)
        if r1 == r2:
            base += 0.4
        if s1 == s2:
            base += 0.1
        if abs(i1 - i2) == 1:
            base += 0.05
        return max(0.0, min(1.0, base))

    def _human_choice_to_action(self, player: Player, choice: str,
                                human_amount: Optional[int]) -> Tuple[str, int]:
        s = self.state
        to_call = max(0, s.current_bet - player.contribution_this_round)
        can_check = (to_call == 0)

        if choice == "fold":
            return "fold", 0

        if choice == "check_call":
            if can_check:
                return "check", 0
            return "call", min(to_call, player.stack)

        if choice == "bet_raise":
            # human_amount is interpreted as "total contribution this street"
            target_total = human_amount
            if target_total is None:
                if can_check:
                    target_total = max(s.big_blind_amount * 2, int(player.stack * 0.25))
                else:
                    target_total = max(
                        s.current_bet * 2,
                        s.current_bet + s.big_blind_amount,
                    ) + player.contribution_this_round

            max_total = player.contribution_this_round + player.stack
            target_total = max(s.big_blind_amount, min(target_total, max_total))

            if can_check:
                amount = target_total
                return "bet", amount

            amount = target_total - player.contribution_this_round
            if amount <= to_call:
                return "call", min(to_call, player.stack)
            return "raise", amount

        return "check", 0

    def _bot_decision(self, player: Player) -> Tuple[str, int]:
        s = self.state
        profile = player.profile or BotProfile("Default", 0.4, 0.5, 0.2)

        ratio = player.stack / player.starting_stack if player.starting_stack > 0 else 1.0
        if ratio >= 1.5:
            player.mood = "heater"
        elif ratio <= 0.7:
            player.mood = "tilt"
        else:
            player.mood = "neutral"

        looseness = profile.looseness
        aggression = profile.aggression
        bluffiness = profile.bluffiness

        if player.mood == "heater":
            looseness += 0.1
            aggression += 0.1
        elif player.mood == "tilt":
            if profile.aggression > 0.5:
                aggression += 0.1
            else:
                looseness -= 0.1

        looseness = max(0.0, min(1.0, looseness))
        aggression = max(0.0, min(1.0, aggression))

        can_check = (s.current_bet == player.contribution_this_round)
        to_call = max(0, s.current_bet - player.contribution_this_round)
        strength = self._hand_strength(player)
        desire = strength * 0.7 + looseness * 0.3

        if player.stack <= 0:
            return "check", 0

        if can_check:
            if desire < 0.2 and random.random() > looseness:
                return "check", 0
            bet_tendency = aggression * 0.6 + strength * 0.4
            if random.random() < bet_tendency:
                base = max(s.big_blind_amount, int((s.pot + s.big_blind_amount) * 0.6))
                bet_size = min(base, int(player.stack * 0.6))
                bet_size = max(s.big_blind_amount, bet_size)
                return "bet", bet_size
            return "check", 0

        if to_call <= 0:
            return "check", 0

        pot_odds = to_call / (s.pot + to_call) if (s.pot + to_call) > 0 else 0.0

        if desire + 0.1 < pot_odds and random.random() > looseness:
            return "fold", 0

        raise_tendency = aggression * (strength + bluffiness) / 2.0
        if random.random() < raise_tendency:
            mult = random.uniform(2.0, 4.0)
            raise_size = int(to_call * mult)
            raise_size = min(raise_size, player.stack)
            if raise_size <= to_call:
                return "call", min(to_call, player.stack)
            return "raise", raise_size
        return "call", min(to_call, player.stack)
