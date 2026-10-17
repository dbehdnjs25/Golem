from game import config
from game.systems import weather


def _trace(fn, span: float = 600.0, step: float = 0.25) -> list[float]:
    n = int(span / step)
    return [fn(i * step) for i in range(n)]


def test_the_storm_stays_between_nothing_and_everything():
    for value in _trace(weather.sandstorm_at):
        assert 0.0 <= value <= 1.0


def test_the_same_moment_always_blows_the_same():
    # Driven by the clock, not by a die. Rolled every frame, a gust would
    # flicker instead of gusting.
    assert weather.sandstorm_at(123.456) == weather.sandstorm_at(123.456)


def test_a_gust_actually_rises_and_falls():
    # A constant is not weather.
    trace = _trace(weather.sandstorm_at)
    assert max(trace) - min(trace) > 0.5


def test_it_is_calm_at_least_some_of_the_time():
    # Weather that is always at full strength is just a worse biome.
    trace = _trace(weather.sandstorm_at)
    assert min(trace) < 0.2
    assert max(trace) > 0.8


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
