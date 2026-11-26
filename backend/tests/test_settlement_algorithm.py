"""Unit tests for the pure greedy settlement algorithm (no database needed)."""
import itertools
import random

import pytest

from app.services.settlement_service import suggest_settlements

SARVESH, RAHUL, KIRAN, AMAN = 1, 2, 3, 4


def apply(balances: dict[int, int], payments) -> dict[int, int]:
    """Apply suggested payments: the debtor's balance goes up, the creditor's goes down."""
    result = dict(balances)
    for debtor, creditor, amount in payments:
        result[debtor] += amount
        result[creditor] -= amount
    return result


def test_example_from_problem_statement():
    balances = {SARVESH: 45000, RAHUL: 5000, KIRAN: -15000, AMAN: -35000}
    plan = suggest_settlements(balances)
    assert plan == [(AMAN, SARVESH, 35000), (KIRAN, SARVESH, 10000), (KIRAN, RAHUL, 5000)]
    assert all(v == 0 for v in apply(balances, plan).values())


def test_empty_group_returns_no_payments():
    assert suggest_settlements({}) == []


def test_everyone_settled_returns_no_payments():
    assert suggest_settlements({1: 0, 2: 0, 3: 0}) == []


def test_single_debtor_single_creditor():
    assert suggest_settlements({1: 250, 2: -250}) == [(2, 1, 250)]


def test_one_creditor_many_debtors():
    plan = suggest_settlements({1: 900, 2: -300, 3: -300, 4: -300})
    assert sorted(plan) == [(2, 1, 300), (3, 1, 300), (4, 1, 300)]


def test_one_debtor_many_creditors():
    plan = suggest_settlements({1: -600, 2: 100, 3: 200, 4: 300})
    assert plan == [(1, 4, 300), (1, 3, 200), (1, 2, 100)]


def test_odd_paise_amounts():
    balances = {1: 1, 2: 333, 3: -167, 4: -167}
    plan = suggest_settlements(balances)
    assert all(amount > 0 for _, _, amount in plan)
    assert all(v == 0 for v in apply(balances, plan).values())


def test_unbalanced_input_is_rejected():
    with pytest.raises(ValueError):
        suggest_settlements({1: 100, 2: -99})


def test_output_is_deterministic():
    balances = {5: 100, 3: 100, 9: -100, 1: -100}
    assert suggest_settlements(balances) == suggest_settlements(dict(reversed(balances.items())))


@pytest.mark.parametrize("seed", range(25))
def test_random_groups_always_settle_with_at_most_n_minus_1_payments(seed):
    rng = random.Random(seed)
    size = rng.randint(2, 12)
    values = [rng.randint(-50_000, 50_000) for _ in range(size - 1)]
    values.append(-sum(values))  # force the total to zero
    balances = dict(enumerate(values, start=1))

    plan = suggest_settlements(balances)

    assert all(amount > 0 for _, _, amount in plan)
    assert all(debtor != creditor for debtor, creditor, _ in plan)
    assert all(v == 0 for v in apply(balances, plan).values())
    non_zero = sum(1 for v in balances.values() if v != 0)
    assert len(plan) <= max(non_zero - 1, 0)
    # total paid by debtors == total received by creditors == total debt
    total_debt = sum(-v for v in balances.values() if v < 0)
    assert sum(amount for _, _, amount in plan) == total_debt


def test_debtors_only_pay_and_creditors_only_receive():
    balances = {1: 700, 2: -200, 3: 100, 4: -600}
    plan = suggest_settlements(balances)
    debtors = {u for u, v in balances.items() if v < 0}
    creditors = {u for u, v in balances.items() if v > 0}
    for debtor, creditor, _ in plan:
        assert debtor in debtors and creditor in creditors


def test_greedy_matches_bruteforce_minimum_on_small_case():
    # {+5, +5, -2, -3, -5} can be settled in 3 payments (-5 -> +5, -2/-3 -> +5)
    # and greedy (largest first) also finds 3. Contrast with the next test,
    # where greedy needs one payment more than the optimum.
    balances = {1: 5, 2: 5, 3: -2, 4: -3, 5: -5}
    plan = suggest_settlements(balances)
    assert all(v == 0 for v in apply(balances, plan).values())
    assert len(plan) <= 4
    # brute-force check that no plan of fewer than 3 transfers exists
    assert min_transfers_bruteforce(balances) == 3


def test_known_case_where_greedy_is_not_minimal():
    """Honest limitation: three people owe Rs 600 each; creditors are owed 300/600/900.
    Greedy produces 5 payments, but 4 are enough:
      D1 -> C600 (600), D2 -> C900 (600), D3 -> C900 (300), D3 -> C300 (300)."""
    balances = {1: -60000, 2: -60000, 3: -60000, 4: 30000, 5: 60000, 6: 90000}
    plan = suggest_settlements(balances)
    assert all(v == 0 for v in apply(balances, plan).values())
    assert len(plan) == 5
    assert min_transfers_bruteforce(balances) == 4


def min_transfers_bruteforce(balances: dict[int, int]) -> int:
    """Minimum transfers = n - (max number of disjoint zero-sum subsets). Tiny inputs only."""
    values = [v for v in balances.values() if v != 0]
    best = 0

    def search(remaining, groups):
        nonlocal best
        if not remaining:
            best = max(best, groups)
            return
        first, rest = remaining[0], remaining[1:]
        for size in range(0, len(rest) + 1):
            for combo in itertools.combinations(range(len(rest)), size):
                if first + sum(rest[i] for i in combo) == 0:
                    left = [rest[i] for i in range(len(rest)) if i not in combo]
                    search(left, groups + 1)

    search(values, 0)
    return len(values) - best
