import random
import math
from soul import Soul

MALE_NAMES = ["Blinky", "Clyde", "Pako", "Chomp", "Munchy", "Bitey", "Paczo", "Glowy", "Glider", "Swift", "Ranger", "Hunter"]
FEMALE_NAMES = ["Pinky", "Dotty", "Stripa", "Rosy", "Mimi", "Penny", "Lulu", "Bella", "Tina", "Zelda", "Vicky", "Flora"]

def generate_name(gender, species, generation):
    names = MALE_NAMES if gender == "male" else FEMALE_NAMES
    base = random.choice(names)
    if generation > 1:
        # Convert generation to Roman numeral
        val = [10, 9, 5, 4, 1]
        syb = ["X", "IX", "V", "IV", "I"]
        roman = ""
        i = 0
        temp = generation
        while temp > 0:
            for _ in range(temp // val[i]):
                roman += syb[i]
                temp -= val[i]
            i += 1
        return f"{base} {roman}"
    return base

class Pacman:
    """
    Physical body of the Pac-Man entity.
    Maintains positions, velocity, energy, age, and delivers motor command updates.
    """
    def __init__(self, world, x, y, species, gender, brain=None, generation=1):
        self.world = world
        self.x = float(x)
        self.y = float(y)
        self.tile_x = int(round(x))
        self.tile_y = int(round(y))
        
        self.species = species      # "spots" | "stripes"
        self.gender = gender        # "male" | "female"
        self.generation = generation
        self.name = generate_name(gender, species, generation)
        
        # Attach the Decoupled Soul Mind
        self.soul = Soul(self, brain)
        self.brain = self.soul.brain # Backwards compatible alias reference
        
        self.age = 0.0
        self.energy = 80.0 + random.random() * 20.0
        self.food_carried = 0
        self.has_worm = False
        self.worm_eat_cooldown = 0.0
        self.max_food_carry = 1
        self.fitness = 0
        
        self.speed = 0.08 # glide speed per tick
        self.current_path = []
        self.target_tile = None
        
        # Decision diagnostics
        self.last_decision_output = [0.0] * 6
        self.last_brain_inputs = [0.0] * 7
        self.current_drive = "Forage"
        self.thought = "I am ready to explore this new world!"
        
        self.offspring_count = 0
        self.mating_cooldown = 0.0
        self.mentor_cooldown = 0.0
        self.eat_cooldown = 0.0
        self.glow_intensity = 0.0
        
        self.carrying_baby = None
        self.carried_by = None
        
        self.mushrooms_eaten = 0
        self.needs_forest_drop = False
        self.hunting_worm_in_forest = False
        self.father = None
        self.mother = None
        
        self.is_dead = False
        self.death_reason = ""

    def update(self):
        if self.is_dead:
            return

        # 1. Age progression (1/60th second per tick at 60fps)
        self.age += 1.0 / 60.0
        if self.age >= self.world.life_expectancy:
            self.die("Old Age")
            return

        # 2. Energy consumption
        energy_loss = 0.08
        if self.is_infant():
            energy_loss = 0.05
        elif self.is_old():
            energy_loss = 0.06

        self.energy -= energy_loss / 60.0

        # If infant is inside home castle and hungry, automatically eat from reserves to grow
        if self.is_infant() and self.energy < 70.0:
            home = self.world.get_home_castle(self.species)
            if self.world.is_inside_castle(self.tile_x, self.tile_y, self.species) and home['food_store'] > 0:
                home['food_store'] -= 1
                self.energy = min(100.0, self.energy + 40.0)
                self.thought = "Eating food from castle storage to grow!"
                self.world.add_log(f"🍼 GROW: Infant {self.name} ate a stored mushroom from castle storage.")

        if self.energy <= 0:
            self.die("Starvation")
            return

        # 3. Decrement Cooldowns
        if self.mating_cooldown > 0:
            self.mating_cooldown = max(0.0, self.mating_cooldown - 1.0 / 60.0)
        if self.mentor_cooldown > 0:
            self.mentor_cooldown = max(0.0, self.mentor_cooldown - 1.0 / 60.0)
        if self.eat_cooldown > 0:
            self.eat_cooldown = max(0.0, self.eat_cooldown - 1.0 / 60.0)
        if self.worm_eat_cooldown > 0:
            self.worm_eat_cooldown = max(0.0, self.worm_eat_cooldown - 1.0 / 60.0)

        # 4. Glow Intensity
        self.glow_intensity = min(1.0, (self.fitness * 0.04) + (0.3 if self.energy > 80.0 else 0.0))

        # 5. Think & Route Decisions via Decoupled Soul
        if self.carried_by is not None:
            # Position is locked to carrying parent
            self.x = self.carried_by.x
            self.y = self.carried_by.y
            self.tile_x = self.carried_by.tile_x
            self.tile_y = self.carried_by.tile_y
            self.target_tile = None
            self.current_path = []
        elif not self.target_tile or (abs(self.x - self.tile_x) < 0.05 and abs(self.y - self.tile_y) < 0.05):
            self.tile_x = int(round(self.x))
            self.tile_y = int(round(self.y))
            self.soul.think()

        # 6. Execute continuous glide step
        self.move()

    def is_infant(self):
        return self.age < self.world.life_expectancy * 0.1

    def is_adult(self):
        return self.world.life_expectancy * 0.1 <= self.age < self.world.life_expectancy * 0.9

    def is_old(self):
        return self.age >= self.world.life_expectancy * 0.9

    def move(self):
        if self.carried_by is not None:
            self.x = self.carried_by.x
            self.y = self.carried_by.y
            self.tile_x = self.carried_by.tile_x
            self.tile_y = self.carried_by.tile_y
            self.target_tile = None
            self.current_path = []
            return

        if not self.target_tile:
            return

        dx = self.target_tile['x'] - self.x
        dy = self.target_tile['y'] - self.y
        dist = math.sqrt(dx*dx + dy*dy)

        # Modifiers on speed
        current_speed = self.speed
        if self.is_old():
            current_speed = self.speed * 0.6
        elif self.is_infant():
            current_speed = self.speed * 0.65
        
        if self.food_carried > 0 or self.has_worm:
            current_speed *= 0.85

        if dist <= current_speed:
            # Snapped to target tile
            self.x = float(self.target_tile['x'])
            self.y = float(self.target_tile['y'])
            self.tile_x = self.target_tile['x']
            self.tile_y = self.target_tile['y']

            self.check_target_interaction()

            if len(self.current_path) > 0:
                self.target_tile = self.current_path.pop(0)
            else:
                self.target_tile = None
        else:
            # Glide step
            self.x += (dx / dist) * current_speed
            self.y += (dy / dist) * current_speed

    def check_target_interaction(self):
        # 1. Food foraging
        if self.current_drive == "Forage":
            # Check for a worm first
            worm = next((w for w in self.world.worms if w.tile_x == self.tile_x and w.tile_y == self.tile_y), None)
            if worm:
                self.world.consume_worm(worm)
                self.hunting_worm_in_forest = False
                if self.energy < 80 and self.worm_eat_cooldown == 0.0:
                    self.age = max(0.0, self.age - 0.20 * self.world.life_expectancy)
                    self.energy = min(100.0, self.energy + 40.0)
                    self.worm_eat_cooldown = 300.0
                    self.fitness += 3
                    self.thought = "Ate a fresh worm! I feel 20% younger!"
                    self.world.add_log(f"🧬 REJUVENATION: {self.name} ate a wild worm (5m digestion cooldown started).")
                else:
                    self.has_worm = True
                    self.thought = "Caught a worm! Carrying it back to the castle."
                    self.world.add_log(f"🪱 HUNT: {self.name} caught a worm and is bringing it back.")
            else:
                shroom = self.world.get_mushroom_at(self.tile_x, self.tile_y)
                if shroom:
                    self.world.consume_mushroom(shroom['id'])
                    
                    can_eat = not self.is_adult() or self.eat_cooldown == 0.0
                    if self.energy < 60 and can_eat:
                        self.energy = min(100.0, self.energy + 35.0)
                        self.fitness += 1
                        self.thought = "Yum! That magic mushroom tasted fantastic."
                        if self.is_adult():
                            self.eat_cooldown = 120.0 # 2 minute digestion cooldown
                            self.world.add_log(f"{self.name} ate a wild mushroom (2m digestion cooldown started).")
                        if not self.is_infant():
                            self.mushrooms_eaten += 1
                            if self.mushrooms_eaten >= 2:
                                self.needs_forest_drop = True
                                self.mushrooms_eaten = 0
                    else:
                        self.food_carried = min(self.max_food_carry, self.food_carried + 1)
                        self.thought = "Harvested mushroom! Carrying it to the castle."

        # 2. Base Delivery
        elif self.current_drive == "Store":
            home = self.world.get_home_castle(self.species)
            dist = self.world.get_distance(self.tile_x, self.tile_y, home['x'], home['y'])
            if dist <= 2:
                if self.has_worm:
                    home['worms_store'] = home.get('worms_store', 0) + 1
                    self.fitness += 5
                    self.world.add_log(f"🪱 STORE: {self.name} delivered a worm to the {self.species} castle reserves.")
                    self.has_worm = False
                elif self.food_carried > 0:
                    home['food_store'] += self.food_carried
                    self.fitness += self.food_carried * 3
                    self.world.add_log(f"{self.name} stored {self.food_carried} food in the {self.species} castle.")
                    self.food_carried = 0
                
                # Check hunger eating: stored worms first, then mushrooms
                if self.energy < 70 and home.get('worms_store', 0) > 0 and self.worm_eat_cooldown == 0.0:
                    home['worms_store'] -= 1
                    self.age = max(0.0, self.age - 0.20 * self.world.life_expectancy)
                    self.energy = min(100.0, self.energy + 40.0)
                    self.worm_eat_cooldown = 300.0
                    self.fitness += 1
                    self.thought = "Ate a stored worm! I feel 20% younger!"
                    self.world.add_log(f"🧬 REJUVENATION: {self.name} ate a stored worm from castle reserves (5m digestion cooldown started).")
                elif self.energy < 50 and home['food_store'] > 0:
                    can_eat = not self.is_adult() or self.eat_cooldown == 0.0
                    if can_eat:
                        home['food_store'] -= 1
                        self.energy = min(100.0, self.energy + 40.0)
                        self.thought = "Ate a mushroom from our castle storage."
                        if self.is_adult():
                            self.eat_cooldown = 120.0
                            self.world.add_log(f"{self.name} ate from castle storage (2m digestion cooldown started).")
                        if not self.is_infant():
                            self.mushrooms_eaten += 1
                            if self.mushrooms_eaten >= 2:
                                self.needs_forest_drop = True
                                self.mushrooms_eaten = 0

        # 3. Garden Planting
        elif self.current_drive == "Cultivate" and self.food_carried > 0:
            if self.world.is_garden_soil(self.tile_x, self.tile_y, self.species):
                self.world.plant_mushroom(self.tile_x, self.tile_y, self.species)
                self.food_carried = 0
                self.fitness += 2
                self.thought = "Soil seeded successfully! It will grow soon."
                self.world.add_log(f"{self.name} cultivated a magic mushroom near their base.")

        # 4. Raid enemy base
        elif self.current_drive == "Attack":
            enemy_species = "stripes" if self.species == "spots" else ("spots" if self.species == "stripes" else None)
            if enemy_species:
                enemy_base = self.world.get_home_castle(enemy_species)
                dist = self.world.get_distance(self.tile_x, self.tile_y, enemy_base['x'], enemy_base['y'])
                if dist <= 2 and enemy_base['food_store'] > 0:
                    enemy_base['food_store'] -= 1
                    self.food_carried = min(self.max_food_carry, self.food_carried + 1)
                    self.fitness += 2
                    self.thought = "Pillaged enemy base food! Escaping home."
                    self.world.add_log(f"⚠️ THIEVERY: {self.name} stole food from the {enemy_species} castle!")
                    self.soul.think() # rethink immediately

    def die(self, reason):
        self.is_dead = True
        self.death_reason = reason
        self.world.add_log(f"💀 DEATH: {self.name} of {self.species} died of {reason}.")
        
        # Release carrying/carried state
        if getattr(self, 'carrying_baby', None) is not None:
            self.carrying_baby.carried_by = None
            self.carrying_baby = None
        if getattr(self, 'carried_by', None) is not None:
            self.carried_by.carrying_baby = None
            self.carried_by = None
        
        # Spawn wild mushroom on death
        if random.random() < 0.6:
            self.world.spawn_mushroom_at(self.tile_x, self.tile_y)

class Worm:
    """
    Prey entity spawning in the Forest.
    Glides away from approaching Pac-men.
    """
    def __init__(self, world, x, y):
        self.world = world
        self.x = float(x)
        self.y = float(y)
        self.tile_x = int(round(x))
        self.tile_y = int(round(y))
        self.speed = 0.05
        self.target_tile = None
        self.current_path = []
        self.wiggling_offset = 0.0 # for wiggling animation in UI

    def update(self):
        self.wiggling_offset += 0.2
        
        # Determine movement when snapped or at target
        if not self.target_tile or (abs(self.x - self.tile_x) < 0.05 and abs(self.y - self.tile_y) < 0.05):
            self.x = float(self.tile_x)
            self.y = float(self.tile_y)
            
            # Check for nearby Pac-man
            nearest_pac = None
            min_dist = 4.0
            for e in self.world.entities:
                if e.is_dead:
                    continue
                d = self.world.get_distance(self.tile_x, self.tile_y, e.tile_x, e.tile_y)
                if d < min_dist:
                    min_dist = d
                    nearest_pac = e

            dirs = [{'x': 0, 'y': -1}, {'x': 0, 'y': 1}, {'x': -1, 'y': 0}, {'x': 1, 'y': 0}]
            best_tile = None
            
            if nearest_pac:
                # Evasion: choose walkable neighbor that maximizes distance to the nearest Pac-man
                max_d = -1.0
                for d in dirs:
                    tx = self.tile_x + d['x']
                    ty = self.tile_y + d['y']
                    # Restricted to the Forest region (columns >= 28)
                    if tx >= 28 and self.world.is_walkable(tx, ty):
                        dist_to_pac = self.world.get_distance(tx, ty, nearest_pac.tile_x, nearest_pac.tile_y)
                        if dist_to_pac > max_d:
                            max_d = dist_to_pac
                            best_tile = {'x': tx, 'y': ty}
            
            if not best_tile:
                # Target nearest mushroom in the forest if not fleeing
                nearest_shroom = None
                min_shroom_dist = 6.0
                for m in self.world.mushrooms:
                    if m['x'] >= 28: # in the forest
                        d = self.world.get_distance(self.tile_x, self.tile_y, m['x'], m['y'])
                        if d < min_shroom_dist:
                            min_shroom_dist = d
                            nearest_shroom = m

                if nearest_shroom:
                    # Choose neighbor that minimizes distance to the mushroom
                    min_d = 999.0
                    for d in dirs:
                        tx = self.tile_x + d['x']
                        ty = self.tile_y + d['y']
                        if tx >= 28 and self.world.is_walkable(tx, ty):
                            dist_to_shroom = self.world.get_distance(tx, ty, nearest_shroom['x'], nearest_shroom['y'])
                            if dist_to_shroom < min_d:
                                min_d = dist_to_shroom
                                best_tile = {'x': tx, 'y': ty}

            if not best_tile:
                # Wander randomly in the forest
                walkable = []
                for d in dirs:
                    tx = self.tile_x + d['x']
                    ty = self.tile_y + d['y']
                    if tx >= 28 and self.world.is_walkable(tx, ty):
                        walkable.append({'x': tx, 'y': ty})
                if walkable:
                    best_tile = random.choice(walkable)
                else:
                    best_tile = {'x': self.tile_x, 'y': self.tile_y}
            
            self.target_tile = best_tile

        # Execute smooth glide step
        if self.target_tile:
            dx = self.target_tile['x'] - self.x
            dy = self.target_tile['y'] - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist <= self.speed:
                self.x = float(self.target_tile['x'])
                self.y = float(self.target_tile['y'])
                self.tile_x = self.target_tile['x']
                self.tile_y = self.target_tile['y']
                self.target_tile = None
            else:
                self.x += (dx / dist) * self.speed
                self.y += (dy / dist) * self.speed

class Zombie:
    """
    Zombie entity that spawns at night.
    Pathfinds towards the nearest Pac-man who is outside castles.
    Moves at a high speed.
    """
    def __init__(self, world, x, y):
        self.world = world
        self.x = float(x)
        self.y = float(y)
        self.tile_x = int(round(x))
        self.tile_y = int(round(y))
        self.speed = 0.09
        self.target_tile = None
        self.current_path = []
        self.is_zombie = True

    def update(self):
        # 1. Target selection: nearest Pac-man who is outside its home castle
        nearest_pac = None
        min_dist = float('inf')
        for e in self.world.entities:
            if e.is_dead:
                continue
            if not self.world.is_inside_castle(e.tile_x, e.tile_y, e.species):
                d = self.world.get_distance(self.tile_x, self.tile_y, e.tile_x, e.tile_y)
                if d < min_dist:
                    min_dist = d
                    nearest_pac = e

        # 2. Determine movement when snapped or at target
        if not self.target_tile or (abs(self.x - self.tile_x) < 0.05 and abs(self.y - self.tile_y) < 0.05):
            self.x = float(self.tile_x)
            self.y = float(self.tile_y)

            best_tile = None
            if nearest_pac:
                path = self.world.find_path(self.tile_x, self.tile_y, nearest_pac.tile_x, nearest_pac.tile_y, self)
                if path:
                    best_tile = path[0]

            if not best_tile:
                # Wander randomly among walkable non-castle tiles
                dirs = [{'x': 0, 'y': -1}, {'x': 0, 'y': 1}, {'x': -1, 'y': 0}, {'x': 1, 'y': 0}]
                walkable = []
                for d in dirs:
                    tx = self.tile_x + d['x']
                    ty = self.tile_y + d['y']
                    if self.world.is_walkable(tx, ty, self) and not self.world.is_inside_any_castle(tx, ty):
                        walkable.append({'x': tx, 'y': ty})
                if walkable:
                    best_tile = random.choice(walkable)
                else:
                    best_tile = {'x': self.tile_x, 'y': self.tile_y}

            self.target_tile = best_tile

        # 3. Execute smooth glide step
        if self.target_tile:
            dx = self.target_tile['x'] - self.x
            dy = self.target_tile['y'] - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist <= self.speed:
                self.x = float(self.target_tile['x'])
                self.y = float(self.target_tile['y'])
                self.tile_x = self.target_tile['x']
                self.tile_y = self.target_tile['y']
                self.target_tile = None
            else:
                self.x += (dx / dist) * self.speed
                self.y += (dy / dist) * self.speed

