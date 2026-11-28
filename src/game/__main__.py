"""Entry point: ``python -m game`` (or the ``game`` console script)."""

from __future__ import annotations

from game.core.app import Game
from game.core.controls import DEFAULT_PATH, Controls
from game.scenes.menu import MenuScene


def main() -> None:
    game = Game()  # pygame.init() first: reading key names needs it
    # The main menu: Play picks a save slot, which starts a new game (with a
    # fresh world seed) or carries on the one saved there.
    game.run(MenuScene(Controls.load(DEFAULT_PATH), DEFAULT_PATH))


if __name__ == "__main__":
    main()
