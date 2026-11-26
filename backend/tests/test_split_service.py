"""Unit tests for paise-accurate splitting (no database needed)."""
import pytest

from app.services.split_service import custom_shares, split_equally


def test_even_split():
    assert split_equally(120000, [1, 2, 3, 4]) == {1: 30000, 2: 30000, 3: 30000, 4: 30000}


def test_remainder_goes_to_lowest_ids_first():
    # Rs 10.00 between 3 people -> 334 + 333 + 333 paise
    assert split_equally(1000, [3, 1, 2]) == {1: 334, 2: 333, 3: 333}


def test_shares_always_add_up_to_amount():
    for amount in (1, 7, 99, 100, 101, 12550, 99999, 1_000_000_007):
        for people in range(1, 9):
            ids = list(range(10, 10 + people))
            if amount < people:
                continue
            shares = split_equally(amount, ids)
            assert sum(shares.values()) == amount
            assert max(shares.values()) - min(shares.values()) <= 1


def test_single_participant_pays_everything():
    assert split_equally(12550, [7]) == {7: 12550}


def test_equal_split_requires_participants():
    with pytest.raises(ValueError):
        split_equally(100, [])


def test_custom_shares_must_sum_to_amount():
    assert custom_shares(100000, [(1, 40000), (2, 30000), (3, 20000), (4, 10000)]) == {
        1: 40000, 2: 30000, 3: 20000, 4: 10000,
    }
    with pytest.raises(ValueError):
        custom_shares(100000, [(1, 40000), (2, 30000)])


def test_custom_shares_reject_duplicates_and_zero():
    with pytest.raises(ValueError):
        custom_shares(200, [(1, 100), (1, 100)])
    with pytest.raises(ValueError):
        custom_shares(100, [(1, 100), (2, 0)])
