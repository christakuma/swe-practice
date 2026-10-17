from pricing import total_pence


def test_total_is_the_sum() -> None:
    assert total_pence([1, 2, 3]) == 6
