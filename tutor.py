"""Quest Lab Tutor Notebook — PYR Teaching Drills

Concept: while loops + input() + list modification
Domain: Adventurer's Backpack (Unrelated to Blackjack)
"""
"""
# =====================================================================
# EXAMPLE 0: What strip() and lower() do
# =====================================================================

def demo_strip_and_lower():
    messy_input = "   PACK  \n"
    print(f"Original messy string: '{messy_input}' (Length: {len(messy_input)})")
    
    # 1. strip() removes leading and trailing spaces/newlines
    stripped = messy_input.strip()
    print(f"After .strip():        '{stripped}' (Length: {len(stripped)})")
    
    # 2. lower() turns capital letters into lowercase
    lowered = stripped.lower()
    print(f"After .lower():        '{lowered}'")
    
    # Chained together: messy_input.strip().lower() -> "pack"

# =====================================================================
# EXAMPLE 1: The Infinite Backpack Loop
# =====================================================================

def run_backpack_drill():
    print("🎒 Welcome to the Equipment Tent!")
    backpack = ["Torches", "Rations"]
    
    is_packing = True
    while is_packing:
        print(f"\nYour current backpack: {backpack}")
        choice = input("Do you want to (pack / done)? ").strip().lower()
        
        if choice == "pack":
            item = input("What item do you want to add? ").strip()
            backpack.append(item)
            print(f"--> Added '{item}' to your backpack.")
        elif choice == "done":
            print("Finished packing!")
            is_packing = False
        else:
            print("⚠️ Invalid command! Please type 'pack' or 'done'.")
            
    print(f"\nFinal Backpack Contents: {backpack}")
"""
# =====================================================================
# YOUR PRACTICE EXERCISE (Try running tutor.py and completing this):
# =====================================================================
# Modify run_potion_seller() below so that:
# 1. It keeps asking the buyer if they want to 'buy' or 'leave'.
# 2. If they type 'buy', subtract 10 gold and add a 'Potion' to inventory.
# 3. If gold falls below 10, print "Not enough gold!" and stop the loop.
# 4. If they type 'leave', set shopping = False to end the loop.

def run_potion_seller():
    gold = 30
    inventory = []
    is_selling = True
    
    print("\n🧪 Potion Shop Open!")
    
    # --- WRITE YOUR WHILE LOOP BELOW THIS LINE ---
    while is_selling:
        choice = input("Do you want to (buy / leave)?").strip().lower()

        if choice == "buy" and gold >= 10:
            inventory.append("Potion")
            gold = gold - 10
            print(f"\n you now have {gold} gold left")
            print("thank you for your purchase")
            if gold < 10:
                print("\n BROKE BOY, BROKE BOOYYYYYY GET TF OUT MY STORE")
                is_selling = False

        elif choice == "leave":
            print("\n lmao u dont got it like that anyways")
            is_selling = False


if __name__ == "__main__":
    # See what strip() and lower() do:
    #demo_strip_and_lower()
    #print("-" * 40)
    # Run the demo first!
    run_potion_seller()


# ill make a function to try run a loop to print out 10 numbers at random
