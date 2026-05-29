import random
import math
from brain import Brain

class Soul:
    """
    Independent mind/controller of a Pacman entity.
    Houses the neural brain and resolves driving impulses.
    Decoupled from physical body execution variables.
    """
    def __init__(self, pacman, brain=None):
        self.pacman = pacman
        self.brain = brain if brain is not None else Brain()

    def think(self):
        body = self.pacman
        world = body.world

        # 1. Compile Sensory Inputs
        is_restricted_to_maze = (body.tile_x < 28) and not getattr(body, 'needs_forest_drop', False) and not getattr(body, 'hunting_worm_in_forest', False)

        # Nearest wild food proximity (either mushroom or worm)
        nearest_shroom = None
        min_shroom_dist = float('inf')
        for m in world.mushrooms:
            if m['type'] == "cultivated" and m['growth_timer'] > 0:
                continue
            if is_restricted_to_maze and m['x'] >= 28:
                continue
            d = world.get_distance(body.tile_x, body.tile_y, m['x'], m['y'])
            if d < min_shroom_dist:
                min_shroom_dist = d
                nearest_shroom = m

        nearest_worm = None
        min_worm_dist = float('inf')
        for w in world.worms:
            if is_restricted_to_maze and w.tile_x >= 28:
                continue
            d = world.get_distance(body.tile_x, body.tile_y, w.tile_x, w.tile_y)
            if d < min_worm_dist:
                min_worm_dist = d
                nearest_worm = w

        nearest_food = nearest_shroom
        dist_food = min_shroom_dist
        if nearest_worm and min_worm_dist < dist_food:
            nearest_food = {'x': nearest_worm.tile_x, 'y': nearest_worm.tile_y, 'is_worm': True}
            dist_food = min_worm_dist

        if nearest_food:
            prox_food = 1.0 / (1.0 + dist_food)
        else:
            prox_food = 0.0

        # Home base proximity
        home_base = world.get_home_castle(body.species)
        dist_home = world.get_distance(body.tile_x, body.tile_y, home_base['x'], home_base['y'])
        prox_home = 1.0 / (1.0 + dist_home)

        # Nearest adult enemy proximity
        nearest_enemy = world.find_nearest_enemy(body.tile_x, body.tile_y, body.species)
        if nearest_enemy:
            dist_enemy = world.get_distance(body.tile_x, body.tile_y, nearest_enemy.tile_x, nearest_enemy.tile_y)
            prox_enemy = 1.0 / (1.0 + dist_enemy)
        else:
            prox_enemy = 0.0

        # Nearest compatible adult mate proximity
        nearest_mate = world.find_nearest_mate(body)
        if nearest_mate:
            dist_mate = world.get_distance(body.tile_x, body.tile_y, nearest_mate.tile_x, nearest_mate.tile_y)
            prox_mate = 1.0 / (1.0 + dist_mate)
        else:
            prox_mate = 0.0

        # Normalize sensory input values [0, 1]
        body.last_brain_inputs = [
            prox_food,
            prox_home,
            prox_enemy,
            prox_mate,
            body.energy / 100.0,
            body.age / world.life_expectancy,
            home_base['food_store'] / 50.0
        ]

        # 2. Feedforward neural network pass
        brain_res = self.brain.feed_forward(body.last_brain_inputs)
        # Convert outputs list to mutable array
        outputs = list(brain_res['outputs'])

        # Virgin mating instinct override: boost Mate output (index 3) to seek mate
        if body.is_adult() and body.offspring_count == 0:
            outputs[3] += 0.85

        # Female protection: if an enemy male is near one of our females, boost Attack output
        intruder = world.find_intruder_threatening_female(body)
        if intruder and body.is_adult():
            outputs[2] += 1.5

        # Boost reproduction if species population is critically low (< 3)
        species_pop = len([e for e in world.entities if not e.is_dead and e.species == body.species])
        if body.is_adult() and species_pop < 3:
            outputs[3] += 1.5

        # 3. Choose highest output drive
        drives = ["Forage", "Store", "Attack", "Mate", "Cultivate", "Defend"]
        max_val = -float('inf')
        max_drive_index = 0

        for i, drive in enumerate(drives):
            val = outputs[i]
            # Restriction on infants and old age: no attack (2), mate (3), or cultivate (4)
            if body.is_infant() or body.is_old():
                if i in [2, 3, 4]:
                    continue
            if val > max_val:
                max_val = val
                max_drive_index = i

        body.current_drive = drives[max_drive_index]
        body.last_decision_output = outputs

        # Search for any un-carried baby of our species outside the castle
        rescue_target = None
        if body.is_adult() and getattr(body, 'carrying_baby', None) is None:
            min_baby_dist = float('inf')
            for infant in world.entities:
                if (not infant.is_dead and infant.is_infant() and 
                    infant.species == body.species and 
                    getattr(infant, 'carried_by', None) is None and 
                    not world.is_inside_castle(infant.tile_x, infant.tile_y, infant.species)):
                    
                    d = world.get_distance(body.tile_x, body.tile_y, infant.tile_x, infant.tile_y)
                    if d < min_baby_dist:
                        min_baby_dist = d
                        rescue_target = infant

        # Ants-like behavior / Rescue baby: If carrying food, carrying a worm, carrying a baby, or if there is a rescue target, force drive to Store
        if body.food_carried > 0 or getattr(body, 'has_worm', False) or getattr(body, 'carrying_baby', None) is not None or rescue_target is not None:
            if body.current_drive not in ["Store", "Cultivate"]:
                body.current_drive = "Store"
        elif getattr(body, 'needs_forest_drop', False):
            body.current_drive = "Forage"

        # 4. Adult Castle Base occupancy check
        inside_base = world.is_inside_castle(body.tile_x, body.tile_y, body.species)
        
        # If carrying a baby and inside base, drop the baby off
        if body.is_adult() and getattr(body, 'carrying_baby', None) is not None and inside_base:
            baby = body.carrying_baby
            # Snap baby positions directly to parent to avoid tick order lag
            baby.x = body.x
            baby.y = body.y
            baby.tile_x = body.tile_x
            baby.tile_y = body.tile_y
            
            baby.carried_by = None
            body.carrying_baby = None
            world.add_log(f"🏠 SAFE: {body.name} safely delivered infant {baby.name} to the castle.")

        allowed_inside = (
            body.food_carried > 0 or getattr(body, 'has_worm', False) or 
            getattr(body, 'carrying_baby', None) is not None or
            body.current_drive == "Mate" or 
            (body.energy < 50 and body.eat_cooldown == 0.0)
        )

        if not world.is_night and body.is_adult() and inside_base and not allowed_inside:
            # Force exit to outer corridors
            exit_tile = world.get_random_walkable_corridor()
            if exit_tile:
                path = world.find_path(body.tile_x, body.tile_y, exit_tile['x'], exit_tile['y'], body)
                if path:
                    body.current_path = path
                    body.target_tile = body.current_path.pop(0)
                    body.thought = "Adults must work outside the castle. Exiting."
                    body.current_drive = "Store"
                    return # early exit, exit route locked

        # 5. Determine Target Coordinate
        target_x, target_y = body.tile_x, body.tile_y

        # Night Override
        if world.is_night:
            if inside_base:
                # 1. Target compatible mates inside the base
                if body.is_adult() and body.mating_cooldown == 0.0:
                    nearest_mate = None
                    min_dist = float('inf')
                    for e in world.entities:
                        if e.is_dead or not e.is_adult() or e == body or e.gender == body.gender:
                            continue
                        if world.is_inside_castle(e.tile_x, e.tile_y, body.species) and e.mating_cooldown == 0.0:
                            d = world.get_distance(body.tile_x, body.tile_y, e.tile_x, e.tile_y)
                            if d < min_dist:
                                min_dist = d
                                nearest_mate = e
                    if nearest_mate:
                        target_x, target_y = nearest_mate.tile_x, nearest_mate.tile_y
                        body.current_drive = "Mate"
                        body.thought = f"Night regroup: Pursuing mate {nearest_mate.name} inside our castle!"
                    else:
                        # Fallback to local wandering
                        wander_tile = world.get_random_tile_near(home_base['x'] + 2, home_base['y'] + 2, 2)
                        if world.is_inside_castle(wander_tile['x'], wander_tile['y'], body.species):
                            target_x, target_y = wander_tile['x'], wander_tile['y']
                        else:
                            target_x, target_y = home_base['x'] + 2, home_base['y'] + 2
                        body.current_drive = "Store"
                        body.thought = "ZZZ... Restfully waiting inside our castle."
                elif body.energy < 60 and home_base['food_store'] > 0:
                    target_x, target_y = home_base['x'] + 2, home_base['y'] + 2
                    body.current_drive = "Store"
                    body.thought = "Feeling hungry at night, eating from reserves."
                else:
                    # Sleep/Regroup: local wandering inside castle
                    wander_tile = world.get_random_tile_near(home_base['x'] + 2, home_base['y'] + 2, 2)
                    if world.is_inside_castle(wander_tile['x'], wander_tile['y'], body.species):
                        target_x, target_y = wander_tile['x'], wander_tile['y']
                    else:
                        target_x, target_y = home_base['x'] + 2, home_base['y'] + 2
                    body.current_drive = "Store"
                    body.thought = "ZZZ... Restfully waiting inside our castle."
            else:
                target_x, target_y = home_base['x'] + 2, home_base['y'] + 2
                body.current_drive = "Store"
                body.thought = "🌌 NIGHT ALERT: Running back to the castle before zombies devour me!"

        # Forest Drop Override
        elif getattr(body, 'needs_forest_drop', False):
            if body.tile_x < 28:
                forest_tile = world.get_random_walkable_forest_tile()
                target_x, target_y = forest_tile['x'], forest_tile['y']
                body.thought = "Heading to the forest to drop mushroom waste."
            else:
                world.spawn_dropped_mushroom_at(body.tile_x, body.tile_y)
                body.needs_forest_drop = False
                body.hunting_worm_in_forest = True
                world.add_log(f"💩 DROP: {body.name} dropped a mushroom in the forest for worms.")
                body.thought = "Dropped mushroom waste. Now smelling worm!"
                body.target_tile = None
                body.current_path = []
                body.soul.think()
                return

        # Forest Worm Hunt Override
        elif getattr(body, 'hunting_worm_in_forest', False):
            nearest_forest_worm = None
            min_f_worm_dist = float('inf')
            for w in world.worms:
                if w.tile_x >= 28:
                    d = world.get_distance(body.tile_x, body.tile_y, w.tile_x, w.tile_y)
                    if d < min_f_worm_dist:
                        min_f_worm_dist = d
                        nearest_forest_worm = w
            
            if nearest_forest_worm:
                target_x, target_y = nearest_forest_worm.tile_x, nearest_forest_worm.tile_y
                body.current_drive = "Forage"
                body.thought = f"Smelling and hunting worm at ({target_x}, {target_y}) in the forest!"
            else:
                body.hunting_worm_in_forest = False
                target_x, target_y = home_base['x'], home_base['y']
                body.current_drive = "Store"
                body.thought = "No worms in forest. Exiting forest."

        # Forest Escape Override
        elif body.tile_x >= 28:
            target_x, target_y = home_base['x'], home_base['y']
            body.current_drive = "Store"
            body.thought = "Task done. Exiting forest immediately."

        # Panic Override: low population (< 3)
        elif species_pop < 3 and body.is_adult():
            if body.gender == "male":
                rival_females = [e for e in world.entities if not e.is_dead and e.is_adult() and e.gender == "female" and e.species != body.species]
                if rival_females:
                    if body.food_carried == 0:
                        nearest_m = world.find_nearest_mushroom(body.tile_x, body.tile_y)
                        if nearest_m:
                            target_x, target_y = nearest_m['x'], nearest_m['y']
                        else:
                            wander = world.get_random_walkable_tile(body.tile_x, body.tile_y, body)
                            target_x, target_y = wander['x'], wander['y']
                        body.current_drive = "Forage"
                        body.thought = "PANIC: Foraging mushroom to gift to rival female to attract mate!"
                    else:
                        nearest_rf = min(rival_females, key=lambda f: world.get_distance(body.tile_x, body.tile_y, f.tile_x, f.tile_y))
                        target_x, target_y = nearest_rf.tile_x, nearest_rf.tile_y
                        body.current_drive = "Mate"
                        body.thought = f"PANIC COURTSHIP: Gifting mushroom to rival female {nearest_rf.name} to mate!"
                else:
                    # Mating with own-species females
                    own_females = [e for e in world.entities if not e.is_dead and e.is_adult() and e.gender == "female" and e.species == body.species]
                    if own_females:
                        nearest_of = min(own_females, key=lambda f: world.get_distance(body.tile_x, body.tile_y, f.tile_x, f.tile_y))
                        target_x, target_y = nearest_of.tile_x, nearest_of.tile_y
                        body.current_drive = "Mate"
                        body.thought = f"PANIC: Low population! Mating with own female {nearest_of.name}."
                    else:
                        base_wander = world.get_random_tile_near(home_base['x'], home_base['y'], 4)
                        target_x, target_y = base_wander['x'], base_wander['y']
                        body.current_drive = "Mate"
                        body.thought = "PANIC: No females available. Waiting near castle."
            
            elif body.gender == "female":
                # "if only female available, it mates with senior/old pacman to produce offspring. else it mates with rival male"
                own_males = [e for e in world.entities if not e.is_dead and e.species == body.species and e.gender == "male" and e.is_adult()]
                if len(own_males) == 0:
                    senior_males = [e for e in world.entities if not e.is_dead and e.species == body.species and e.gender == "male" and e.is_old()]
                    if senior_males:
                        nearest_senior = min(senior_males, key=lambda m: world.get_distance(body.tile_x, body.tile_y, m.tile_x, m.tile_y))
                        target_x, target_y = nearest_senior.tile_x, nearest_senior.tile_y
                        body.current_drive = "Mate"
                        body.thought = f"PANIC: No local males! Mating with senior {nearest_senior.name}."
                    else:
                        rival_males = [e for e in world.entities if not e.is_dead and e.species != body.species and e.gender == "male" and e.is_adult()]
                        if rival_males:
                            nearest_rm = min(rival_males, key=lambda m: world.get_distance(body.tile_x, body.tile_y, m.tile_x, m.tile_y))
                            target_x, target_y = nearest_rm.tile_x, nearest_rm.tile_y
                            body.current_drive = "Mate"
                            body.thought = f"PANIC: Mating with rival male {nearest_rm.name}."
                        else:
                            base_wander = world.get_random_tile_near(home_base['x'], home_base['y'], 4)
                            target_x, target_y = base_wander['x'], base_wander['y']
                            body.current_drive = "Mate"
                            body.thought = "PANIC: No mates found. Waiting near castle."
                else:
                    # Mating with own-species males
                    nearest_om = min(own_males, key=lambda m: world.get_distance(body.tile_x, body.tile_y, m.tile_x, m.tile_y))
                    target_x, target_y = nearest_om.tile_x, nearest_om.tile_y
                    body.current_drive = "Mate"
                    body.thought = f"PANIC: Breeding with colony male {nearest_om.name}."

        # Greed Override: high population (> 10)
        elif world.greed_active.get(body.species, False) and body.is_adult():
            # 1. Target rival infants (even in castles)
            rival_infants = [e for e in world.entities if not e.is_dead and e.is_infant() and e.species != body.species]
            if rival_infants:
                nearest_infant = min(rival_infants, key=lambda infant: world.get_distance(body.tile_x, body.tile_y, infant.tile_x, infant.tile_y))
                target_x, target_y = nearest_infant.tile_x, nearest_infant.tile_y
                body.current_drive = "Attack"
                body.thought = f"GREED: Infiltrating to kill rival infant {nearest_infant.name}!"
            else:
                # 2. Target rival males to fight
                rival_males = [e for e in world.entities if not e.is_dead and e.is_adult() and e.gender == "male" and e.species != body.species]
                if rival_males:
                    nearest_rm = min(rival_males, key=lambda m: world.get_distance(body.tile_x, body.tile_y, m.tile_x, m.tile_y))
                    target_x, target_y = nearest_rm.tile_x, nearest_rm.tile_y
                    body.current_drive = "Attack"
                    body.thought = f"GREED: Hunting rival male {nearest_rm.name} to fight!"
                else:
                    # 3. Target mushrooms to eat
                    nearest_m = world.find_nearest_mushroom(body.tile_x, body.tile_y)
                    if nearest_m:
                        target_x, target_y = nearest_m['x'], nearest_m['y']
                        body.current_drive = "Forage"
                        body.thought = "GREED: Devouring mushroom to satisfy hunger!"
                    else:
                        wander = world.get_random_walkable_tile(body.tile_x, body.tile_y, body)
                        target_x, target_y = wander['x'], wander['y']
                        body.current_drive = "Forage"
                        body.thought = "GREED: Wandering for food."

        # Normal Drive Targets
        else:
            if body.current_drive == "Forage":
                if nearest_food:
                    target_x, target_y = nearest_food['x'], nearest_food['y']
                    if nearest_food.get('is_worm'):
                        body.thought = "Hunting a wiggling worm in the forest!"
                    else:
                        body.thought = "I am crawling around looking for a magic mushroom!" if body.is_infant() else "Searching for a wild magic mushroom to forage."
                else:
                    wander = world.get_random_walkable_tile(body.tile_x, body.tile_y, body)
                    target_x, target_y = wander['x'], wander['y']
                    body.thought = "No food in sight. Wandering around."

            elif body.current_drive == "Store":
                if getattr(body, 'carrying_baby', None) is not None:
                    target_x, target_y = home_base['x'], home_base['y']
                    body.thought = f"Carrying baby {body.carrying_baby.name} back to the safety of our castle!"
                elif body.is_adult() and body.food_carried == 0 and not getattr(body, 'has_worm', False) and rescue_target is None and not (body.energy < 50 and body.eat_cooldown == 0.0):
                    gate = home_base['gates'][0]
                    target_x, target_y = gate['x'], gate['y']
                    body.thought = "Heading to our castle gates to regroup."
                elif rescue_target is not None:
                    target_x, target_y = rescue_target.tile_x, rescue_target.tile_y
                    body.thought = f"Going to rescue baby {rescue_target.name} outside the castle!"
                else:
                    target_x, target_y = home_base['x'], home_base['y']
                    if getattr(body, 'has_worm', False):
                        body.thought = "Carrying a worm back to our castle reserves."
                    elif body.food_carried > 0:
                        body.thought = f"Carrying {body.food_carried} mushroom(s) back to our castle."
                    elif body.energy < 40 and home_base['food_store'] > 0:
                        body.thought = "Heading back home to eat from the castle reserves."
                    else:
                        body.thought = "Heading home to regroup."

            elif body.current_drive == "Attack":
                intruder = world.find_intruder_threatening_female(body)
                if intruder:
                    target_x, target_y = intruder.tile_x, intruder.tile_y
                    body.thought = f"DEFENDER: Chasing rival male {intruder.name} to protect our females!"
                elif nearest_enemy:
                    target_x, target_y = nearest_enemy.tile_x, nearest_enemy.tile_y
                    body.thought = f"Intruder alert! Moving to confront enemy {nearest_enemy.name}."
                else:
                    enemy_species = "stripes" if body.species == "spots" else "spots"
                    enemy_base = world.get_home_castle(enemy_species)
                    target_x, target_y = enemy_base['x'], enemy_base['y']
                    body.thought = "Infiltrating the enemy castle to pillage their reserves!"

            elif body.current_drive == "Mate":
                if nearest_mate:
                    target_x, target_y = nearest_mate.tile_x, nearest_mate.tile_y
                    body.thought = f"I find {nearest_mate.name}'s glow highly attractive! Pursuing."
                else:
                    base_wander = world.get_random_tile_near(home_base['x'], home_base['y'], 4)
                    target_x, target_y = base_wander['x'], base_wander['y']
                    body.thought = "Searching for mates near our home castle."

            elif body.current_drive == "Cultivate":
                if world.cultivation_unlocked[body.species]:
                    free_soil = world.get_free_garden_soil(body.species)
                    if free_soil and body.food_carried > 0:
                        target_x, target_y = free_soil['x'], free_soil['y']
                        body.thought = "Cultivating... Planting a mushroom seed in our garden."
                    else:
                        target_x, target_y = home_base['x'], home_base['y']
                        body.thought = "No planting soil available, delivering food to castle."
                else:
                    target_x, target_y = home_base['x'], home_base['y']
                    body.thought = "We need more stored food to invent agricultural cultivation!"

            elif body.current_drive == "Defend":
                gates = home_base['gates']
                if gates:
                    gate = random.choice(gates)
                    target_x, target_y = gate['x'], gate['y']
                    body.thought = "I am too old to hunt, but I will guard our castle entrance!" if body.is_old() else "Patrolling our castle gates to ward off thieves."
                else:
                    target_x, target_y = home_base['x'], home_base['y']
                    body.thought = "Guarding the castle interior."

        # 6. Recompute Path if Target Changed
        if body.target_tile and body.target_tile['x'] == target_x and body.target_tile['y'] == target_y and len(body.current_path) > 0:
            return

        path = world.find_path(body.tile_x, body.tile_y, target_x, target_y, body)
        if path:
            body.current_path = path
            body.target_tile = body.current_path.pop(0)
        else:
            # Fallback to prevent freezing: try to wander to a random walkable neighbor
            wander = world.get_random_walkable_tile(body.tile_x, body.tile_y, body)
            if wander['x'] != body.tile_x or wander['y'] != body.tile_y:
                body.current_path = [wander]
                body.target_tile = body.current_path.pop(0)
                body.thought = "Target unreachable. Wandering to find a way."
            else:
                body.target_tile = None
