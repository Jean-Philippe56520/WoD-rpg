from game.dice import roll_pool, rouse_check


def test_dice_pool_is_deterministic_for_async_retry_safety():
    first = roll_pool(pool=7, hunger=3, difficulty=3, seed="same-scene")
    second = roll_pool(pool=7, hunger=3, difficulty=3, seed="same-scene")

    assert first == second
    assert len(first.hunger_dice) == 3
    assert len(first.normal_dice) == 4
    assert first.margin == first.successes - 3


def test_hunger_never_adds_dice_beyond_pool():
    result = roll_pool(pool=2, hunger=5, difficulty=1, seed="hungry")

    assert len(result.hunger_dice) == 2
    assert not result.normal_dice
    assert all(1 <= value <= 10 for value in result.hunger_dice)


def test_rouse_check_is_idempotent_and_caps_hunger():
    die_one, hunger_one = rouse_check(hunger=5, seed="rouse")
    die_two, hunger_two = rouse_check(hunger=5, seed="rouse")

    assert (die_one, hunger_one) == (die_two, hunger_two)
    assert 1 <= die_one <= 10
    assert hunger_one == 5
