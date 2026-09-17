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
    if choice == "hit" and p_score < 21:
        player_hand.append(deal_card())
        dealer_hand.append(deal_card())
        print(
            f"\nEKSE my outtie you got a {player_hand} in your hand now its {p_score} btw \ncause ik you cant do maths lol. \n \njrr i got a {dealer_hand} \nyoh i have {d_score}"
        )
        if p_score == d_score and p_score < 21:
            print(f"\nwe inna stand off rn who gon hit first tehehe")
            player_turn = False
        elif p_score > 21:
            print(f"\n{p_score} lamooooo WE just busted all over you")
            player_turn = False

    elif choice == "stand":
        if p_score > d_score and d_score > 18:
            dealer_hand.append(deal_card)

        elif p_score > d_score and d_score > 21:
            print("\naint no way u won ts play me again mxm")
        else:
            print("\nwhy u chicken out bruh u coulda won it you hit trust me 😏")
        player_turn = False

    elif choice == "hit" and p_score == 21:
        print(f"\netche you won???")
        player_turn = False

    else:
        print("\nHella man I said hit or stand")
