from tests.conftest import add_expense, balances_by_name

ALL = ("Sarvesh", "Rahul", "Kiran", "Aman")


def ids(roommates, *names):
    return [roommates[n]["id"] for n in names]


def setup_example(client, roommates):
    """Build the balances used in the problem statement:
    Sarvesh +450, Rahul +50, Kiran -150, Aman -350 (rupees)."""
    gid = roommates["group_id"]
    h = roommates["Sarvesh"]["headers"]
    # Sarvesh pays Rs 1200 groceries for all 4 -> each owes 300
    add_expense(client, gid, h, amount_paise=120000, paid_by=roommates["Sarvesh"]["id"], participant_ids=ids(roommates, *ALL))
    #   -> S +900, R -300, K -300, A -300
    # Rahul pays Rs 400 dinner, custom shares S 50, R 50, K 150, A 150
    #   -> S +850, R +50, K -450, A -450
    add_expense(
        client, gid, h, description="Dinner", category="food", amount_paise=40000,
        paid_by=roommates["Rahul"]["id"], split_type="custom",
        splits=[
            {"user_id": roommates["Sarvesh"]["id"], "share_amount_paise": 5000},
            {"user_id": roommates["Rahul"]["id"], "share_amount_paise": 5000},
            {"user_id": roommates["Kiran"]["id"], "share_amount_paise": 15000},
            {"user_id": roommates["Aman"]["id"], "share_amount_paise": 15000},
        ],
    )
    # Kiran pays a Rs 400 cab used only by Sarvesh
    #   -> S +450, R +50, K -50, A -450
    add_expense(
        client, gid, h, description="Cab", category="transport", amount_paise=40000,
        paid_by=roommates["Kiran"]["id"], split_type="custom",
        splits=[
            {"user_id": roommates["Sarvesh"]["id"], "share_amount_paise": 40000},
        ],
    )
    # Aman pays Rs 100 tea consumed only by Kiran
    #   -> S +450, R +50, K -150, A -350
    add_expense(
        client, gid, h, description="Tea", category="food", amount_paise=10000,
        paid_by=roommates["Aman"]["id"], split_type="custom",
        splits=[{"user_id": roommates["Kiran"]["id"], "share_amount_paise": 10000}],
    )
    return gid


def test_balances_follow_the_formula(client, roommates):
    gid = setup_example(client, roommates)
    balances = balances_by_name(client, gid, roommates["Kiran"]["headers"])
    assert balances == {"Sarvesh": 45000, "Rahul": 5000, "Kiran": -15000, "Aman": -35000}
    assert sum(balances.values()) == 0


def test_balance_breakdown_fields(client, roommates):
    gid = setup_example(client, roommates)
    rows = client.get(f"/api/v1/groups/{gid}/balances", headers=roommates["Sarvesh"]["headers"]).json()["balances"]
    sarvesh = next(r for r in rows if r["name"] == "Sarvesh")
    assert sarvesh["total_paid_paise"] == 120000
    assert sarvesh["total_share_paise"] == 30000 + 5000 + 40000
    assert sarvesh["net_balance_paise"] == 45000


def test_zero_balance_group(client, roommates):
    gid = roommates["group_id"]
    balances = balances_by_name(client, gid, roommates["Sarvesh"]["headers"])
    assert balances == {"Sarvesh": 0, "Rahul": 0, "Kiran": 0, "Aman": 0}
    suggested = client.get(f"/api/v1/groups/{gid}/settlements/suggested", headers=roommates["Sarvesh"]["headers"]).json()
    assert suggested["settlements"] == []


def test_suggested_settlements_match_example(client, roommates):
    gid = setup_example(client, roommates)
    suggested = client.get(f"/api/v1/groups/{gid}/settlements/suggested", headers=roommates["Rahul"]["headers"]).json()
    plan = [(s["from_name"], s["to_name"], s["amount_paise"]) for s in suggested["settlements"]]
    assert plan == [("Aman", "Sarvesh", 35000), ("Kiran", "Sarvesh", 10000), ("Kiran", "Rahul", 5000)]


def test_recording_settlements_updates_balances(client, roommates):
    gid = setup_example(client, roommates)
    response = client.post(
        f"/api/v1/groups/{gid}/settlements",
        json={"paid_by": roommates["Aman"]["id"], "paid_to": roommates["Sarvesh"]["id"],
              "amount_paise": 35000, "settled_at": "2026-11-15"},
        headers=roommates["Aman"]["headers"],
    )
    assert response.status_code == 201, response.text
    assert response.json()["paid_by_name"] == "Aman"
    balances = balances_by_name(client, gid, roommates["Aman"]["headers"])
    assert balances == {"Sarvesh": 10000, "Rahul": 5000, "Kiran": -15000, "Aman": 0}

    # Apply the remaining suggestions -> everyone settled.
    for s in client.get(f"/api/v1/groups/{gid}/settlements/suggested", headers=roommates["Kiran"]["headers"]).json()["settlements"]:
        ok = client.post(
            f"/api/v1/groups/{gid}/settlements",
            json={"paid_by": s["from_user_id"], "paid_to": s["to_user_id"], "amount_paise": s["amount_paise"]},
            headers=roommates["Sarvesh"]["headers"],  # admin may record on behalf of others
        )
        assert ok.status_code == 201, ok.text
    assert set(balances_by_name(client, gid, roommates["Kiran"]["headers"]).values()) == {0}

    history = client.get(f"/api/v1/groups/{gid}/settlements", headers=roommates["Rahul"]["headers"]).json()
    assert len(history) == 3


def test_partial_settlement(client, roommates):
    gid = setup_example(client, roommates)
    response = client.post(
        f"/api/v1/groups/{gid}/settlements",
        json={"paid_by": roommates["Aman"]["id"], "paid_to": roommates["Sarvesh"]["id"], "amount_paise": 10000},
        headers=roommates["Aman"]["headers"],
    )
    assert response.status_code == 201
    assert balances_by_name(client, gid, roommates["Aman"]["headers"])["Aman"] == -25000


def test_invalid_settlements(client, roommates, make_user):
    gid = setup_example(client, roommates)
    h = roommates["Sarvesh"]["headers"]
    url = f"/api/v1/groups/{gid}/settlements"
    s, r, k, a = ids(roommates, *ALL)

    # same person
    assert client.post(url, json={"paid_by": a, "paid_to": a, "amount_paise": 100}, headers=h).status_code == 422
    # zero / negative amount
    assert client.post(url, json={"paid_by": a, "paid_to": s, "amount_paise": 0}, headers=h).status_code == 422
    assert client.post(url, json={"paid_by": a, "paid_to": s, "amount_paise": -5}, headers=h).status_code == 422
    # more than the debt (Aman owes 350)
    too_much = client.post(url, json={"paid_by": a, "paid_to": s, "amount_paise": 35001}, headers=h)
    assert too_much.status_code == 400 and "Maximum allowed is Rs 350.00" in too_much.text
    # more than the receiver is owed (Rahul is owed only 50)
    assert client.post(url, json={"paid_by": a, "paid_to": r, "amount_paise": 6000}, headers=h).status_code == 400
    # payer is a creditor, not a debtor
    assert client.post(url, json={"paid_by": s, "paid_to": r, "amount_paise": 100}, headers=h).status_code == 400
    # receiver is a debtor
    assert client.post(url, json={"paid_by": a, "paid_to": k, "amount_paise": 100}, headers=h).status_code == 400
    # outsider involved
    outsider = make_user("Outsider")
    assert client.post(url, json={"paid_by": outsider["id"], "paid_to": s, "amount_paise": 100}, headers=h).status_code == 400
    # nothing was stored
    assert client.get(url, headers=h).json() == []


def test_member_cannot_record_settlement_between_two_others(client, roommates):
    gid = setup_example(client, roommates)
    response = client.post(
        f"/api/v1/groups/{gid}/settlements",
        json={"paid_by": roommates["Aman"]["id"], "paid_to": roommates["Sarvesh"]["id"], "amount_paise": 100},
        headers=roommates["Rahul"]["headers"],  # Rahul is neither party nor admin
    )
    assert response.status_code == 403


def test_non_member_cannot_see_balances_or_settlements(client, roommates, make_user):
    outsider = make_user("Outsider")
    gid = roommates["group_id"]
    for path in ("balances", "settlements", "settlements/suggested"):
        assert client.get(f"/api/v1/groups/{gid}/{path}", headers=outsider["headers"]).status_code == 404


def test_multiple_groups_are_isolated(client, roommates, make_user):
    """Expenses in one group never affect balances in another group."""
    gid = setup_example(client, roommates)
    sarvesh, rahul = roommates["Sarvesh"], roommates["Rahul"]
    trip = client.post("/api/v1/groups", json={"name": "Goa Trip"}, headers=rahul["headers"]).json()["id"]
    client.post(f"/api/v1/groups/{trip}/members", json={"email": sarvesh["email"]}, headers=rahul["headers"])
    add_expense(client, trip, rahul["headers"], amount_paise=500000, paid_by=rahul["id"], participant_ids=[rahul["id"], sarvesh["id"]])

    assert balances_by_name(client, trip, rahul["headers"]) == {"Rahul": 250000, "Sarvesh": -250000}
    assert balances_by_name(client, gid, rahul["headers"]) == {"Sarvesh": 45000, "Rahul": 5000, "Kiran": -15000, "Aman": -35000}
    # Kiran is not in the trip group
    assert client.get(f"/api/v1/groups/{trip}/balances", headers=roommates["Kiran"]["headers"]).status_code == 404


def test_rounding_balances_still_sum_to_zero(client, roommates):
    gid = roommates["group_id"]
    h = roommates["Sarvesh"]["headers"]
    everyone = ids(roommates, *ALL)
    for amount, payer in ((10001, "Sarvesh"), (333, "Rahul"), (99999, "Kiran"), (7, "Aman")):
        add_expense(client, gid, h, amount_paise=amount, paid_by=roommates[payer]["id"], participant_ids=everyone)
    balances = balances_by_name(client, gid, h)
    assert sum(balances.values()) == 0
    plan = client.get(f"/api/v1/groups/{gid}/settlements/suggested", headers=h).json()["settlements"]
    assert all(p["amount_paise"] > 0 for p in plan)
    assert sum(p["amount_paise"] for p in plan) == sum(-v for v in balances.values() if v < 0)


def test_editing_expense_changes_balances(client, roommates):
    gid = roommates["group_id"]
    h = roommates["Sarvesh"]["headers"]
    created = add_expense(client, gid, h, amount_paise=120000, paid_by=roommates["Sarvesh"]["id"],
                          participant_ids=ids(roommates, *ALL)).json()
    client.patch(f"/api/v1/expenses/{created['id']}",
                 json={"amount_paise": 60000, "split_type": "equal", "participant_ids": ids(roommates, "Sarvesh", "Rahul")},
                 headers=h)
    assert balances_by_name(client, gid, h) == {"Sarvesh": 30000, "Rahul": -30000, "Kiran": 0, "Aman": 0}
    client.delete(f"/api/v1/expenses/{created['id']}", headers=h)
    assert set(balances_by_name(client, gid, h).values()) == {0}
