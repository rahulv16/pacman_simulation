import pygame
import math
import numpy as np

# Color Definitions
COLOR_BG_MAIN = (6, 8, 19)
COLOR_BG_CARD = (15, 22, 42)
COLOR_BORDER = (35, 45, 75)
COLOR_TEXT_PRIMARY = (248, 250, 252)
COLOR_TEXT_SECONDARY = (148, 163, 184)
COLOR_TEXT_MUTED = (100, 116, 139)
COLOR_ACCENT_CYAN = (56, 189, 248)

COLOR_SPOTS = (0, 255, 255)
COLOR_STRIPES = (255, 20, 147)
COLOR_HYBRID = (0, 255, 0)
COLOR_FOOD = (200, 255, 0)
COLOR_INFANT = (255, 0, 0)
COLOR_OLD = (230, 230, 230)

class SimulationUI:
    """
    Pygame UI Renderer. Handles vector drawings for entities, symmetric grids,
    population charts, system logger, and visual neural brain synapse paths.
    """
    def __init__(self, world, screen):
        self.world = world
        self.screen = screen
        
        # Determine dynamic dimensions based on actual screen size
        screen_w, screen_h = screen.get_size()
        sidebar_min_w = 400
        
        max_tile_w = (screen_w - sidebar_min_w) // world.width
        max_tile_h = screen_h // world.height
        self.tile_size = max(12, min(max_tile_w, max_tile_h))
        
        self.viewport_w = world.width * self.tile_size
        self.viewport_h = world.height * self.tile_size
        self.sidebar_w = screen_w - self.viewport_w
        self.y_offset = (screen_h - self.viewport_h) // 2
        
        # Fonts
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Helvetica", 18, bold=True)
        self.font_header = pygame.font.SysFont("Helvetica", 14, bold=True)
        self.font_body = pygame.font.SysFont("Helvetica", 12)
        self.font_small = pygame.font.SysFont("Helvetica", 10)
        self.font_mono = pygame.font.SysFont("Courier", 11)

    def draw(self, selected_pacman=None):
        # 1. Clear Screen
        self.screen.fill(COLOR_BG_MAIN)

        # 2. Draw Simulation Viewport (Left)
        self.draw_viewport()

        # 3. Draw Sidebar Panel (Right)
        self.draw_sidebar(selected_pacman)

    def draw_viewport(self):
        # A. Draw corridors and walls
        for y in range(self.world.height):
            for x in range(self.world.width):
                cell = self.world.maze_map[y][x]
                px = x * self.tile_size
                py = y * self.tile_size + self.y_offset
                
                is_forest = (x >= 28)
                is_separator = (x == 27)
                
                if cell == 1:
                    if is_forest:
                        # Draw tree obstacle: grass background
                        pygame.draw.rect(self.screen, (16, 44, 22), (px, py, self.tile_size, self.tile_size))
                        cx = px + self.tile_size // 2
                        cy = py + self.tile_size // 2
                        # Trunk
                        pygame.draw.rect(self.screen, (100, 70, 40), (cx - 2, cy, 4, self.tile_size // 2))
                        # Leaves
                        pygame.draw.circle(self.screen, (34, 139, 34), (cx, cy - 2), 6)
                    elif is_separator:
                        # Gold tech separator wall
                        pygame.draw.rect(self.screen, (180, 140, 20), (px + 1, py + 1, self.tile_size - 2, self.tile_size - 2))
                        pygame.draw.rect(self.screen, (220, 180, 40), (px, py, self.tile_size, self.tile_size), 1)
                    else:
                        # Wall: Dark Slate tech look
                        pygame.draw.rect(self.screen, (30, 41, 59), (px + 1, py + 1, self.tile_size - 2, self.tile_size - 2))
                        pygame.draw.rect(self.screen, (71, 85, 105), (px, py, self.tile_size, self.tile_size), 1)
                else:
                    if is_forest:
                        # Grass walkable field
                        pygame.draw.rect(self.screen, (16, 44, 22), (px, py, self.tile_size, self.tile_size))
                    else:
                        # Walkable corridor
                        pygame.draw.rect(self.screen, (3, 7, 18), (px, py, self.tile_size, self.tile_size))

        # B. Draw Castle Base Areas
        for species, c in self.world.castles.items():
            cx = c['x'] * self.tile_size
            cy = c['y'] * self.tile_size + self.y_offset
            cw = c['w'] * self.tile_size
            ch = c['h'] * self.tile_size
            
            # semi-transparent base filling (simulate alpha manually since Pygame handles transparency via separate surfaces)
            base_surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            alpha_color = c['color'] + (35,) # append 35 alpha
            base_surf.fill(alpha_color)
            self.screen.blit(base_surf, (cx, cy))
            
            # draw borders
            pygame.draw.rect(self.screen, c['color'], (cx, cy, cw, ch), 2)
            
            # Draw gates
            for gate in c['gates']:
                gx = gate['x'] * self.tile_size
                gy = gate['y'] * self.tile_size + self.y_offset
                pygame.draw.rect(self.screen, c['color'], (gx + 2, gy + 2, self.tile_size - 4, self.tile_size - 4))

        # C. Draw Gardens
        for species, gardens in self.world.gardens.items():
            unlocked = self.world.cultivation_unlocked[species]
            color = (16, 185, 129) if unlocked else (100, 116, 139)
            for tile in gardens:
                tx = tile['x'] * self.tile_size
                ty = tile['y'] * self.tile_size + self.y_offset
                
                soil_surf = pygame.Surface((self.tile_size - 4, self.tile_size - 4), pygame.SRCALPHA)
                soil_surf.fill(color + (30 if unlocked else 10,))
                self.screen.blit(soil_surf, (tx + 2, ty + 2))
                pygame.draw.rect(self.screen, color, (tx + 2, ty + 2, self.tile_size - 4, self.tile_size - 4), 1)

        # Draw Night Overlay
        if self.world.is_night:
            night_surf = pygame.Surface((self.viewport_w, self.viewport_h), pygame.SRCALPHA)
            night_surf.fill((10, 10, 35, 130)) # dark navy blue with alpha 130
            self.screen.blit(night_surf, (0, self.y_offset))

        # D. Draw Mushrooms (Food)
        for m in self.world.mushrooms:
            mx = m['x'] * self.tile_size + self.tile_size // 2
            my = m['y'] * self.tile_size + self.tile_size // 2 + self.y_offset
            
            if m['type'] == "wild":
                color = COLOR_FOOD
                # Draw cap
                pygame.draw.circle(self.screen, color, (mx, my - 2), 6, draw_top_left=True, draw_top_right=True)
                # Draw stem
                pygame.draw.rect(self.screen, (200, 200, 200), (mx - 2, my - 2, 4, 7))
            else:
                # Cultivated
                if m['growth_timer'] > 0:
                    # Sprout
                    pygame.draw.circle(self.screen, (16, 185, 129), (mx, my + 2), 3)
                else:
                    # Mature
                    pygame.draw.circle(self.screen, COLOR_HYBRID, (mx, my - 2), 6, draw_top_left=True, draw_top_right=True)
                    pygame.draw.rect(self.screen, (150, 150, 150), (mx - 2, my - 2, 4, 7))

        # Draw Worms (Prey)
        for w in self.world.worms:
            wx = int(w.x * self.tile_size + self.tile_size // 2)
            wy = int(w.y * self.tile_size + self.tile_size // 2) + self.y_offset
            
            wiggle = math.sin(w.wiggling_offset) * 3
            pygame.draw.circle(self.screen, (244, 143, 177), (wx, wy), 4) # Head
            pygame.draw.circle(self.screen, (240, 98, 146), (wx - 4, int(wy + wiggle)), 3) # Body
            pygame.draw.circle(self.screen, (233, 30, 99), (wx - 8, int(wy - wiggle)), 2) # Tail

        # E. Draw Path Guides (for selected debugging)
        if self.world.show_path_guide:
            for e in self.world.entities:
                if e.current_path:
                    points = [(e.x * self.tile_size + self.tile_size//2, e.y * self.tile_size + self.tile_size//2 + self.y_offset)]
                    for p in e.current_path:
                        points.append((p['x'] * self.tile_size + self.tile_size//2, p['y'] * self.tile_size + self.tile_size//2 + self.y_offset))
                    
                    color = COLOR_SPOTS if e.species == "spots" else COLOR_STRIPES
                    if len(points) >= 2:
                        pygame.draw.lines(self.screen, color + (80,), False, points, 2)

        # F. Draw Pac-Man Entities
        for e in self.world.entities:
            ex = int(e.x * self.tile_size + self.tile_size // 2)
            ey = int(e.y * self.tile_size + self.tile_size // 2) + self.y_offset
            rad = 9

            # Base skin color by age/gender
            skin_color = COLOR_OLD
            if e.is_infant():
                skin_color = COLOR_INFANT
            elif e.is_adult():
                if e.gender == "male":
                    skin_color = (255, 246, 85) if e.glow_intensity > 0.65 else (234, 179, 8)
                else:
                    skin_color = (255, 136, 204) if e.glow_intensity > 0.65 else (236, 72, 153)
            elif e.is_old():
                skin_color = (255, 255, 255)

            # Draw glowing circles
            if e.glow_intensity > 0:
                glow_rad = int(rad + e.glow_intensity * 6)
                glow_color = COLOR_SPOTS if e.species == "spots" else COLOR_STRIPES
                
                glow_surf = pygame.Surface((glow_rad * 2, glow_rad * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, glow_color + (40,), (glow_rad, glow_rad), glow_rad)
                self.screen.blit(glow_surf, (ex - glow_rad, ey - glow_rad))

            # Draw body (mouth arc)
            pygame.draw.circle(self.screen, skin_color, (ex, ey), rad)
            # Draw mouth cut
            pygame.draw.polygon(self.screen, (3, 7, 18), [
                (ex, ey), 
                (ex + int(rad * math.cos(0.2 * math.pi)), ey - int(rad * math.sin(0.2 * math.pi))),
                (ex + int(rad * math.cos(-0.2 * math.pi)), ey - int(rad * math.sin(-0.2 * math.pi)))
            ])

            # Draw eyes
            pygame.draw.circle(self.screen, (0, 0, 0), (ex + 1, ey - 4), 2)

            # Draw patterns
            if e.species == "spots":
                spots_coords = [(-4, 1), (-1, 4), (-3, -2)]
                for dx, dy in spots_coords:
                    pygame.draw.circle(self.screen, COLOR_SPOTS, (ex + dx, ey + dy), 2)
                    pygame.draw.circle(self.screen, (0, 0, 0), (ex + dx, ey + dy), 2, 1)

            elif e.species == "stripes":
                # Stripe 1
                pygame.draw.line(self.screen, COLOR_STRIPES, (ex - 6, ey - 1), (ex - 2, ey + 4), 2)
                # Stripe 2
                pygame.draw.line(self.screen, COLOR_STRIPES, (ex - 4, ey - 4), (ex + 1, ey + 2), 2)

            # Draw carried food/baby indicator (green dot for mushroom, pink dot for worm, red dot for baby)
            if getattr(e, 'carrying_baby', None) is not None:
                pygame.draw.circle(self.screen, COLOR_INFANT, (ex - 7, ey + 2), 4)
            if getattr(e, 'has_worm', False):
                pygame.draw.circle(self.screen, (244, 143, 177), (ex + 7, ey + 2), 4)
            elif e.food_carried > 0:
                pygame.draw.circle(self.screen, COLOR_FOOD, (ex + 7, ey + 2), 4)

        # G. Draw Zombies (Prey/Predator at Night)
        if self.world.is_night:
            for z in self.world.zombies:
                zx = int(z.x * self.tile_size + self.tile_size // 2)
                zy = int(z.y * self.tile_size + self.tile_size // 2) + self.y_offset
                rad = 9
                
                # Glowing green effect
                glow_rad = rad + 5
                glow_surf = pygame.Surface((glow_rad * 2, glow_rad * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (34, 197, 94, 50), (glow_rad, glow_rad), glow_rad) # Translucent green glow
                self.screen.blit(glow_surf, (zx - glow_rad, zy - glow_rad))
                
                # Main body: Vibrant green
                pygame.draw.circle(self.screen, (34, 197, 94), (zx, zy), rad)
                
                # Red eyes
                pygame.draw.circle(self.screen, (239, 68, 68), (zx - 3, zy - 3), 2)
                pygame.draw.circle(self.screen, (239, 68, 68), (zx + 3, zy - 3), 2)
                
                # Angry eyebrow lines
                pygame.draw.line(self.screen, (0, 0, 0), (zx - 5, zy - 6), (zx - 1, zy - 4), 1)
                pygame.draw.line(self.screen, (0, 0, 0), (zx + 5, zy - 6), (zx + 1, zy - 4), 1)
                
                # Zombie decay mouth
                pygame.draw.rect(self.screen, (0, 0, 0), (zx - 3, zy + 2, 6, 3))

    def draw_sidebar(self, selected_pacman=None):
        # Coordinates for sidebar elements
        start_x = self.viewport_w
        screen_h = self.screen.get_height()
        pygame.draw.rect(self.screen, COLOR_BG_CARD, (start_x, 0, self.sidebar_w, screen_h))
        pygame.draw.line(self.screen, COLOR_BORDER, (start_x, 0), (start_x, screen_h), 2)

        y_offset = 12

        # A. Title Section
        title_surf = self.font_title.render("A-Life Pac-Man Simulation", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(title_surf, (start_x + 16, y_offset))
        y_offset += 24

        # B. Statistics Section
        stat_header = self.font_header.render("WORLD STATISTICS", True, COLOR_TEXT_SECONDARY)
        self.screen.blit(stat_header, (start_x + 16, y_offset))
        y_offset += 18

        # Day/Night HUD timer
        if self.world.is_night:
            remaining = int(180.0 - self.world.time_in_cycle)
            cycle_text = f"Cycle Phase: NIGHT 🌌 (Zombies active!)"
            timer_text = f"Time Remaining: {remaining}s"
            timer_color = (239, 68, 68) # Red alert color
        else:
            remaining = int(120.0 - self.world.time_in_cycle)
            cycle_text = f"Cycle Phase: DAY 🌅"
            timer_text = f"Time Remaining: {remaining}s"
            timer_color = (250, 204, 21) # Yellow sun color

        phase_surf = self.font_body.render(cycle_text, True, timer_color)
        self.screen.blit(phase_surf, (start_x + 20, y_offset))
        y_offset += 16
        timer_surf = self.font_body.render(timer_text, True, COLOR_TEXT_SECONDARY)
        self.screen.blit(timer_surf, (start_x + 20, y_offset))
        y_offset += 18

        # Population figures
        counts = {'spots': 0, 'stripes': 0}
        for e in self.world.entities:
            counts[e.species] += 1

        stats_text = [
            (f"Spots Species: {counts['spots']}", COLOR_SPOTS),
            (f"Stripes Species: {counts['stripes']}", COLOR_STRIPES),
            (f"Active Mushrooms: {len(self.world.mushrooms)}", COLOR_FOOD)
        ]

        for txt, color in stats_text:
            text_surf = self.font_body.render(txt, True, color)
            self.screen.blit(text_surf, (start_x + 20, y_offset))
            y_offset += 16

        # C. Castle Reserves
        y_offset += 6
        castle_header = self.font_header.render("CASTLE RESERVES", True, COLOR_TEXT_SECONDARY)
        self.screen.blit(castle_header, (start_x + 16, y_offset))
        y_offset += 18

        for spec in ['spots', 'stripes']:
            c = self.world.castles[spec]
            label_surf = self.font_body.render(f"{spec.capitalize()} Food: {c['food_store']} | Worms: {c.get('worms_store', 0)}", True, c['color'])
            self.screen.blit(label_surf, (start_x + 20, y_offset))
            
            # Progress bar
            bar_w = 120
            bar_h = 6
            bar_x = start_x + 220
            pygame.draw.rect(self.screen, (40, 40, 40), (bar_x, y_offset + 4, bar_w, bar_h))
            
            fill_w = int(min(1.0, c['food_store'] / 30.0) * bar_w)
            if fill_w > 0:
                pygame.draw.rect(self.screen, c['color'], (bar_x, y_offset + 4, fill_w, bar_h))
            y_offset += 18

        # D. Custom Population Graph
        y_offset += 6
        chart_header = self.font_header.render("POPULATION HISTORY", True, COLOR_TEXT_SECONDARY)
        self.screen.blit(chart_header, (start_x + 16, y_offset))
        y_offset += 18
        self.draw_pygame_chart(start_x + 16, y_offset, self.sidebar_w - 32, 70)
        y_offset += 80

        # E. Pacman Inspector Section
        pygame.draw.line(self.screen, COLOR_BORDER, (start_x, y_offset), (start_x + self.sidebar_w, y_offset), 1)
        y_offset += 10
        
        if not selected_pacman:
            # Placeholder text
            ph_title = self.font_header.render("PAC-MAN INSPECTOR", True, COLOR_TEXT_SECONDARY)
            self.screen.blit(ph_title, (start_x + 16, y_offset))
            y_offset += 20
            ph_surf = self.font_body.render("Click on any Pac-Man on the grid", True, COLOR_TEXT_MUTED)
            self.screen.blit(ph_surf, (start_x + 24, y_offset))
            y_offset += 16
            ph_surf2 = self.font_body.render("to inspect its neural brain & thoughts.", True, COLOR_TEXT_MUTED)
            self.screen.blit(ph_surf2, (start_x + 24, y_offset))
            y_offset += 24
        else:
            # Inspector content
            self.draw_inspector_details(selected_pacman, start_x + 16, y_offset)
            y_offset += 260

        # F. System Console Log Overlay (Bottom Sidebar)
        pygame.draw.line(self.screen, COLOR_BORDER, (start_x, y_offset), (start_x + self.sidebar_w, y_offset), 1)
        y_offset += 8
        log_header = self.font_header.render("SYSTEM EVENTS LOG", True, COLOR_ACCENT_CYAN)
        self.screen.blit(log_header, (start_x + 16, y_offset))
        y_offset += 16

        log_h = screen_h - y_offset - 8
        self.draw_console_logs(start_x + 16, y_offset, self.sidebar_w - 32, log_h)

    def draw_pygame_chart(self, x, y, w, h):
        pygame.draw.rect(self.screen, (3, 7, 18), (x, y, w, h))
        pygame.draw.rect(self.screen, COLOR_BORDER, (x, y, w, h), 1)

        history = self.world.population_history
        if not history['spots'] or len(history['spots']) < 2:
            lbl = self.font_small.render("Timeline recording in progress...", True, COLOR_TEXT_MUTED)
            self.screen.blit(lbl, (x + w//2 - lbl.get_width()//2, y + h//2 - lbl.get_height()//2))
            return

        points_count = len(history['spots'])
        
        # Max value for axis scaling
        max_val = 5
        for spec in ['spots', 'stripes']:
            max_val = max(max_val, max(history[spec]))
        max_val = int(max_val * 1.15) # offset

        # Draw lines helper
        def draw_curve(data, color):
            pts = []
            for i in range(len(data)):
                lx = x + (i / (points_count - 1)) * w
                ly = y + h - (data[i] / max_val) * h
                pts.append((lx, ly))
            if len(pts) >= 2:
                pygame.draw.lines(self.screen, color, False, pts, 2)

        draw_curve(history['spots'], COLOR_SPOTS)
        draw_curve(history['stripes'], COLOR_STRIPES)

    def draw_inspector_details(self, e, x, y):
        # Draw Name
        gender_icon = "Male (M)" if e.gender == "male" else "Female (F)"
        spec_color = COLOR_SPOTS if e.species == "spots" else COLOR_STRIPES
        
        name_surf = self.font_header.render(f"{e.name} ({gender_icon})", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(name_surf, (x, y))
        
        spec_surf = self.font_small.render(f"SPECIES: {e.species.upper()} | GEN: {e.generation}", True, spec_color)
        self.screen.blit(spec_surf, (x + 210, y + 3))
        y += 18

        # Lifecycle age stages
        stage = "Adult"
        if e.is_infant():
            stage = "Infant (Young)"
        elif e.is_old():
            stage = "Old (Defender)"

        total_secs = int(e.age)
        mins = total_secs // 60
        secs = total_secs % 60
        
        exp_secs = int(self.world.life_expectancy)
        exp_mins = exp_secs // 60
        exp_sec = exp_secs % 60

        life_text = f"Age: {mins:02d}:{secs:02d} / {exp_mins:02d}:{exp_sec:02d} [{stage}]"
        life_surf = self.font_body.render(life_text, True, COLOR_TEXT_SECONDARY)
        self.screen.blit(life_surf, (x, y))
        y += 15

        # Progress bar age
        bar_w = 340
        pygame.draw.rect(self.screen, (40, 40, 40), (x, y, bar_w, 5))
        life_perc = e.age / self.world.life_expectancy
        pygame.draw.rect(self.screen, COLOR_ACCENT_CYAN, (x, y, int(life_perc * bar_w), 5))
        y += 10

        # Energy & Fitness & Digestion
        digest_text = ""
        if e.is_adult() and e.eat_cooldown > 0:
            digest_text = f" | Digesting: {int(e.eat_cooldown)}s"
        worm_cooldown = getattr(e, 'worm_eat_cooldown', 0.0)
        if worm_cooldown > 0:
            digest_text += f" | Worm CD: {int(worm_cooldown)}s"

        stats_text = f"Energy: {int(e.energy)}% | Fitness: {e.fitness}{digest_text}"
        stats_surf = self.font_body.render(stats_text, True, COLOR_TEXT_SECONDARY)
        self.screen.blit(stats_surf, (x, y))
        y += 15

        # Progress bar energy
        pygame.draw.rect(self.screen, (40, 40, 40), (x, y, bar_w, 5))
        pygame.draw.rect(self.screen, COLOR_FOOD, (x, y, int((e.energy/100.0) * bar_w), 5))
        y += 12

        # Thoughts Stream bubble
        pygame.draw.rect(self.screen, (5, 10, 22), (x, y, bar_w, 40))
        pygame.draw.rect(self.screen, COLOR_BORDER, (x, y, bar_w, 40), 1)
        
        thought_lines = self.wrap_text(f"Thought: \"{e.thought}\"", self.font_mono, bar_w - 16)
        ty_offset = 4
        for line in thought_lines[:3]:
            thought_surf = self.font_mono.render(line, True, (167, 243, 208))
            self.screen.blit(thought_surf, (x + 8, y + ty_offset))
            ty_offset += 12
        y += 45

        # Renders the Neural Network brain visualizer
        brain_title = self.font_small.render("🧠 NEURAL BRAIN SYLLABLE GRAPH", True, COLOR_TEXT_SECONDARY)
        self.screen.blit(brain_title, (x, y))
        y += 14
        self.draw_neural_brain(e, x, y, bar_w, 110)

    def draw_neural_brain(self, e, x, y, w, h):
        pygame.draw.rect(self.screen, (2, 3, 8), (x, y, w, h))
        pygame.draw.rect(self.screen, COLOR_BORDER, (x, y, w, h), 1)

        brain = e.brain
        inputs = e.last_brain_inputs
        outputs = e.last_decision_output
        active_drive = e.current_drive

        input_labels = ["Food", "Home", "Enemy", "Mate", "Nrg", "Age", "Res"]
        output_labels = ["Forage", "Store", "Attack", "Mate", "Plant", "Guard"]

        # Coordinates computation
        nodes_input = []
        nodes_hidden = []
        nodes_output = []

        padding = 10
        col_w = w // 2

        # Calculate Y steps
        step_in = (h - padding * 2) / max(1, brain.input_size - 1)
        for i in range(brain.input_size):
            nodes_input.append({'x': x + 35, 'y': y + padding + i * step_in, 'val': inputs[i] if i < len(inputs) else 0.0, 'lbl': input_labels[i]})

        step_hd = (h - padding * 2) / max(1, brain.hidden_size - 1)
        for j in range(brain.hidden_size):
            nodes_hidden.append({'x': x + col_w, 'y': y + padding + j * step_hd})

        step_out = (h - padding * 2) / max(1, brain.output_size - 1)
        for k in range(brain.output_size):
            nodes_output.append({'x': x + w - 45, 'y': y + padding + k * step_out, 'val': outputs[k] if k < len(outputs) else 0.0, 'lbl': output_labels[k]})

        # Convert weights tensors from GPU/MPS to numpy CPU for visual plotting
        w1_arr = brain.w1.cpu().numpy()
        w2_arr = brain.w2.cpu().numpy()

        # 1. Draw Synapses
        # Input -> Hidden
        for i in range(brain.input_size):
            for j in range(brain.hidden_size):
                weight = w1_arr[i][j]
                self.draw_synapse_line(nodes_input[i]['x'], nodes_input[i]['y'], nodes_hidden[j]['x'], nodes_hidden[j]['y'], weight)

        # Hidden -> Output
        for j in range(brain.hidden_size):
            for k in range(brain.output_size):
                weight = w2_arr[j][k]
                self.draw_synapse_line(nodes_hidden[j]['x'], nodes_hidden[j]['y'], nodes_output[k]['x'], nodes_output[k]['y'], weight)

        # 2. Draw nodes circles
        for node in nodes_input:
            intensity = int(node['val'] * 200)
            color = (min(255, 56 + intensity), 189, 248) if intensity > 0 else (30, 41, 59)
            pygame.draw.circle(self.screen, color, (node['x'], int(node['y'])), 4)
            # Label
            lbl = self.font_small.render(node['lbl'], True, COLOR_TEXT_MUTED)
            self.screen.blit(lbl, (node['x'] - 32, node['y'] - 5))

        for node in nodes_hidden:
            pygame.draw.circle(self.screen, (71, 85, 105), (node['x'], int(node['y'])), 3)

        for k, node in enumerate(nodes_output):
            is_active = (node['lbl'].lower() == active_drive.lower() or 
                         (node['lbl'] == "Plant" and active_drive == "Cultivate") or 
                         (node['lbl'] == "Guard" and active_drive == "Defend"))
            color = (34, 197, 94) if is_active else (30, 41, 59)
            pygame.draw.circle(self.screen, color, (node['x'], int(node['y'])), 4)
            # Label
            txt_color = (34, 197, 94) if is_active else COLOR_TEXT_SECONDARY
            lbl = self.font_small.render(node['lbl'], True, txt_color)
            self.screen.blit(lbl, (node['x'] + 8, node['y'] - 5))

    def draw_synapse_line(self, x1, y1, x2, y2, weight):
        color = (255, 120, 73) if weight > 0 else (0, 188, 212)
        alpha = int(min(255, 20 + abs(weight) * 120))
        # Draw line with thickness
        thick = max(1, int(abs(weight) * 1.5))
        
        # Pygame line drawing
        pygame.draw.line(self.screen, color, (x1, y1), (x2, y2), thick)

    def draw_console_logs(self, x, y, w, h):
        pygame.draw.rect(self.screen, (2, 3, 8), (x, y, w, h))
        pygame.draw.rect(self.screen, COLOR_BORDER, (x, y, w, h), 1)

        log_y = y + 4
        # Slice logs that fit inside
        visible_count = h // 12
        for log in self.world.logs[:visible_count]:
            log_surf = self.font_mono.render(log, True, (192, 132, 252)) # soft violet console
            self.screen.blit(log_surf, (x + 8, log_y))
            log_y += 12

    def wrap_text(self, text, font, max_width):
        words = text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines
