"""The application shell: owns the window, the clock and the scene stack.

This is the *only* module that touches `pygame.display` and the event pump, so
it is intentionally thin. Everything worth testing lives in scenes, entities
and `FixedTimestep`; this class just wires them to real pygame I/O.
"""

from __future__ import annotations

import os

import pygame

from game import config
from game.core.loop import FixedTimestep
from game.core.scene import Scene, SceneManager


class Game:
    def __init__(self) -> None:
        # Nearest-neighbour when SDL stretches the window. The default is
        # linear, which smears every edge in the game the moment the window
        # stops being exactly SCREEN_SIZE -- the ground, the player and the
        # items all went soft at once under F11. It has to be set before the
        # display is created, so it goes above pygame.init().
        os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "0")
        # Whole multiples only, with bars around the rest. A 1.07x stretch to
        # fill a screen is the same disease as a 0.75 zoom: some pixels get two
        # rows and their neighbours get one, and the seam between them travels
        # as you walk. Bars are the price of every pixel being the same size.
        os.environ.setdefault("SDL_RENDER_INTEGER_SCALE", "1")
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        # SCALED keeps the drawing surface at SCREEN_SIZE and lets SDL stretch
        # it to whatever the window is, picking an opening size that fits the
        # desktop. Everything downstream -- the camera's view, every HUD
        # coordinate, the mouse positions mining and the free camera read --
        # is written against 960x540, and this way all of it stays true at any
        # window size. RESIZABLE lets the player drag it; F11 fills the screen.
        # vsync, because without it the window tears. The seam is a horizontal
        # line, so it only shows when the view moves ACROSS it -- walking left
        # and right looked clean and walking up and down smeared.
        self.screen = pygame.display.set_mode(
            config.SCREEN_SIZE, pygame.SCALED | pygame.RESIZABLE, vsync=1
        )
        self.clock = pygame.time.Clock()
        self.timestep = FixedTimestep()
        self.scenes = SceneManager()
        self.running = False

    def run(self, initial_scene: Scene) -> None:
        self.scenes.push(initial_scene)
        self.running = True
        while self.running and not self.scenes.is_empty:
            frame_time = self.clock.tick(config.FPS) / 1000.0  # ms -> seconds
            self._process_events()
            for _ in range(self.timestep.steps(frame_time)):
                self.scenes.update(self.timestep.dt)
            self._render()
        pygame.quit()

    def _process_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            # Fullscreen is the window's business, not a scene's, so it is
            # swallowed here rather than passed down.
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
                continue
            self.scenes.handle_event(event)

    def _render(self) -> None:
        self.screen.fill(config.BACKGROUND)
        self.scenes.draw(self.screen)
        pygame.display.flip()
