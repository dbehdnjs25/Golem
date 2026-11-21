"""Entry point: ``python -m game`` (or the ``game`` console script)."""

from __future__ import annotations

from game.core.app import Game
from game.core.controls import DEFAULT_PATH, Controls
from game.scenes.play import PlayScene


def main() -> None:
    game = Game()  # pygame.init() first: reading key names needs it
    game.run(PlayScene(Controls.load(DEFAULT_PATH), DEFAULT_PATH))


if __name__ == "__main__":
    main()
