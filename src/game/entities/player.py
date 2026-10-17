"""Top-down player. Logic-only: movement (and the dodge dash) is a pure function
of dt and input, so it is unit-testable headlessly. Damage is applied by
systems/combat, which reads ``invulnerable`` and writes ``hp``."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.world.biomes import WASTELAND
from game.world.map import WorldMap


@dataclass
class Player:
    pos: pygame.Vector2
    radius: float = config.PLAYER_RADIUS
    speed: float = config.PLAYER_SPEED
    hp: float = config.PLAYER_MAX_HP
    max_hp: float = config.PLAYER_MAX_HP
    dodge_timer: float = 0.0  # dash movement remaining
    iframe_timer: float = 0.0  # invulnerability remaining
    dodge_cooldown_timer: float = 0.0  # time until dodge is available again
    ward_time: float = 0.0  # seconds spent inside the ward; resets on leaving
    stamina: float = config.PLAYER_MAX_STAMINA
    max_stamina: float = config.PLAYER_MAX_STAMINA
    # Seconds before wind starts coming back. Without it, mashing dodge would
    # recover between presses and the cost would never be felt.
    stamina_hold: float = 0.0

    @property
    def winded(self) -> bool:
        return self.stamina <= 0

    def spend(self, amount: float) -> bool:
        """Pay for a move outright. False, and nothing taken, if short.

        All or nothing: there is no half a dodge, and a partial charge would
        leave the player paying for something they did not get. Trickles --
        digging, the bog -- use ``drain`` instead.
        """
        if amount > self.stamina:
            return False
        self.stamina -= amount
        self.stamina_hold = config.STAMINA_DELAY
        return True

    def drain(self, amount: float) -> None:
        """Take what is there, down to nothing, and refuse nothing."""
        self.stamina = max(0.0, self.stamina - amount)
        self.stamina_hold = config.STAMINA_DELAY

    @property
    def invulnerable(self) -> bool:
        return self.iframe_timer > 0

    def _sprint_mult(self, world: WorldMap) -> float:
        """How much running is worth under the player's feet.

        Blunted on the wasteland: flat open ground you cannot simply outrun
        what is on. Only the RUNNING -- the walk is the same everywhere, or
        the biome would be a chore to cross rather than a place that is hard
        to leave. The wind costs the same either way: it is the ground that
        is poor, not the legs.
        """
        if world.biome_at(self.pos) is WASTELAND:
            return config.WASTELAND_SPRINT_MULT
        return config.PLAYER_SPRINT_MULT

    def update(
        self,
        dt: float,
        move_dir: pygame.Vector2,
        world: WorldMap,
        dodge_pressed: bool = False,
        sprinting: bool = False,
    ) -> None:
        """Advance by ``dt`` along ``move_dir`` (unnormalized), clamped to the map circle.

        A dodge grants i-frames immediately (even when standing still) and a
        speed boost while the dash lasts.

        Running costs wind, but only while actually covering ground: the charge
        is for distance, not for a key being held. With nothing left the player
        simply walks -- not a stutter and not a refusal to move.
        """
        # A dodge with nothing left simply does not happen: not a slow one and
        # not a cheap one. The i-frames ARE the move, so a half-priced version
        # would be a half-priced escape. The cooldown is not burned either.
        if dodge_pressed and self.dodge_cooldown_timer <= 0 and self.spend(config.DODGE_COST):
            self.dodge_timer = config.DODGE_DURATION
            self.iframe_timer = config.DODGE_IFRAMES
            self.dodge_cooldown_timer = config.DODGE_COOLDOWN

        moving = move_dir.length_squared() > 0
        # A dash is already paid for; running out mid-dodge must not cut it short.
        if self.dodge_timer > 0:
            speed = self.speed * config.DODGE_SPEED_MULT
        elif sprinting and moving and self.spend(config.SPRINT_DRAIN * dt):
            speed = self.speed * self._sprint_mult(world)
        else:
            speed = self.speed
        if moving:
            self.pos += move_dir.normalize() * speed * dt
        world.clamp(self.pos, self.radius)

        self.dodge_timer = max(0.0, self.dodge_timer - dt)
        self.iframe_timer = max(0.0, self.iframe_timer - dt)
        self.dodge_cooldown_timer = max(0.0, self.dodge_cooldown_timer - dt)
