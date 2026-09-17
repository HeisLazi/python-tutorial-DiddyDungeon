import random

cards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]


def deal_card():
    return random.choice(cards)


def calculate_score(hand):
    return sum(hand)


player_hand = [deal_card(), deal_card()]
dealer_hand = [deal_card(), deal_card()]

print(f"You got: {player_hand} lmao, ur score is: {calculate_score(player_hand)}")
print(f"My first card is: {dealer_hand[0]}")

d_score = calculate_score(dealer_hand)
p_score = calculate_score(player_hand)

player_turn = True
while player_turn:
    choice = input(f"\nwhat do yu want to do BOY (hit / stand): ").strip().lower()
    if choice == "hit":
        player_hand.append(deal_card())
        p_score = calculate_score(player_hand)
        print(f"You ahh got {p_score} LMAOOO")

        if p_score > 21:
            print("I JUST BUSTED ALL OVER YOOOOOUUUUUU")
            player_turn = False
        elif p_score == 21:
            print("u gotta be kavango or smth??? i refuse to believe u beat me")
            player_turn = False

    elif choice == "stand":
        while d_score < 17:
            dealer_hand.append(deal_card())
            d_score = calculate_score(dealer_hand)
            print(f"rah my ahh got {d_score}")

        if d_score > 21 or p_score > d_score:
            print("aint no way this nigga gotta be cheating run ts back!" )
            player_turn = False
        elif p_score == d_score:
            print("Push / Standoff!")
        else:
            print("I won lmaooooooo!")
        player_turn = False
    else:
        print("Hella man i said hit or stand mxm!")
