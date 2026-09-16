"""Quest Lab Tutor Notebook.

PYR and the player may edit this file together for examples, drills, and tiny
experiments. Required project source stays player-authored. Examples here
should teach the concept without becoming a paste-ready solution for the
current project.
"""

# PYR can place unrelated teaching examples below this line.
# You can freely change, run, break, and rebuild them.

import random

# --- Section 1: Dealing / Drawing Items ---
def draw_loot():
    """Picks a single random gem from the pool and returns it."""
    gem_pool = ["Ruby", "Emerald", "Sapphire", "Diamond", "Amethyst"]
    picked_gem = random.choice(gem_pool)
    return picked_gem

hero_stash = []
goblin_stash = []

hero_stash.append(draw_loot())
hero_stash.append(draw_loot())

goblin_stash.append(draw_loot())
goblin_stash.append(draw_loot())

print("Hero stash:", hero_stash)
print("Goblin stash:", goblin_stash)

# --- Section 2: Calculating Totals with Numbers ---
# Lists with numbers:
knight_bag = [15, 20, 5]     # 3 items weighing 15kg, 20kg, 5kg
wizard_pouch = [2, 1, 4]     # 3 small items weighing 2kg, 1kg, 4kg
archer_quiver = [3, 4, 5]    # 3 arrows weighing 3g, 4g, 5g

# Method 1: The 'for' loop accumulator (manual counting)
# 'items' is the parameter (placeholder)
def calculate_weight_loop(items):
    total = 0
    for weight in items:
        total = total + weight
    return total

# Calling the function with () and passing the list:
knight_total = calculate_weight_loop(knight_bag)
wizard_total = calculate_weight_loop(wizard_pouch)

print("\n--- Method 1: For Loop Accumulator ---")
print("Knight bag total:", knight_total)
print("Wizard pouch total:", wizard_total)

# Method 2: Python's built-in sum() helper
# Note: sum() only works on numbers (ints/floats), not strings!
def calculate_weight_fast(items):
    return sum(items)

archer_total = calculate_weight_fast(archer_quiver)

print("\n--- Method 2: Built-in sum() ---")
print("Archer quiver total:", archer_total)

# --- Section 3: The Mining Drill (Reference) ---
# (Commented out so Section 4 runs directly when you execute the script)
# mine_cart = ["Coal"]
# while True:
#     choice = input("Type 'dig' or 'leave': ")
#     if choice == "dig": ...
#     elif choice == "leave": break

# --- Section 4: The Potion Cauldron Drill (While Loop + Live Sum) ---
# Scenario: Adding ingredients to a potion until you choose to brew

print("\n--- Section 4: While Loop + Live Sum Drill ---")

def grab_ingredient():
    ingredient_powers = [2, 3, 5, 8, 10]
    return random.choice(ingredient_powers)

cauldron = [4, 6]  # Starting ingredients

while True:
    # 1. Show the current state and current total
    current_power = sum(cauldron)
    print(f"Cauldron: {cauldron} | Current Power: {current_power}")

    # 2. Ask the user for their decision
    choice = input("Type 'add' for more ingredients, or 'brew' to stop: ").lower().strip()

    # 3. Handle their choice
    if choice == "add":
        new_item = grab_ingredient()
        cauldron.append(new_item)
        print(f"-> Bubbling! Added ingredient with {new_item} power.\n")
    elif choice == "brew":
        print(f"-> Stopped! Potion brewed with {current_power} total power.\n")
        break  # Exits the loop!
    else:
        print("-> Huh? Please type 'add' or 'brew'.\n")

print(f"Final Potion Ingredients: {cauldron} (Total Power: {sum(cauldron)})")
