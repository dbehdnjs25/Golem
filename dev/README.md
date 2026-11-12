# dev — tuning scripts

Not part of the game. Nothing in `src/game` imports anything here, so a knob
turned in this folder cannot reach a build. That is why these are scripts
rather than a debug key: a debug key ships.

Each one changes **one number** and then starts the real game, real window and
all. You are playing the actual game with that number set.

```bash
python dev/magic.py         # a staff in hand, every shape already found
python dev/magic.py 1       # the same, standing on the burnt forest's altar
python dev/boss.py 1        # an altar, unkillable, no staff
python dev/damage.py 50     # the weapon hits for 50
python dev/speed.py 400     # the player walks at 400 px/s
python dev/stamina.py 400   # the wind holds 400
python dev/maxhp.py 1000    # the health bar holds 1000
```

Run one with no number and it picks a generous default, which is usually what
you wanted anyway:

| | default | normally |
|---|---|---|
| `damage.py` | 60 | 12 |
| `speed.py` | 400 | 200 |
| `stamina.py` | 400 | 100 |
| `maxhp.py` | 1000 | 100 |

## One number each, on purpose

Only the ceiling moves. What spends stamina, what deals damage, what multiplies
speed when sprinting or dodging — all unchanged. So a bigger number buys more
of the same game rather than a different one, and what you learn from playing
with it still applies to the build.

## Why they set the object, not the config

The dataclass defaults (`speed: float = config.PLAYER_SPEED` and the rest) are
read once, when the class is created at import. Assigning `config.PLAYER_SPEED`
afterwards changes nothing at all, silently — the worst kind of knob. These set
the value on the player, or on the weapon in hand.
