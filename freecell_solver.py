import os
import sys
import time
from itertools import repeat, chain
from enum import Enum
from random import shuffle, sample
from io import StringIO


def clear_screen():
    # os.system('clear')
    # print('\x1b[2J\x1b[3J')
    print("\033[H\033[J")


class Suit(Enum):
    HEARTS = 'H'
    CLUBS = 'C'
    SPADES = 'S'
    DIAMONDS = 'D'


class Value(Enum):
    ACE = 'A'
    TWO = '2'
    THREE = '3'
    FOUR = '4'
    FIVE = '5'
    SIX = '6'
    SEVEN = '7'
    EIGHT = '8'
    NINE = '9'
    TEN = 'T'
    JACK = 'J'
    QUEEN = 'Q'
    KING = 'K'


class Color(Enum):
    RED = 'R'
    BLACK = 'B'


suit_color = {
    Suit.HEARTS: Color.RED,
    Suit.DIAMONDS: Color.RED,
    Suit.CLUBS: Color.BLACK,
    Suit.SPADES: Color.BLACK
}

value_order = {
    Value.ACE: 1,
    Value.TWO: 2,
    Value.THREE: 3,
    Value.FOUR: 4,
    Value.FIVE: 5,
    Value.SIX: 6,
    Value.SEVEN: 7,
    Value.EIGHT: 8,
    Value.NINE: 9,
    Value.TEN: 10,
    Value.JACK: 11,
    Value.QUEEN: 12,
    Value.KING: 13,
}


def parse_card_name(name):
    value_str = name[:-1]
    suit_str = name[-1]
    value = Value(value_str)
    suit = Suit(suit_str)
    return suit, value


class Card(object):
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    @classmethod
    def from_name(cls, name):
        value, suit = parse_card_name(name)
        return cls(value, suit)

    @property
    def color(self):
        return suit_color[self.suit.value]

    def __str__(self):
        return f"{self.value.value}{self.suit.value}"

    def __repr__(self):
        return f"Card(suit={self.suit}, value={self.value})"


class Deck(object):
    def __init__(self):
        self.cards = list(Deck.generate())
        shuffle(self.cards)

    @staticmethod
    def generate():
        for suit in Suit:
            for value in Value:
                yield Card(suit, value)


class Stack(object):
    def __init__(self):
        self.cards = []

    @property
    def top_card(self):
        return self.cards[-1] if self.cards else None

    def card_at(self, index):
        return self.cards[index] if index < len(self.cards) else None

    def pop_card(self):
        return self.cards.pop()

    def push_card(self, card):
        self.cards.append(card)


class FreeCell(Stack):
    def can_accept_card(self, card):
        return not self.cards


class HomeStack(Stack):
    def can_accept_card(self, card):
        return ((not self.cards and card.value == Value.ACE) or
                (self.cards and self.top_card.suit == card.suit and
                 value_order[self.top_card.value] == value_order[card.value] - 1))


class SourceStack(Stack):
    def can_accept_card(self, card):
        return (not self.cards or
                (suit_color[self.top_card.suit] != suit_color[card.suit] and
                 value_order[self.top_card.value] == value_order[card.value] + 1))


class Move:
    def __init__(self, from_stack, to_stack):
        self.from_stack = from_stack
        self.to_stack = to_stack

        card_being_moved = self.from_stack.top_card
        destination = self.to_stack.top_card
        if destination is None:
            # destination = '%s@%x' % (self.to_stack.__class__.__name__, id(self.to_stack))
            destination = self.to_stack.__class__.__name__
        self.description = f"{card_being_moved}>{destination}"

    def __str__(self):
        return self.description

    def __repr__(self):
        return self.description


class Board(object):
    def __init__(self):
        self.free_cells = [FreeCell() for _ in range(4)]
        self.home_stacks = [HomeStack() for _ in range(4)]
        self.source_stacks = [SourceStack() for _ in range(8)]
        self.move_history = []

    def all_valid_moves(self):
        for from_stack in chain(self.free_cells, self.source_stacks):
            top_card = from_stack.top_card
            if top_card is None:
                continue
            if isinstance(from_stack, FreeCell):
                to_stacks = chain(self.home_stacks, self.source_stacks)
            else:
                to_stacks = chain(self.home_stacks, self.source_stacks, self.free_cells)
            for to_stack in to_stacks:
                if from_stack is to_stack:
                    continue
                if to_stack.can_accept_card(top_card):
                    yield Move(from_stack, to_stack)

    def make_move(self, move):
        move.to_stack.push_card(move.from_stack.pop_card())
        self.move_history.append(move)

    def undo_last_move(self):
        move = self.move_history.pop()
        move.from_stack.push_card(move.to_stack.pop_card())

    @property
    def number_of_moves(self):
        return len(self.move_history)

    @property
    def is_solved(self):
        return (all(hs.top_card and hs.top_card.value == Value.KING for hs in self.home_stacks)
                and all(fs.top_card is None for fs in self.free_cells)
                and all(ss.top_card is None for ss in self.source_stacks))

    def __hash__(self):  # make order of freecells and homecells unimportant
        with StringIO() as out:
            save_game(out, self)
            out.seek(0)
            text = out.read()
            return hash(text)


def load_game(f):
    board = Board()
    for line in f:
        cards = line.split()
        for n, card in enumerate(cards):
            board.source_stacks[n % 8].cards.append(Card.from_name(card))
    return board


def save_game(f, board):
    def cards_to_line(cards):
        return " ".join("  " if card is None else str(card) for card in cards)
    fc_line = cards_to_line(s.top_card for s in board.free_cells)
    home_line = cards_to_line(s.top_card for s in board.home_stacks)
    print(fc_line + "|" + home_line, file=f)
    num_rows = max(len(stk.cards) for stk in board.source_stacks)
    for row in range(num_rows):
        print(cards_to_line(stack.card_at(row) for stack in board.source_stacks), file=f)


def print_game(board):
    save_game(sys.stdout, board)


def random_search(board):
    for attempt in range(1, 101):
        # Make up to 100 random moves, break out if no move possible or solved
        solved = False
        for move_number in range(1, 101):
            moves = list(board.all_valid_moves())
            if len(moves) == 0:
                print('No moves possible!')
                break
            random_move = sample(moves, 1)[0]
            print(f'Making move #{move_number}:', random_move)
            board.make_move(random_move)
            print_game(board)
            solved = board.is_solved
            if solved:
                print('Game is solved yippee! (after', attempt, 'attempts')
                break

        print('Move history:')
        print(" ".join(board.move_history))

        if solved:
            break
        else:
            while board.number_of_moves > 0:
                print(f'Undoing move #{board.number_of_moves}:', board.move_history[-1])
                board.undo_last_move()
                print_game(board)


def sort_moves_by_priority(moves):
    def key_fn(move):
        if isinstance(move.to_stack, HomeStack):
            return 0
        elif isinstance(move.to_stack, SourceStack):
            return 1
        elif isinstance(move.to_stack, FreeCell):
            return 2
    return sorted(moves, key=key_fn)


def filter_redundant_moves(moves):
    equivalency_set = set()
    for move in moves:
        equivalency_key = "|".join([
            move.from_stack.__class__.__name__,
            str(move.from_stack.top_card),
            move.to_stack.__class__.__name__,
            str(move.to_stack.top_card)])

        if equivalency_key not in equivalency_set:
            equivalency_set.add(equivalency_key)
            yield move


boards_seen = dict()

lookback_distance_histogram = dict()

next_print = 0


def full_recursive_search(board, depth_remaining=100):
    if depth_remaining < 0:
        return

    global next_print
    global max_lookback_distance
    now = time.time()
    if next_print == 0 or now >= next_print:
        next_print = now + 1
        clear_screen()
        print('Depth remaining:', depth_remaining)
        print('Number of boards seen:', len(boards_seen))
        #print('Max lookback distance:', max_lookback_distance)
        print_game(board)
        print(" ".join(map(str, board.move_history)))
        print("Lookback distance histogram:", sorted(list(lookback_distance_histogram.items())))

    moves = sort_moves_by_priority(list(board.all_valid_moves()))
    moves = list(filter_redundant_moves(moves))  # grab whole list just for debugging
    for move in moves:
        # print_game(board)
        board.make_move(move)
        # print(move)
        # print_game(board)
        if board.is_solved:
            return
        hash_value = hash(board)
        board_seen_at = boards_seen.get(hash_value)
        if board_seen_at is None:
            boards_seen[hash_value] = len(boards_seen)
            full_recursive_search(board, depth_remaining - 1)
            if board.is_solved:
                return
        else:
            lookback_distance = len(boards_seen) - board_seen_at
            #max_lookback_distance = max(lookback_distance, max_lookback_distance)
            lookback_distance_histogram[lookback_distance] = lookback_distance_histogram.get(lookback_distance, 0) + 1
        board.undo_last_move()


test_game = """
6C 6H TH 6S JD 9H QH 5H
KC 5D AD JC 8S TS 8D 2H
4D QD 7H KD 3S 4S 2D JS
JH 9C TC 8H 5S AH 6D 2S
KH 7C QC AS 7D TD 2C 5C
3H 9S 4C 7S KS QS 9D AC
3D 3C 8C 4H
"""


def main():
    deck = Deck()
    print(deck.cards)

    input = StringIO(test_game)
    board = load_game(input)
    print_game(board)

    moves = list(board.all_valid_moves())
    for move in moves:
        if not isinstance(move.to_stack, FreeCell):
            print(move)

    random_move = sample(moves, 1)[0]
    print("Making move", random_move)
    board.make_move(random_move)
    print_game(board)
    print("Undoing move", random_move)
    board.undo_last_move()
    print_game(board)

    # random_search(board)

    full_recursive_search(board)

    if board.is_solved:
        print('Board is solved and here are the moves:')
        # print(board.move_history)
        print(" ".join(map(str, board.move_history)))
        # print(" ".join(board.move_history))


if __name__ == '__main__':
    main()
