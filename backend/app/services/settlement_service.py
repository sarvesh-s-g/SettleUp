"""Greedy settlement suggestion algorithm.

Input : {user_id: net_balance_paise}   (positive = creditor, negative = debtor)
Output: list of (debtor_id, creditor_id, amount_paise) payments that bring every
        balance to zero.

Steps
  1. Split members into creditors (balance > 0) and debtors (balance < 0).
  2. Sort both lists by amount, largest first (ties broken by user id, so the
     output is deterministic).
  3. Take the current debtor and the current creditor. The payment is the smaller
     of what the debtor owes and what the creditor is owed.
  4. Subtract the payment from both. Whoever reaches zero is finished, so move to
     the next debtor and/or creditor.
  5. Repeat until one list is exhausted. Because balances sum to zero, both lists
     run out at the same time.

Every step settles at least one person completely, so for n people with non-zero
balances the plan has at most n - 1 payments.

Complexity: sorting is O(n log n); the matching loop is O(n) because each
iteration advances at least one pointer. Extra space is O(n).

Note: this is a heuristic. Finding the absolute minimum number of payments is
NP-hard in general (it requires finding the largest number of disjoint zero-sum
subgroups), so we do not claim the result is always the global minimum.
"""


def suggest_settlements(balances: dict[int, int]) -> list[tuple[int, int, int]]:
    if sum(balances.values()) != 0:
        raise ValueError("Balances must sum to zero")

    creditors = sorted(
        ((user_id, amount) for user_id, amount in balances.items() if amount > 0),
        key=lambda item: (-item[1], item[0]),
    )
    debtors = sorted(
        ((user_id, -amount) for user_id, amount in balances.items() if amount < 0),
        key=lambda item: (-item[1], item[0]),
    )

    payments: list[tuple[int, int, int]] = []
    i = j = 0
    # Mutable copies of the remaining amounts.
    debt_left = [amount for _, amount in debtors]
    credit_left = [amount for _, amount in creditors]

    while i < len(debtors) and j < len(creditors):
        amount = min(debt_left[i], credit_left[j])
        payments.append((debtors[i][0], creditors[j][0], amount))
        debt_left[i] -= amount
        credit_left[j] -= amount
        if debt_left[i] == 0:
            i += 1
        if credit_left[j] == 0:
            j += 1

    return payments
