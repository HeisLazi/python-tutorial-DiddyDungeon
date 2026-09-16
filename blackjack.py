import random


def deal_card():
    cards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]
    dealt_card = random.choice(cards)
    return dealt_card

def calculate_total_hand(items):
    return sum(items)

player_hand = []
dealer_hand = []

player_hand.append(deal_card())
player_hand.append(deal_card())

dealer_hand.append(deal_card())
dealer_hand.append(deal_card())

calculate_total_hand(player_hand)
calculate_total_hand(dealer_hand)

player_score = calculate_total_hand(player_hand)
dealer_score = calculate_total_hand(dealer_hand)

print(f"player was dealt {player_hand} in their hand with a score {calculate_total_hand(player_hand)}")
print(f"dealer was dealt {dealer_hand} in their hand with a score {calculate_total_hand(dealer_hand)}")
