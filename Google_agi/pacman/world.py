import random
import datetime
import torch
from entity import Pacman, Worm
from brain import Brain

# Symmetric 27x21 grid maze layout (1 = Solid Wall, 0 = Walkable Corridor)
MAZE_LAYOUT = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,1,1,1,0,1,0,1,1,1,0,1,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,1,0,1,1,1,1,1,0,1,0,1,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,1,1,0,1,0,0,0,1,0,0,0,1,0,1,1,0,0,0,0,0,0,1],
    [1,1,0,1,1,1,0,0,0,1,1,0,1,0,1,1,0,0,0,1,1,1,0,1,1,1,1],
    [1,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,1],
    [1,0,1,0,1,0,1,1,1,0,1,1,0,1,1,0,1,1,1,0,1,0,1,0,1,0,1],
    [1,0,1,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,1,0,1,0,1],
    [1,0,1,1,1,1,1,0,1,0,1,0,0,0,1,0,1,0,1,1,1,1,1,0,1,0,1],
    [1,0,1,0,0,0,0,0,1,0,1,0,0,0,1,0,1,0,0,0,0,0,1,0,1,0,1],
    [1,0,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,0,1,0,1,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,1],
    [1,1,1,1,0,1,1,0,1,1,1,0,1,0,1,1,1,0,1,1,0,1,1,0,1,0,1],
    [1,0,0,0,0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,0,0,1,0,0,0,1],
    [1,0,0,0,0,0,1,0,1,0,1,1,1,1,1,0,1,0,1,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,1,1,1,0,1,0,1,1,1,0,1,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
]

class SimulationWorld:
    """
    Simulation World manager. Houses game map coordinates, pathfinder solvers,
    mushrooms lists, logs list, and controls interaction updates.
    """
    def __init__(self):
        self.width = 47
        self.height = 21
        
        # Build extended 47x21 map (0-26 Maze, 27 partition wall with gates, 28-46 Forest)
        self.maze_map = []
        for y in range(self.height):
            row = list(MAZE_LAYOUT[y])
            # Make column 26 walkable at row 10 and 11 to connect to the gate at column 27
            if y in [10, 11]:
                row[26] = 0
                row.append(0)
            else:
                row.append(1)
            
            # Forest (19 columns)
            # Spawn trees randomly (12% chance) but keep boundaries closed
            forest_row = []
            for x in range(19):
                if y in [0, 20]: # Boundary walls
                    forest_row.append(1)
                elif x == 18: # Right boundary wall
                    forest_row.append(1)
                elif y in [10, 11] and x < 4: # Clear entrance area
                    forest_row.append(0)
                else:
                    forest_row.append(1 if random.random() < 0.12 else 0)
            row.extend(forest_row)
            self.maze_map.append(row)
        
        self.entities = []
        self.mushrooms = []
        self.worms = []
        self.logs = []
        
        self.is_paused = False
        self.speed_multiplier = 1
        self.life_expectancy = 900.0 # Default 15 minutes in seconds
        self.show_path_guide = False
        
        # Base Castle coordinates
        self.castles = {
            'spots': {
                'x': 2, 'y': 2, 'w': 5, 'h': 5,
                'food_store': 12,
                'worms_store': 0,
                'color': (0, 255, 255),
                'gates': [{'x': 5, 'y': 4}, {'x': 4, 'y': 5}]
            },
            'stripes': {
                'x': 20, 'y': 14, 'w': 5, 'h': 5,
                'food_store': 12,
                'worms_store': 0,
                'color': (255, 20, 147),
                'gates': [{'x': 20, 'y': 16}, {'x': 21, 'y': 14}]
            }
        }
        
        self.gardens = {
            'spots': [{'x': 1, 'y': 7}, {'x': 2, 'y': 7}, {'x': 3, 'y': 7}],
            'stripes': [{'x': 23, 'y': 13}, {'x': 24, 'y': 13}, {'x': 25, 'y': 13}]
        }
        
        self.cultivation_unlocked = {
            'spots': False,
            'stripes': False
        }
        
        self.population_history = {
            'spots': [],
            'stripes': []
        }
        self.history_tick = 0
        
        self.greed_active = {
            'spots': False,
            'stripes': False
        }
        
        self.time_in_cycle = 0.0
        self.is_night = False
        self.zombies = []
        self.zombies_spawned = False

        self.reset_simulation()

    def reset_simulation(self):
        self.entities.clear()
        self.mushrooms.clear()
        self.worms.clear()
        self.logs.clear()
        self.history_tick = 0
        self.population_history = {'spots': [], 'stripes': []}
        
        self.time_in_cycle = 0.0
        self.is_night = False
        self.zombies = []
        self.zombies_spawned = False
        
        try:
            with open("simulation_last_run.log", "w") as f:
                f.write(f"=== Simulation Started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        except Exception as e:
            print(f"Error resetting log file: {e}")
        
        self.castles['spots']['food_store'] = 12
        self.castles['stripes']['food_store'] = 12
        self.castles['spots']['worms_store'] = 0
        self.castles['stripes']['worms_store'] = 0
        
        self.cultivation_unlocked = {'spots': False, 'stripes': False}
        self.greed_active = {'spots': False, 'stripes': False}

        # Clear gardens on map grid
        for spec in self.gardens:
            for tile in self.gardens[spec]:
                self.maze_map[tile['y']][tile['x']] = 0

        # Spawn initial adults (same as web engine)
        # Spots (Top-Left Base)
        self.spawn_pacman(2, 3, "spots", "male", 1)
        self.spawn_pacman(3, 2, "spots", "female", 1)
        self.spawn_pacman(1, 4, "spots", "male", 1)
        self.spawn_pacman(4, 1, "spots", "female", 1)

        # Stripes (Bottom-Right Base)
        self.spawn_pacman(23, 16, "stripes", "male", 1)
        self.spawn_pacman(22, 17, "stripes", "female", 1)
        self.spawn_pacman(24, 15, "stripes", "male", 1)
        self.spawn_pacman(21, 18, "stripes", "female", 1)

        # Spawn initial magic mushrooms
        for _ in range(15):
            self.spawn_random_mushroom()

        # Spawn initial worms
        for _ in range(6):
            self.spawn_wild_worm()

        self.add_log("Simulation initialized. Forest opened, worms spawned.")

    def spawn_zombies(self):
        self.zombies.clear()
        for _ in range(6):
            spawned = False
            for _ in range(100):
                rx = random.randint(0, self.width - 1)
                ry = random.randint(0, self.height - 1)
                if self.is_walkable(rx, ry) and not self.is_inside_any_castle(rx, ry):
                    too_close = False
                    for e in self.entities:
                        if not e.is_dead:
                            if self.get_distance(rx, ry, e.tile_x, e.tile_y) < 8:
                                too_close = True
                                break
                    if not too_close:
                        for spec in self.castles:
                            c = self.castles[spec]
                            if self.get_distance(rx, ry, c['x'] + 2, c['y'] + 2) < 8:
                                too_close = True
                                break
                    if not too_close or _ == 99:
                        from entity import Zombie
                        self.zombies.append(Zombie(self, rx, ry))
                        spawned = True
                        break

    def spawn_wild_worm(self):
        # Spawns a worm at a random walkable corridor inside the Forest (columns 28-45)
        for _ in range(100):
            rx = random.randint(28, 45)
            ry = random.randint(1, 19)
            if self.is_walkable(rx, ry) and not self.get_worm_at(rx, ry):
                w = Worm(self, rx, ry)
                self.worms.append(w)
                return w
        return None

    def get_worm_at(self, x, y):
        for w in self.worms:
            if w.tile_x == x and w.tile_y == y:
                return w
        return None

    def consume_worm(self, worm):
        if worm in self.worms:
            self.worms.remove(worm)

    def spawn_pacman(self, x, y, species, gender, generation, brain=None):
        p = Pacman(self, x, y, species, gender, brain, generation)
        self.entities.append(p)
        return p

    def spawn_random_mushroom(self):
        tile = self.get_random_walkable_corridor()
        if tile:
            self.spawn_mushroom_at(tile['x'], tile['y'])

    def spawn_mushroom_at(self, x, y):
        if self.get_mushroom_at(x, y):
            return
        self.mushrooms.append({
            'id': f"m_{random.randint(0, 1000000)}",
            'x': x,
            'y': y,
            'type': "wild",
            'growth_timer': 0.0
        })

    def plant_mushroom(self, x, y, species):
        self.mushrooms.append({
            'id': f"m_{random.randint(0, 1000000)}",
            'x': x,
            'y': y,
            'type': "cultivated",
            'owner': species,
            'growth_timer': 15.0 # takes 15 simulation seconds to grow
        })

    def get_mushroom_at(self, x, y):
        for m in self.mushrooms:
            if m['x'] == x and m['y'] == y:
                return m
        return None

    def consume_mushroom(self, m_id):
        self.mushrooms = [m for m in self.mushrooms if m['id'] != m_id]

    def get_home_castle(self, species):
        return self.castles[species]

    def is_inside_castle(self, x, y, species):
        c = self.castles[species]
        return c['x'] <= x < c['x'] + c['w'] and c['y'] <= y < c['y'] + c['h']

    def is_inside_any_castle(self, x, y):
        for spec in self.castles:
            if self.is_inside_castle(x, y, spec):
                return True
        return False

    def is_walkable(self, x, y, entity=None):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        if self.maze_map[y][x] == 1:
            return False

        if entity:
            is_zombie = getattr(entity, 'is_zombie', False)
            if is_zombie:
                if self.is_inside_any_castle(x, y):
                    return False
            else:
                # Night curfew: if currently inside home base at night, do not allow stepping outside
                if self.is_night:
                    currently_inside = self.is_inside_castle(entity.tile_x, entity.tile_y, entity.species)
                    target_inside = self.is_inside_castle(x, y, entity.species)
                    if currently_inside and not target_inside:
                        return False

                # If infant is currently inside home base, do not let it wander outside
                if entity.is_infant():
                    currently_inside = self.is_inside_castle(entity.tile_x, entity.tile_y, entity.species)
                    if currently_inside and not self.is_inside_castle(x, y, entity.species):
                        return False

            # Forest entrance gate check: if crossing from < 28 to >= 28
            if entity.tile_x < 28 and x >= 28:
                if not (getattr(entity, 'needs_forest_drop', False) or getattr(entity, 'hunting_worm_in_forest', False) or is_zombie):
                    return False

            # Old Pac-man blockade gates check
            is_gate = self.is_gate_tile(x, y)
            if is_gate and not is_zombie:
                defender = next((e for e in self.entities if 
                                 not e.is_dead and e.is_old() and e.tile_x == x and e.tile_y == y and e.species != entity.species), None)
                if defender:
                    return False # path blocked!

            # Adult castle base occupancy boundaries check
            if not is_zombie and entity.is_adult() and self.is_inside_castle(x, y, entity.species):
                has_food_or_worm = entity.food_carried > 0 or getattr(entity, 'has_worm', False)
                allowed = (
                    has_food_or_worm or 
                    entity.current_drive == "Mate" or 
                    (entity.current_drive == "Store" and has_food_or_worm) or
                    (entity.energy < 50 and entity.eat_cooldown == 0.0) or
                    self.is_night
                )
                currently_inside = self.is_inside_castle(entity.tile_x, entity.tile_y, entity.species)
                if not allowed and not currently_inside:
                    return False # prevent entering without reason

        return True

    def is_gate_tile(self, x, y):
        for spec in self.castles:
            c = self.castles[spec]
            for g in c['gates']:
                if g['x'] == x and g['y'] == y:
                    return True
        return False

    def get_random_walkable_corridor(self):
        for _ in range(100):
            rx = random.randint(0, 26) # Restrict to Maze corridors
            ry = random.randint(0, self.height - 1)
            if self.is_walkable(rx, ry) and not self.is_inside_any_castle(rx, ry):
                return {'x': rx, 'y': ry}
        return None

    def get_random_walkable_forest_tile(self):
        for _ in range(100):
            rx = random.randint(28, 45)
            ry = random.randint(1, self.height - 2)
            if self.is_walkable(rx, ry) and self.maze_map[ry][rx] == 0:
                return {'x': rx, 'y': ry}
        return {'x': 30, 'y': 10} # fallback

    def spawn_dropped_mushroom_at(self, x, y):
        # Check if there is already a mushroom at (x, y)
        if not self.get_mushroom_at(x, y):
            shroom_id = len(self.mushrooms) + 1
            self.mushrooms.append({
                'id': shroom_id,
                'x': x,
                'y': y,
                'type': 'wild',
                'growth_timer': 0.0
            })

    def get_random_walkable_tile(self, start_x, start_y, entity=None):
        dirs = [{'x': 0, 'y': -1}, {'x': 0, 'y': 1}, {'x': -1, 'y': 0}, {'x': 1, 'y': 0}]
        walkable = []
        for d in dirs:
            tx = start_x + d['x']
            ty = start_y + d['y']
            if self.is_walkable(tx, ty, entity):
                walkable.append({'x': tx, 'y': ty})
        if walkable:
            return random.choice(walkable)
        return {'x': start_x, 'y': start_y}

    def get_random_tile_near(self, x, y, radius):
        for _ in range(50):
            rx = x + random.randint(-radius, radius)
            ry = y + random.randint(-radius, radius)
            if self.is_walkable(rx, ry):
                return {'x': rx, 'y': ry}
        return {'x': x, 'y': y}

    def get_distance(self, x1, y1, x2, y2):
        return abs(x1 - x2) + abs(y1 - y2)

    def find_nearest_mushroom(self, x, y):
        nearest = None
        min_dist = float('inf')
        for m in self.mushrooms:
            if m['type'] == "cultivated" and m['growth_timer'] > 0:
                continue
            d = self.get_distance(x, y, m['x'], m['y'])
            if d < min_dist:
                min_dist = d
                nearest = m
        return nearest

    def find_nearest_enemy(self, x, y, self_species):
        nearest = None
        min_dist = float('inf')
        for e in self.entities:
            if e.is_dead or e.is_infant():
                continue
            is_enemy = (e.species != self_species)

            if is_enemy:
                d = self.get_distance(x, y, e.tile_x, e.tile_y)
                if d < min_dist:
                    min_dist = d
                    nearest = e
        return nearest

    def find_nearest_mate(self, self_entity):
        nearest = None
        min_dist = float('inf')
        for e in self.entities:
            if e.is_dead or not e.is_adult() or e == self_entity or e.gender == self_entity.gender:
                continue
            
            # All opposite-gender adult pairs are compatible, allowing cross-breeding
            if e.mating_cooldown == 0.0:
                d = self.get_distance(self_entity.tile_x, self_entity.tile_y, e.tile_x, e.tile_y)
                if d < min_dist:
                    min_dist = d
                    nearest = e
        return nearest

    def is_garden_soil(self, x, y, species):
        for tile in self.gardens[species]:
            if tile['x'] == x and tile['y'] == y:
                return True
        return False

    def get_free_garden_soil(self, species):
        for tile in self.gardens[species]:
            if not self.get_mushroom_at(tile['x'], tile['y']):
                return tile
        return None

    def find_path(self, start_x, start_y, end_x, end_y, entity=None):
        if start_x == end_x and start_y == end_y:
            return []
        if not self.is_walkable(end_x, end_y, entity):
            return []

        queue = [{'x': start_x, 'y': start_y, 'path': []}]
        visited = {f"{start_x},{start_y}"}
        dirs = [{'x': 0, 'y': -1}, {'x': 0, 'y': 1}, {'x': -1, 'y': 0}, {'x': 1, 'y': 0}]

        while queue:
            curr = queue.pop(0)
            if curr['x'] == end_x and curr['y'] == end_y:
                return curr['path']

            for d in dirs:
                nx = curr['x'] + d['x']
                ny = curr['y'] + d['y']
                key = f"{nx},{ny}"
                
                if key not in visited and self.is_walkable(nx, ny, entity):
                    visited.add(key)
                    new_path = list(curr['path']) + [{'x': nx, 'y': ny}]
                    queue.append({'x': nx, 'y': ny, 'path': new_path})
        return []

    def tick(self):
        if self.is_paused:
            return

        # Day / Night Cycle updates
        self.time_in_cycle += 1.0 / 60.0
        if self.time_in_cycle >= 180.0:
            self.time_in_cycle = 0.0
            
        if self.time_in_cycle >= 120.0:
            # Night time
            if not self.is_night:
                self.is_night = True
                self.zombies_spawned = False
                self.add_log("🌌 NIGHTFALL: Night has begun. Returning to base. Danger level: CRITICAL.")
            
            # 5-second zombie spawn delay: spawn when time_in_cycle reaches 125.0
            if not self.zombies_spawned and self.time_in_cycle >= 125.0:
                self.zombies_spawned = True
                self.spawn_zombies()
                self.add_log("🧟 INVASION: Zombies have entered the maze!")
        else:
            # Day time
            if self.is_night:
                self.is_night = False
                self.zombies_spawned = False
                self.zombies.clear()
                self.add_log("🌅 DAWN: Morning has arrived. Zombies have turned to dust. Begin your day.")

        # Update Zombies at Night
        if self.is_night:
            for z in list(self.zombies):
                z.update()
                
                # Check collision with pacman outside castle
                for e in list(self.entities):
                    if e.is_dead:
                        continue
                    if not self.is_inside_castle(e.tile_x, e.tile_y, e.species):
                        dx = z.x - e.x
                        dy = z.y - e.y
                        if (dx*dx + dy*dy) < 0.64: # dist < 0.8
                            e.die("Zombie Devastation")
                            self.add_log(f"🧟 ZOMBIE ATTACK: {e.name} was devoured by a zombie outside the castle!")

        # Update greed active state for each species
        for spec in ['spots', 'stripes']:
            pop = len([e for e in self.entities if not e.is_dead and e.species == spec])
            is_panic = pop < 3
            if is_panic:
                self.greed_active[spec] = False
            else:
                if pop > 10:
                    if not self.greed_active[spec]:
                        self.greed_active[spec] = True
                        self.add_log(f"🔥 GREED: {spec} population exceeded 10! Greed sets in.")
                elif pop <= 5:
                    if self.greed_active[spec]:
                        self.greed_active[spec] = False
                        self.add_log(f"🍃 GREED OVER: {spec} population dropped to 5 or below. Greed decayed.")

        # A. Update entities
        for e in self.entities:
            e.update()

        # Update worms
        for w in self.worms:
            w.update()

        # Check continuous worm collision catching
        for e in self.entities:
            if e.is_dead or e.current_drive != "Forage" or getattr(e, 'has_worm', False) or e.food_carried > 0:
                continue
            for w in list(self.worms):
                dx = e.x - w.x
                dy = e.y - w.y
                if (dx*dx + dy*dy) < 0.64: # 0.8 tile radius collision
                    self.consume_worm(w)
                    e.hunting_worm_in_forest = False
                    if e.energy < 80 and e.worm_eat_cooldown == 0.0:
                        e.age = max(0.0, e.age - 0.20 * self.life_expectancy)
                        e.energy = min(100.0, e.energy + 40.0)
                        e.worm_eat_cooldown = 300.0
                        e.fitness += 3
                        e.thought = "Ate a fresh worm! I feel 20% younger!"
                        self.add_log(f"🧬 REJUVENATION: {e.name} ate a wild worm (5m digestion cooldown started).")
                    else:
                        e.has_worm = True
                        e.thought = "Caught a worm! Carrying it back to the castle."
                        self.add_log(f"🪱 HUNT: {e.name} caught a worm and is bringing it back.")
                    break

        # Worms eat dropped mushrooms in the forest
        for w in list(self.worms):
            shroom = self.get_mushroom_at(w.tile_x, w.tile_y)
            if shroom and w.tile_x >= 28:
                self.consume_mushroom(shroom['id'])
                self.add_log(f"🪱 FEED: A worm ate a dropped mushroom at ({w.tile_x}, {w.tile_y}).")

        # B. Filter deceased
        self.entities = [e for e in self.entities if not e.is_dead]

        # C. Update cultivated mushrooms growth timer
        for m in self.mushrooms:
            if m['type'] == "cultivated" and m['growth_timer'] > 0:
                m['growth_timer'] = max(0.0, m['growth_timer'] - 1.0 / 60.0)

        # D. Spawn wild food if scarce
        wild_count = len([m for m in self.mushrooms if m['type'] == "wild"])
        if wild_count < 12 and random.random() < 0.08:
            self.spawn_random_mushroom()

        # Spawn wild worms in the forest if scarce
        if len(self.worms) < 5 and random.random() < 0.05:
            self.spawn_wild_worm()

        # E. Process Fights/Mating/Mentoring
        self.handle_global_interactions()

        # F. Check Agriculture eras
        self.check_castle_rules()

        # G. Record Population curves
        self.history_tick += 1
        if self.history_tick % 100 == 0:
            self.record_population_history()

    def handle_global_interactions(self):
        entities_copy = list(self.entities)
        length = len(entities_copy)

        for i in range(length):
            e1 = entities_copy[i]
            if e1.is_dead:
                continue

            for j in range(i + 1, length):
                e2 = entities_copy[j]
                if e2.is_dead:
                    continue

                dist = self.get_distance(e1.tile_x, e1.tile_y, e2.tile_x, e2.tile_y)
                if dist <= 1:
                    # 1. Mentoring and Baby Pickup
                    if e1.species == e2.species and ((e1.is_adult() and e2.is_infant()) or (e1.is_infant() and e2.is_adult())):
                        adult = e1 if e1.is_adult() else e2
                        infant = e1 if e1.is_infant() else e2
                        
                        # Standard Mentoring
                        if adult.mentor_cooldown == 0.0 and infant.mentor_cooldown == 0.0:
                            self.mentor_infant(adult, infant)
                        
                        # Baby Pickup: if the infant is outside the castle and not already carried
                        if (getattr(adult, 'carrying_baby', None) is None and 
                            getattr(infant, 'carried_by', None) is None and 
                            not self.is_inside_castle(infant.tile_x, infant.tile_y, infant.species)):
                            adult.carrying_baby = infant
                            infant.carried_by = adult
                            self.add_log(f"🍼 RESCUE: {adult.name} picked up infant {infant.name} to carry them to safety.")

                    # 2. Mating Instinct / Combat Resolves
                    # Panic breeding / Mating instinct overrides
                    mated_successfully = False
                    is_opposite_gender = e1.gender != e2.gender
                    if is_opposite_gender:
                        male = e1 if e1.gender == "male" else e2
                        female = e1 if e1.gender == "female" else e2
                        
                        if male.mating_cooldown == 0.0 and female.mating_cooldown == 0.0:
                            # A. Check female panic
                            own_fem_pop = len([e for e in self.entities if not e.is_dead and e.species == female.species])
                            if own_fem_pop < 3 and female.is_adult():
                                own_males = [e for e in self.entities if not e.is_dead and e.species == female.species and e.gender == "male" and e.is_adult()]
                                if len(own_males) == 0:
                                    # Mating with senior male of own species
                                    if male.species == female.species and male.is_old():
                                        if self.perform_breeding(male, female, is_cross=False):
                                            self.add_log(f"👵 PANIC SENIOR BREED: Female {female.name} mated with senior {male.name} to save colony!")
                                            mated_successfully = True
                                    # Mating with rival male fallback
                                    elif male.species != female.species and male.is_adult():
                                        if self.perform_breeding(male, female, is_cross=True):
                                            self.add_log(f"💔 PANIC RIVAL BREED: Female {female.name} mated with rival male {male.name}!")
                                            mated_successfully = True
                            
                            # B. Check male panic (Courtship Gift)
                            if not mated_successfully:
                                own_male_pop = len([e for e in self.entities if not e.is_dead and e.species == male.species])
                                if own_male_pop < 3 and male.is_adult():
                                    if male.food_carried > 0 and female.species != male.species and female.is_adult():
                                        if self.perform_breeding(male, female, is_cross=True):
                                            male.food_carried -= 1
                                            self.add_log(f"🎁 PANIC COURTSHIP: Male {male.name} gifted a mushroom to rival female {female.name} and mated!")
                                            mated_successfully = True

                            # C. Virgin mating instinct override
                            if not mated_successfully and male.is_adult() and female.is_adult() and (male.offspring_count == 0 or female.offspring_count == 0):
                                if self.perform_breeding(male, female, male.species != female.species):
                                    mated_successfully = True

                    if mated_successfully:
                        continue # bypass combat logic

                    # 3. Rival adult kills enemy infant check
                    if e1.species != e2.species:
                        adult = e1 if (e1.is_adult() or e1.is_old()) else None
                        infant = e2 if e2.is_infant() else None
                        if not adult or not infant:
                            adult = e2 if (e2.is_adult() or e2.is_old()) else None
                            infant = e1 if e1.is_infant() else None
                        
                        if adult and infant and not infant.is_dead:
                            is_greedy = self.greed_active.get(adult.species, False) and adult.is_adult()
                            is_outside = not self.is_inside_castle(infant.tile_x, infant.tile_y, infant.species)
                            is_std_kill = adult.gender != "female" and is_outside
                            
                            if (is_greedy or is_std_kill) and getattr(infant, 'carried_by', None) is None:
                                # Check for parent protection within 2 tiles
                                parent = None
                                for p_cand in [getattr(infant, 'mother', None), getattr(infant, 'father', None)]:
                                    if p_cand and not p_cand.is_dead:
                                        d = self.get_distance(infant.tile_x, infant.tile_y, p_cand.tile_x, p_cand.tile_y)
                                        if d <= 2:
                                            parent = p_cand
                                            break
                                
                                if parent:
                                    # Vicious parent protective combat (80% parent wins)
                                    if random.random() < 0.8:
                                        # Parent wins
                                        adult.die(f"Killed by protecting parent {parent.name}")
                                        self.add_log(f"🛡️ PROTECT: Parent {parent.name} defended baby {infant.name} & killed intruder {adult.name}!")
                                    else:
                                        # Parent loses
                                        parent.die(f"Felled protecting baby from {adult.name}")
                                        infant.die(f"Killed by intruder {adult.name}")
                                        self.add_log(f"☠️ PROTECT FAIL: Parent {parent.name} fell defending baby {infant.name} against {adult.name}!")
                                else:
                                    # Infant killed unprotected
                                    infant.die(f"Killed by rival {adult.name}")
                                    self.add_log(f"⚔️ INFANT FALL: Infant {infant.name} was killed by rival adult {adult.name} (unprotected).")
                                continue

                    # Standard combat check
                    animosity = False
                    # Females do not engage in combat
                    if e1.gender != "female" and e2.gender != "female":
                        if e1.species != e2.species:
                            animosity = True

                    if animosity:
                        if (e1.is_adult() and e2.is_adult()) or (e1.is_adult() and e2.is_old()) or (e2.is_adult() and e1.is_old()):
                            self.resolve_combat(e1, e2)

                    # Standard breeding check
                    if e1.gender != e2.gender:
                        male = e1 if e1.gender == "male" else e2
                        female = e1 if e1.gender == "female" else e2
                        if male.is_adult() and female.is_adult() and male.mating_cooldown == 0.0 and female.mating_cooldown == 0.0:
                            if male.current_drive == "Mate" and female.current_drive == "Mate":
                                self.perform_breeding(male, female, male.species != female.species)

    def resolve_combat(self, e1, e2):
        if e1.is_old() and e2.is_adult():
            e1.energy -= 18.0
            e2.energy -= 6.0
            e2.fitness += 1
            e1.thought = "Ouch! Defending our gates, stalling the attackers!"
            if e1.energy <= 0:
                e1.die("Defending base gates")
                self.add_log(f"🛡️ DEFENSE: Old {e1.name} fell defending the gate against {e2.name}.")
            return
        
        if e2.is_old() and e1.is_adult():
            e2.energy -= 18.0
            e1.energy -= 6.0
            e1.fitness += 1
            e2.thought = "Stalling enemy invasion!"
            if e2.energy <= 0:
                e2.die("Defending base gates")
                self.add_log(f"🛡️ DEFENSE: Old {e2.name} fell defending the gate against {e1.name}.")
            return

        # Adult vs Adult fight probabilities
        win_prob1 = 0.5 + (e1.glow_intensity - e2.glow_intensity) * 0.3
        winner, loser = (e1, e2) if random.random() < win_prob1 else (e2, e1)

        winner.fitness += 4
        winner.energy = max(20.0, winner.energy - 15.0)
        winner.thought = f"I defeated {loser.name} in combat!"
        
        loser.die(f"Combat defeat by {winner.name}")
        self.add_log(f"⚔️ COMBAT: {winner.name} ({winner.species}) defeated and killed {loser.name} ({loser.species})")

    def perform_breeding(self, male, female, is_cross):
        # Allow unlimited offspring when either species is in panic mode (< 3 population) to prevent extinction
        pop_male = len([e for e in self.entities if not e.is_dead and e.species == male.species])
        pop_female = len([e for e in self.entities if not e.is_dead and e.species == female.species])
        is_panic = (pop_male < 3) or (pop_female < 3)
        
        if not is_panic:
            if male.offspring_count >= 2 or female.offspring_count >= 2:
                return False

        male.energy = max(10.0, male.energy - 35.0)
        female.energy = max(10.0, female.energy - 35.0)
        
        male.mating_cooldown = 20.0 # 20 seconds cooldown
        female.mating_cooldown = 20.0
        
        male.offspring_count += 1
        female.offspring_count += 1
        
        male.fitness += 2
        female.fitness += 2

        # Crossover & mutation in PyTorch
        baby_brain = Brain.crossover(male.brain, female.brain).mutate(0.15)
        
        # Offspring species determination
        baby_species = male.species
        if is_cross:
            spots_count = len([e for e in self.entities if not e.is_dead and e.species == "spots"])
            stripes_count = len([e for e in self.entities if not e.is_dead and e.species == "stripes"])
            if stripes_count < spots_count:
                baby_species = "stripes"
            elif spots_count < stripes_count:
                baby_species = "spots"
            else:
                baby_species = random.choice(["spots", "stripes"])

        baby_gender = "male" if random.random() < 0.5 else "female"

        bx, by = female.tile_x, female.tile_y
        self.add_log(f"👶 BIRTH: {male.name} ({male.species}) & {female.name} ({female.species}) had a baby named {baby_gender} in {baby_species} colony.")

        baby = self.spawn_pacman(bx, by, baby_species, baby_gender, max(male.generation, female.generation) + 1, baby_brain)
        baby.age = 0.0
        baby.energy = 90.0
        baby.father = male
        baby.mother = female
        return True

    def mentor_infant(self, adult, infant):
        adult.mentor_cooldown = 15.0
        infant.mentor_cooldown = 15.0

        # Blend neural parameters
        # Weights reside on GPU/MPS device, PyTorch operations naturally accelerate this
        with torch.no_grad():
            infant.brain.w1 = infant.brain.w1 * 0.85 + adult.brain.w1 * 0.15
            infant.brain.w2 = infant.brain.w2 * 0.85 + adult.brain.w2 * 0.15

        adult.fitness += 1
        adult.thought = f"Teaching {infant.name} how to survive and forage."
        infant.thought = f"Mentored by {adult.name}! Feeling wiser."

        if infant.energy < 40 and adult.food_carried > 0:
            adult.food_carried -= 1
            infant.energy = min(100.0, infant.energy + 40.0)
            infant.thought = f"Ate food hand-delivered by mentor {adult.name}!"

    def check_castle_rules(self):
        for spec in self.castles:
            castle = self.castles[spec]
            if not self.cultivation_unlocked[spec] and castle['food_store'] >= 20:
                self.cultivation_unlocked[spec] = True
                self.add_log(f"🎓 AGRARIAN ERA: The {spec} species has invented Agricultural Cultivation! Gardens unlocked.")

    def record_population_history(self):
        counts = {'spots': 0, 'stripes': 0}
        for e in self.entities:
            if not e.is_dead:
                counts[e.species] += 1
        
        self.population_history['spots'].append(counts['spots'])
        self.population_history['stripes'].append(counts['stripes'])

        # Keep last 30 readings
        for spec in self.population_history:
            if len(self.population_history[spec]) > 30:
                self.population_history[spec].pop(0)

    def add_log(self, message):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.logs.insert(0, f"[{time_str}] {message}")
        if len(self.logs) > 40:
            self.logs.pop()
        
        log_line = f"[{time_str}] {message}"
        print(log_line)
        try:
            with open("simulation_last_run.log", "a") as f:
                f.write(log_line + "\n")
        except Exception as e:
            pass

    def find_intruder_threatening_female(self, self_entity):
        # Enforces: pacman needs to protect their female from intruding male.
        # An intruder is a male of a DIFFERENT species within 3 tiles of one of our females.
        for female in self.entities:
            if female.is_dead or female.gender != "female" or female.species != self_entity.species:
                continue
            
            # Check if there is an enemy male close to her (dist <= 3)
            for enemy_male in self.entities:
                if (enemy_male.is_dead or 
                    enemy_male.gender != "male" or 
                    enemy_male.species == self_entity.species):
                    continue
                
                d = self.get_distance(female.tile_x, female.tile_y, enemy_male.tile_x, enemy_male.tile_y)
                if d <= 3:
                    # Found threatening rival male!
                    return enemy_male
        return None
