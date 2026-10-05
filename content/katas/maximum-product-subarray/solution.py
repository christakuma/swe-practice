"""Reference solution. CI asserts this passes every test in `tests.py`."""


def max_product(numbers: list[int]) -> int:
    """Return the largest product of any contiguous non-empty run.

    Kadane's algorithm in `maximum-subarray` carries one running value: the
    best sum ending here. Swapping addition for multiplication breaks that,
    and the reason is the whole kata -- **multiplication does not preserve
    order across a negative**. A large negative running product is not a dead
    end; it is one negative away from being the best answer in the list.

    So the running state is a *pair*: the best and the worst product ending at
    this position. Each new value has three candidates, because a run ending
    here either starts here or extends the previous one:

        value, value * best_so_far, value * worst_so_far

    The new best is the largest of the three and the new worst is the smallest.
    Including `value` alone is what lets a run start fresh, which is also how
    zeros are handled without a branch: after a zero both running values
    collapse to zero, and the next value's bare `value` candidate restarts the
    run.

    **Both must be computed from the old pair.** `best` is read when computing
    the new `worst`, so overwriting it first computes the worst from a value
    that no longer exists -- the classic simultaneous-assignment bug, and it
    survives every all-positive test.

    `answer` is tracked separately from `best` because the question is about
    the best run *anywhere*, not the best run ending at the last position --
    the same separation as in Kadane's. Seeding everything with `numbers[0]`
    rather than with 0 or 1 is what keeps the run non-empty: a list of a single
    negative has to return that negative, and an identity of 1 would wrongly
    beat it.
    """
    best = worst = answer = numbers[0]
    for value in numbers[1:]:
        candidates = (value, value * best, value * worst)
        best, worst = max(candidates), min(candidates)
        answer = max(answer, best)
    return answer
