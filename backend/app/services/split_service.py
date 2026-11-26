"""Pure functions that turn an expense amount into individual shares (in paise)."""


def split_equally(amount_paise: int, user_ids: list[int]) -> dict[int, int]:
    """Split amount_paise between user_ids so the shares add up EXACTLY to the amount.

    Integer division gives everyone the same base share. The leftover paise
    (amount % n, always fewer than n) are handed out one each to the users with the
    smallest ids, so the result is deterministic: the same input always gives the
    same shares.

    >>> split_equally(1000, [3, 1, 2])
    {1: 334, 2: 333, 3: 333}
    """
    if not user_ids:
        raise ValueError("At least one participant is required")
    if amount_paise <= 0:
        raise ValueError("Amount must be positive")

    ordered = sorted(user_ids)
    count = len(ordered)
    base_share, remainder = divmod(amount_paise, count)

    shares: dict[int, int] = {}
    for index, user_id in enumerate(ordered):
        shares[user_id] = base_share + (1 if index < remainder else 0)
    return shares


def custom_shares(amount_paise: int, splits: list[tuple[int, int]]) -> dict[int, int]:
    """Validate user-entered (user_id, share) pairs and return them as a dict."""
    shares: dict[int, int] = {}
    for user_id, share in splits:
        if share <= 0:
            raise ValueError("Every share must be greater than zero")
        if user_id in shares:
            raise ValueError("A participant is listed more than once")
        shares[user_id] = share
    if sum(shares.values()) != amount_paise:
        raise ValueError("Custom shares must add up to the expense amount")
    return shares
