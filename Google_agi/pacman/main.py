import pygame
import sys
from world import SimulationWorld
from ui import SimulationUI

def main():
    # 1. Initialize Pygame Modules
    pygame.init()
    pygame.display.set_caption("A-Life Pac-Man: Evolutionary Neural Network Simulation")

    # Run in native fullscreen mode
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    # 2. Setup World Environment
    world = SimulationWorld()
    
    # Initialize UI (which dynamically calculates tile size and y-offset based on fullscreen size)
    ui = SimulationUI(world, screen)
    
    tile_size = ui.tile_size
    viewport_w = ui.viewport_w
    viewport_h = ui.viewport_h
    y_offset = ui.y_offset
    world.tileSize = tile_size # attach parameter for ui reference

    # 3. Configure Clock
    clock = pygame.time.Clock()
    running = True
    
    # Inspected Pacman reference
    selected_pacman = None

    print("==================================================================")
    print("A-Life Pac-Man Simulation running on PyGame & PyTorch (accelerated)")
    print("==================================================================")
    print("CONTROLS:")
    print("  [SPACE] - Play / Pause Simulation")
    print("  [R]     - Restart / Reset simulation")
    print("  [M]     - Spawn wild magic mushroom")
    print("  [P]     - Toggle path guides")
    print("  [1]     - Set simulation speed to 1x (Normal)")
    print("  [2]     - Set simulation speed to 2x")
    print("  [3]     - Set simulation speed to 5x")
    print("  [4]     - Set simulation speed to 10x")
    print("  [5]     - Set simulation speed to 20x")
    print("  [UP]    - Increase Life Expectancy by 1 minute")
    print("  [DOWN]  - Decrease Life Expectancy by 1 minute")
    print("  [CLICK] - Click on any Pac-Man on the maze grid to inspect it")
    print("==================================================================")

    while running:
        # A. Process Window Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                
                # Check if click is inside the simulation viewport both horizontally and vertically
                if mx < viewport_w and y_offset <= my < y_offset + viewport_h:
                    click_tile_x = mx / tile_size
                    click_tile_y = (my - y_offset) / tile_size
                    
                    # Search nearest Pac-man within tolerance bounds
                    nearest = None
                    min_dist = 1.3
                    
                    for entity in world.entities:
                        dx = entity.x - click_tile_x
                        dy = entity.y - click_tile_y
                        d = (dx*dx + dy*dy) ** 0.5
                        if d < min_dist:
                            min_dist = d
                            nearest = entity
                            
                    if nearest:
                        selected_pacman = nearest
                    else:
                        selected_pacman = None
                        
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    break
                elif event.key == pygame.K_SPACE:
                    world.is_paused = not world.is_paused
                    world.add_log(f"Simulation {'Paused' if world.is_paused else 'Resumed'}")
                    
                elif event.key == pygame.K_r:
                    world.reset_simulation()
                    selected_pacman = None
                    world.add_log("Simulation reset completed.")
                    
                elif event.key == pygame.K_m:
                    world.spawn_random_mushroom()
                    world.add_log("Manually spawned a wild mushroom.")
                    
                elif event.key == pygame.K_p:
                    world.show_path_guide = not world.show_path_guide
                    world.add_log(f"Path guides {'enabled' if world.show_path_guide else 'disabled'}")
                    
                elif event.key == pygame.K_1:
                    world.speed_multiplier = 1
                    world.add_log("Speed set to 1x")
                elif event.key == pygame.K_2:
                    world.speed_multiplier = 2
                    world.add_log("Speed set to 2x")
                elif event.key == pygame.K_3:
                    world.speed_multiplier = 5
                    world.add_log("Speed set to 5x")
                elif event.key == pygame.K_4:
                    world.speed_multiplier = 10
                    world.add_log("Speed set to 10x")
                elif event.key == pygame.K_5:
                    world.speed_multiplier = 20
                    world.add_log("Speed set to 20x")
                    
                elif event.key == pygame.K_UP:
                    # Add 60 seconds (1 minute) to lifespan
                    world.life_expectancy = min(1800.0, world.life_expectancy + 60.0)
                    mins = int(world.life_expectancy) // 60
                    world.add_log(f"Life Expectancy increased to {mins} min.")
                    
                elif event.key == pygame.K_DOWN:
                    # Subtract 60 seconds (1 minute) from lifespan
                    world.life_expectancy = max(60.0, world.life_expectancy - 60.0)
                    mins = int(world.life_expectancy) // 60
                    world.add_log(f"Life Expectancy decreased to {mins} min.")

        # B. Step Simulation Physics (Ticks multiplied for fast forward speeds)
        if not world.is_paused:
            for _ in range(world.speed_multiplier):
                world.tick()

        # Check if inspected Pacman is dead
        if selected_pacman and selected_pacman.is_dead:
            selected_pacman = None

        # C. Render UI Viewport & Sidebar Panels
        ui.draw(selected_pacman)
        pygame.display.flip()

        # Limit frame rate to 60fps
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
