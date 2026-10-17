from game import config
from game.systems import weather


def _trace(fn, span: float = 600.0, step: float = 0.25) -> list[float]:
    n = int(span / step)
    return [fn(i * step) for i in range(n)]


def test_both_storms_stay_between_nothing_and_everything():
    for fn in (weather.blizzard_at, weather.sandstorm_at):
        for value in _trace(fn):
            assert 0.0 <= value <= 1.0


def test_the_same_moment_always_blows_the_same():
    # Driven by the clock, not by a die. Rolled every frame, a gust would
    # flicker instead of gusting.
    for fn in (weather.blizzard_at, weather.sandstorm_at):
        assert fn(123.456) == fn(123.456)


def test_a_gust_actually_rises_and_falls():
    # A constant is not weather.
    for fn in (weather.blizzard_at, weather.sandstorm_at):
        trace = _trace(fn)
        assert max(trace) - min(trace) > 0.5, fn.__name__


def test_it_is_calm_at_least_some_of_the_time():
    # Weather that is always at full strength is just a worse biome.
    for fn in (weather.blizzard_at, weather.sandstorm_at):
        trace = _trace(fn)
        assert min(trace) < 0.2, fn.__name__
        assert max(trace) > 0.8, fn.__name__


def test_the_two_storms_do_not_move_together():
    # They are different weather in different places; marching in lockstep
    # would read as one effect wearing two coats.
    blizzard = _trace(weather.blizzard_at)
    sand = _trace(weather.sandstorm_at)
    disagreement = sum(1 for a, b in zip(blizzard, sand, strict=True) if abs(a - b) > 0.3)
    assert disagreement > len(blizzard) // 4


def test_sight_shrinks_as_the_blizzard_rises():
    clear = weather.sight_radius(0.0)
    thick = weather.sight_radius(1.0)
    assert thick < clear
    assert thick == config.BLIZZARD_SIGHT_MIN
    assert clear == config.BLIZZARD_SIGHT_MAX


def test_you_can_always_see_something():
    # Blind is not a mechanic, it is a black screen.
    for strength in (0.0, 0.5, 1.0):
        assert weather.sight_radius(strength) > 0


# --- what a sandstorm does to the breath ----------------------------------


def test_a_storm_slows_the_breath_coming_back():
    assert weather.regen_mult(1.0) < weather.regen_mult(0.0)
    assert weather.regen_mult(0.0) == 1.0


def test_even_the_worst_of_it_never_stops_recovery():
    # The bog is already the place where nothing comes back. Two places doing
    # the same thing would leave one of them spare.
    assert weather.regen_mult(1.0) == config.WASTELAND_REGEN_FLOOR
    assert config.WASTELAND_REGEN_FLOOR > 0


def test_it_is_steady_between_the_ends():
    seen = [weather.regen_mult(i / 10) for i in range(11)]
    assert seen == sorted(seen, reverse=True)
