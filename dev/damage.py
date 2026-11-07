"""Play with the weapon hitting for a different number.

    python dev/damage.py 50

Set on the weapon in hand rather than on ``config.WEAPON_DAMAGE``, which the
WeaponTool read once at import and will not read again. Carved glyphs still
add their own power on top, as they do in a real game.
"""

from __future__ import annotations

from _launch import number, run, weapon_of

from game import config

if __name__ == "__main__":
    hit = number(config.WEAPON_DAMAGE * 5)
    run("weapon damage", hit, lambda scene: setattr(weapon_of(scene), "damage", hit))
