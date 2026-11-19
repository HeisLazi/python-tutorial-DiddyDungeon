"""Server-authored duel material. Hidden checks never enter a player view."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DuelChallenge:
    id: str
    title: str
    prompt: str
    starter: str
    baseline: str
    checks: tuple[str, ...]
    duration_seconds: int = 180
    raid_attack_type: str = 'single'
    # 'choice' rounds are graded by the service from `answer`; 'code' rounds by the worker.
    kind: str = 'code'
    options: tuple[str, ...] = ()
    answer: int = -1  # private: never part of a player view
    snippet: str = ''  # code shown above a choice question (bug hunts, predict-the-output)
    bonus_after: bool = False
    # False: this step stands alone, so its starter is always loaded fresh.
    builds_on_previous: bool = True


CHAINS = {
    'potion': (
        DuelChallenge('potion-afford', 'Can you afford it?', 'Write can_buy(balance, price). Return True if the balance covers the price; otherwise return False.', '',
            'def can_buy(balance, price):\n    return balance >= price\n',
            ('can_buy(10, 4) is True', 'can_buy(4, 4) is True', 'can_buy(3, 4) is False', 'can_buy(0, 1) is False'), bonus_after=True),
        DuelChallenge('potion-purchase', 'Make the purchase', 'Add buy_potion(balance, price). Use can_buy to return the balance after a valid purchase, or the unchanged balance when it cannot be afforded.', '',
            'def can_buy(balance, price):\n    return balance >= price\n\ndef buy_potion(balance, price):\n    if can_buy(balance, price):\n        return balance - price\n    return balance\n',
            ('buy_potion(10, 4) == 6', 'buy_potion(4, 4) == 0', 'buy_potion(3, 4) == 3', 'buy_potion(19, 0) == 19')),
        DuelChallenge('potion-negative', 'Close the loophole', 'Update buy_potion so a negative price leaves the balance unchanged. Normal purchases must still work.', '', '',
            ('buy_potion(10, -4) == 10', 'buy_potion(10, 4) == 6', 'buy_potion(3, 4) == 3', 'buy_potion(0, -100) == 0'),
            raid_attack_type='aoe'),
    ),
    'chest': (
        DuelChallenge('chest-fix', 'Find the bug', 'Fix chest_reward(gold, reward) so it adds the reward to the current total.',
            'def chest_reward(gold, reward):\n    return gold - reward\n',
            'def chest_reward(gold, reward):\n    return gold + reward\n',
            ('chest_reward(10, 5) == 15', 'chest_reward(0, 0) == 0', 'chest_reward(100, 2) == 102'), bonus_after=True),
        DuelChallenge('chest-locked', 'Locked chest', 'Add an opened parameter: chest_reward(gold, reward, opened). A closed chest leaves gold unchanged; an open chest adds the reward.', '',
            'def chest_reward(gold, reward, opened):\n    if opened:\n        return gold + reward\n    return gold\n',
            ('chest_reward(10, 5, False) == 10', 'chest_reward(10, 5, True) == 15', 'chest_reward(0, 3, True) == 3')),
        DuelChallenge('chest-collect', 'Collect the chests', 'Add collect_chests(gold, chests). Each entry is a (reward, opened) pair. Use chest_reward to calculate the final gold.', '',
            'def chest_reward(gold, reward, opened):\n    if opened:\n        return gold + reward\n    return gold\n\ndef collect_chests(gold, chests):\n    for reward, opened in chests:\n        gold = chest_reward(gold, reward, opened)\n    return gold\n',
            ('collect_chests(10, [(5, True), (7, False), (3, True)]) == 18', 'collect_chests(4, []) == 4', 'collect_chests(0, [(7, False)]) == 0')),
        DuelChallenge('chest-refund', 'Protect the refund boundary', 'Add refund_chest(gold, refund). A valid refund subtracts from the total without making it negative; a zero or negative refund leaves the total unchanged.', '', '',
            ('refund_chest(10, 4) == 6', 'refund_chest(3, 5) == 0', 'refund_chest(0, 1) == 0', 'refund_chest(10, -4) == 10')),
    ),
}


def _choice(id, title, prompt, options, answer, snippet='', seconds=40):
    return DuelChallenge(id, title, prompt, '', '', (), seconds, kind='choice', options=tuple(options), answer=answer, snippet=snippet)


def _code(id, title, prompt, starter, baseline, seconds, builds_on_previous=True):
    return DuelChallenge(id, title, prompt, starter, baseline, (), seconds, builds_on_previous=builds_on_previous)


# Difficulty tiers. Hidden checks for the code rounds live in worker/cases.py.
CHAINS['basic'] = (
    _choice('basic-variable', 'Variables', 'True or false: after this line runs, Python has a variable called lives that holds the number 3.',
            ['True', 'False'], 0, snippet='lives = 3'),
    _code('basic-bump', 'Change a variable', 'Write bump(score). Create a variable bonus equal to 10, add it to score, and return the result.',
          'def bump(score):\n    # make a variable called bonus, then add it\n    ', 'def bump(score):\n    bonus = 10\n    return score + bonus\n', 120, False),
    _choice('basic-append', 'Lists', "Which line adds 'kiwi' to the end of the list?",
            ["fruits.add('kiwi')", "fruits + 'kiwi'", "fruits.append('kiwi')"], 2, snippet="fruits = ['apple', 'pear']"),
    _code('basic-third', 'Pick from a list', 'Write third(items). It receives a list and returns the third item. Remember that Python counts from 0.',
          'def third(items):\n    ', 'def third(items):\n    return items[2]\n', 120, False),
    _choice('basic-bug', 'Bug hunt', 'Python reports an error when this runs. Why?',
            ['Python cannot print text', 'name and Name are different variables, and Name was never created', 'A variable cannot hold text'], 1,
            snippet='name = "Ada"\nprint(Name)'),
)
CHAINS['normal'] = (
    _code('normal-append', 'Add to a list', 'Write add_item(items, item). Append item to the list, then return how many items the list now holds.',
          'def add_item(items, item):\n    ', 'def add_item(items, item):\n    items.append(item)\n    return len(items)\n', 120, False),
    _choice('normal-bug-range', 'Bug hunt', 'This loop should print every item once. What goes wrong?',
            ['Nothing, it prints a, b, c', 'It raises an IndexError on the last pass because range() goes one step too far', 'It prints c, b, a'], 1,
            snippet="items = ['a', 'b', 'c']\nfor i in range(len(items) + 1):\n    print(items[i])"),
    _code('normal-tally', 'Count with a dictionary', 'Write tally(votes, name). Count how many times name appears in the votes list using a dictionary, and return that count (0 if it never appears).',
          'def tally(votes, name):\n    counts = {}\n    ', 'def tally(votes, name):\n    counts = {}\n    for vote in votes:\n        counts[vote] = counts.get(vote, 0) + 1\n    return counts.get(name, 0)\n', 150, False),
    _choice('normal-object', 'Objects', 'This class is defined. Which line creates a Wallet object?',
            ['Wallet.new()', 'new Wallet()', 'Wallet()'], 2, snippet='class Wallet:\n    def __init__(self):\n        self.balance = 0'),
    _code('normal-wallet', 'A small class', 'Create class Wallet with __init__(self, balance) and spend(self, amount). spend subtracts amount only when the balance covers it and returns True; otherwise it changes nothing and returns False. Then write wallet_after(balance, spends): make a Wallet, spend each amount in order, and return the final balance.',
          'class Wallet:\n    ', 'class Wallet:\n    def __init__(self, balance):\n        self.balance = balance\n\n    def spend(self, amount):\n        if amount <= self.balance:\n            self.balance -= amount\n            return True\n        return False\n\ndef wallet_after(balance, spends):\n    wallet = Wallet(balance)\n    for amount in spends:\n        wallet.spend(amount)\n    return wallet.balance\n', 240, False),
)
_POKER_RANK = ("RANKS = '23456789TJQKA'\n\n"
               "def card_rank(card):\n    return RANKS.index(card[0]) + 2\n")
_POKER_SCORE = (_POKER_RANK + "\ndef score_hand(hand):\n    counts = {}\n    for card in hand:\n        rank = card_rank(card)\n        counts[rank] = counts.get(rank, 0) + 1\n"
                "    shape = sorted(counts.values(), reverse=True)\n"
                "    if shape == [4, 1]:\n        return 'four of a kind'\n"
                "    if shape == [3, 2]:\n        return 'full house'\n"
                "    if shape == [3, 1, 1]:\n        return 'three of a kind'\n"
                "    if shape == [2, 2, 1]:\n        return 'two pair'\n"
                "    if shape == [2, 1, 1, 1]:\n        return 'pair'\n"
                "    return 'high card'\n")
_POKER_WINNER = (_POKER_SCORE + "\nORDER = ['high card', 'pair', 'two pair', 'three of a kind', 'full house', 'four of a kind']\n\n"
                 "def winner(hand_a, hand_b):\n    a, b = ORDER.index(score_hand(hand_a)), ORDER.index(score_hand(hand_b))\n"
                 "    if a != b:\n        return 'A' if a > b else 'B'\n"
                 "    top_a = max(card_rank(c) for c in hand_a)\n    top_b = max(card_rank(c) for c in hand_b)\n"
                 "    if top_a == top_b:\n        return 'tie'\n    return 'A' if top_a > top_b else 'B'\n")
_POKER_ROUND = (_POKER_WINNER + "\ndef play_round(hands):\n    best = 0\n    for i in range(1, len(hands)):\n        if winner(hands[i], hands[best]) == 'A':\n            best = i\n    return best\n")
CHAINS['advanced'] = (
    _code('advanced-rank', 'Mini poker · card ranks', "Cards are two-character strings such as 'Kh': a rank character, then a suit. Write card_rank(card) returning the rank as a number: '2'-'9' are 2-9, 'T' is 10, 'J' 11, 'Q' 12, 'K' 13 and 'A' 14.",
          'def card_rank(card):\n    ', _POKER_RANK, 150, False),
    _code('advanced-score', 'Mini poker · score a hand', "Add score_hand(hand) for a list of five cards. Return the best label that applies: 'four of a kind', 'full house', 'three of a kind', 'two pair', 'pair', otherwise 'high card'. Ignore straights and flushes. Reuse card_rank.",
          '', _POKER_SCORE, 240),
    _code('advanced-winner', 'Mini poker · who wins?', "Add winner(hand_a, hand_b). The stronger label wins (ranked from high card up to four of a kind). With equal labels, compare only each hand's single highest card (ignore pairs and kickers); the higher card wins, and if they match, return 'tie'. Return 'A', 'B', or 'tie'. Reuse score_hand.",
          '', _POKER_WINNER, 240),
    _code('advanced-round', 'Mini poker · play a round', 'Add play_round(hands). Given a list of hands, return the index of the winning hand. If hands tie, the earliest one wins. Reuse winner.',
          '', _POKER_ROUND, 210),
    _choice('advanced-interview', 'Interview', 'An interviewer reads your score_hand. You counted each rank with a dictionary as you walked the hand once. They ask why not call hand.count() for every card. Which answer is strongest?',
            ['Dictionaries are the only way to count things in Python.',
             'One pass with a dictionary does the counting once; repeated count() calls rescan the whole hand for every card and slow down as hands grow.',
             'count() does not work on lists of strings.'], 1, seconds=60),
)


# Fun modes: short, sharp, and separate from the difficulty ladder.
CHAINS['bughunt'] = (
    _choice('bughunt-total', 'Spot the bug', 'This should print 6, the sum of the list. Which line is the bug?',
            ['total = 0', 'total = n  (it replaces the total on every pass)', 'print(total)'], 1,
            snippet='total = 0\nfor n in [1, 2, 3]:\n    total = n\nprint(total)'),
    _choice('bughunt-compare', 'Spot the bug', 'Python refuses to run this function. Why?',
            ['n % 2 is not allowed', 'The function needs a print', 'A single = assigns; comparing values needs =='], 2,
            snippet='def is_even(n):\n    return n % 2 = 0'),
    _choice('bughunt-index', 'Spot the bug', 'What happens when this runs?',
            ['IndexError: the list only has positions 0 and 1', 'It prints Bo', 'It prints None'], 0,
            snippet="names = ['Ada', 'Bo']\nprint(names[2])"),
    _code('bughunt-last', 'Fix the bug', 'last_item(items) should return the final item of a list, but it crashes. Fix it.',
          'def last_item(items):\n    return items[len(items)]\n', 'def last_item(items):\n    return items[-1]\n', 120, False),
    _code('bughunt-evens', 'Fix the bug', 'count_evens(numbers) should count the even numbers, but it counts the wrong ones. Fix it.',
          'def count_evens(numbers):\n    count = 0\n    for n in numbers:\n        if n % 2 == 1:\n            count += 1\n    return count\n',
          'def count_evens(numbers):\n    count = 0\n    for n in numbers:\n        if n % 2 == 0:\n            count += 1\n    return count\n', 150, False),
)
CHAINS['oracle'] = (
    _choice('oracle-double', 'What prints?', 'What does this print?', ['4', '8', 'x * 2'], 1, snippet='x = 4\nx = x * 2\nprint(x)', seconds=30),
    _choice('oracle-repeat', 'What prints?', 'What does this print?', ['ababab', 'ab3', 'It raises an error'], 0, snippet='print("ab" * 3)', seconds=30),
    _choice('oracle-sort', 'What prints?', 'What does this print?', ['3', '2', '1'], 2, snippet='nums = [3, 1, 2]\nnums.sort()\nprint(nums[0])', seconds=30),
    _choice('oracle-dict', 'What prints?', 'What does this print?', ['1', '2', 'It raises an error'], 1, snippet="d = {'a': 1}\nd['b'] = 2\nprint(len(d))", seconds=30),
    _choice('oracle-branch', 'What prints?', 'What does this print?', ['big', 'small', 'None'], 1,
            snippet='def f(n):\n    if n > 2:\n        return "big"\n    return "small"\nprint(f(2))', seconds=30),
)


def public_challenge(challenge: DuelChallenge, previous_passed: bool | None) -> dict:
    # An explicit allow-list: the answer key and hidden checks never leave the service.
    view = {'id': challenge.id, 'title': challenge.title, 'prompt': challenge.prompt, 'kind': challenge.kind,
            'duration_seconds': challenge.duration_seconds}
    if challenge.kind == 'choice':
        view['options'] = list(challenge.options)
        view['snippet'] = challenge.snippet
        view['starter'] = ''
    else:
        # Baselines repair only a missed *previous* step; never reveal the current answer.
        standalone = not challenge.builds_on_previous
        view['starter'] = challenge.starter if standalone or previous_passed is None else ''
        view['fresh'] = standalone
    return view
