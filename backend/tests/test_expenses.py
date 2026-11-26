from sqlalchemy import text

from app.database import engine
from tests.conftest import add_expense


def ids(roommates, *names):
    return [roommates[n]["id"] for n in names]


ALL = ("Sarvesh", "Rahul", "Kiran", "Aman")


def test_create_equal_split_expense(client, roommates):
    response = add_expense(
        client, roommates["group_id"], roommates["Sarvesh"]["headers"],
        paid_by=roommates["Sarvesh"]["id"], participant_ids=ids(roommates, *ALL),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["amount_paise"] == 120000
    assert body["paid_by_name"] == "Sarvesh"
    assert [s["share_amount_paise"] for s in body["splits"]] == [30000] * 4


def test_equal_split_with_paise_remainder(client, roommates):
    # Rs 100.00 between 3 people: 3334 + 3333 + 3333 paise
    response = add_expense(
        client, roommates["group_id"], roommates["Rahul"]["headers"],
        amount_paise=10000, paid_by=roommates["Rahul"]["id"],
        participant_ids=ids(roommates, "Rahul", "Kiran", "Aman"),
    )
    shares = sorted(s["share_amount_paise"] for s in response.json()["splits"])
    assert shares == [3333, 3333, 3334]
    assert sum(shares) == 10000


def test_create_custom_split_expense(client, roommates):
    splits = [
        {"user_id": roommates["Sarvesh"]["id"], "share_amount_paise": 40000},
        {"user_id": roommates["Rahul"]["id"], "share_amount_paise": 30000},
        {"user_id": roommates["Kiran"]["id"], "share_amount_paise": 20000},
        {"user_id": roommates["Aman"]["id"], "share_amount_paise": 10000},
    ]
    response = add_expense(
        client, roommates["group_id"], roommates["Sarvesh"]["headers"],
        description="Electricity", category="utilities", amount_paise=100000,
        paid_by=roommates["Sarvesh"]["id"], split_type="custom", splits=splits,
    )
    assert response.status_code == 201, response.text
    assert {s["user_name"]: s["share_amount_paise"] for s in response.json()["splits"]} == {
        "Sarvesh": 40000, "Rahul": 30000, "Kiran": 20000, "Aman": 10000,
    }


def test_invalid_custom_split_total_is_rejected(client, roommates):
    response = add_expense(
        client, roommates["group_id"], roommates["Sarvesh"]["headers"],
        amount_paise=100000, paid_by=roommates["Sarvesh"]["id"], split_type="custom",
        splits=[
            {"user_id": roommates["Sarvesh"]["id"], "share_amount_paise": 40000},
            {"user_id": roommates["Rahul"]["id"], "share_amount_paise": 30000},
        ],
    )
    assert response.status_code == 422
    assert "add up" in response.text


def test_zero_and_negative_amounts_rejected(client, roommates):
    for amount in (0, -500):
        response = add_expense(
            client, roommates["group_id"], roommates["Sarvesh"]["headers"], amount_paise=amount,
            paid_by=roommates["Sarvesh"]["id"], participant_ids=ids(roommates, *ALL),
        )
        assert response.status_code == 422


def test_float_amount_rejected(client, roommates):
    response = add_expense(
        client, roommates["group_id"], roommates["Sarvesh"]["headers"], amount_paise=100.5,
        paid_by=roommates["Sarvesh"]["id"], participant_ids=ids(roommates, *ALL),
    )
    assert response.status_code == 422


def test_payer_and_participants_must_be_members(client, roommates, make_user):
    outsider = make_user("Outsider")
    gid = roommates["group_id"]
    headers = roommates["Sarvesh"]["headers"]
    bad_payer = add_expense(client, gid, headers, paid_by=outsider["id"], participant_ids=ids(roommates, *ALL))
    bad_participant = add_expense(
        client, gid, headers, paid_by=roommates["Sarvesh"]["id"],
        participant_ids=[roommates["Sarvesh"]["id"], outsider["id"]],
    )
    assert bad_payer.status_code == 400
    assert bad_participant.status_code == 400


def test_duplicate_participants_rejected(client, roommates):
    sid = roommates["Sarvesh"]["id"]
    response = add_expense(client, roommates["group_id"], roommates["Sarvesh"]["headers"], paid_by=sid, participant_ids=[sid, sid])
    assert response.status_code == 422


def test_non_member_cannot_create_or_read_expenses(client, roommates, make_user):
    outsider = make_user("Outsider")
    gid = roommates["group_id"]
    created = add_expense(
        client, gid, roommates["Sarvesh"]["headers"], paid_by=roommates["Sarvesh"]["id"],
        participant_ids=ids(roommates, *ALL),
    ).json()
    assert add_expense(client, gid, outsider["headers"], paid_by=outsider["id"], participant_ids=[outsider["id"]]).status_code == 404
    assert client.get(f"/api/v1/groups/{gid}/expenses", headers=outsider["headers"]).status_code == 404
    assert client.get(f"/api/v1/expenses/{created['id']}", headers=outsider["headers"]).status_code == 404
    assert client.delete(f"/api/v1/expenses/{created['id']}", headers=outsider["headers"]).status_code == 404


def test_edit_expense_rebuilds_splits(client, roommates):
    created = add_expense(
        client, roommates["group_id"], roommates["Sarvesh"]["headers"],
        paid_by=roommates["Sarvesh"]["id"], participant_ids=ids(roommates, *ALL),
    ).json()
    response = client.patch(
        f"/api/v1/expenses/{created['id']}",
        json={"description": "Groceries + snacks", "amount_paise": 90000, "split_type": "equal",
              "participant_ids": ids(roommates, "Sarvesh", "Rahul", "Kiran")},
        headers=roommates["Sarvesh"]["headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["description"] == "Groceries + snacks"
    assert [s["share_amount_paise"] for s in body["splits"]] == [30000] * 3
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM expense_splits WHERE expense_id = :e"), {"e": created["id"]}).scalar_one()
    assert count == 3  # old splits really were replaced


def test_edit_metadata_only_keeps_splits(client, roommates):
    created = add_expense(
        client, roommates["group_id"], roommates["Sarvesh"]["headers"],
        paid_by=roommates["Sarvesh"]["id"], participant_ids=ids(roommates, *ALL),
    ).json()
    response = client.patch(
        f"/api/v1/expenses/{created['id']}", json={"notes": "Big Bazaar", "category": "food"},
        headers=roommates["Sarvesh"]["headers"],
    )
    assert response.status_code == 200
    assert response.json()["notes"] == "Big Bazaar"
    assert len(response.json()["splits"]) == 4


def test_edit_amount_without_split_type_rejected(client, roommates):
    created = add_expense(
        client, roommates["group_id"], roommates["Sarvesh"]["headers"],
        paid_by=roommates["Sarvesh"]["id"], participant_ids=ids(roommates, *ALL),
    ).json()
    response = client.patch(
        f"/api/v1/expenses/{created['id']}", json={"amount_paise": 5000},
        headers=roommates["Sarvesh"]["headers"],
    )
    assert response.status_code == 422


def test_only_payer_or_admin_can_edit_or_delete(client, roommates):
    created = add_expense(
        client, roommates["group_id"], roommates["Rahul"]["headers"],
        paid_by=roommates["Rahul"]["id"], participant_ids=ids(roommates, *ALL),
    ).json()
    url = f"/api/v1/expenses/{created['id']}"
    assert client.patch(url, json={"notes": "x"}, headers=roommates["Kiran"]["headers"]).status_code == 403
    assert client.delete(url, headers=roommates["Kiran"]["headers"]).status_code == 403
    assert client.patch(url, json={"notes": "x"}, headers=roommates["Rahul"]["headers"]).status_code == 200
    assert client.delete(url, headers=roommates["Sarvesh"]["headers"]).status_code == 204  # admin


def test_delete_expense_removes_splits(client, roommates):
    created = add_expense(
        client, roommates["group_id"], roommates["Sarvesh"]["headers"],
        paid_by=roommates["Sarvesh"]["id"], participant_ids=ids(roommates, *ALL),
    ).json()
    assert client.delete(f"/api/v1/expenses/{created['id']}", headers=roommates["Sarvesh"]["headers"]).status_code == 204
    assert client.get(f"/api/v1/expenses/{created['id']}", headers=roommates["Sarvesh"]["headers"]).status_code == 404
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM expense_splits")).scalar_one() == 0


def test_filters_and_pagination(client, roommates):
    gid = roommates["group_id"]
    headers = roommates["Sarvesh"]["headers"]
    everyone = ids(roommates, *ALL)
    add_expense(client, gid, headers, description="Rent", category="rent", amount_paise=2000000,
                expense_date="2026-10-01", paid_by=roommates["Sarvesh"]["id"], participant_ids=everyone)
    add_expense(client, gid, headers, description="Pizza", category="food", amount_paise=80000,
                expense_date="2026-11-05", paid_by=roommates["Rahul"]["id"],
                participant_ids=ids(roommates, "Rahul", "Kiran"))
    add_expense(client, gid, headers, description="Cab", category="transport", amount_paise=40000,
                expense_date="2026-11-10", paid_by=roommates["Kiran"]["id"], participant_ids=everyone)

    base = f"/api/v1/groups/{gid}/expenses"
    all_items = client.get(base, headers=headers).json()
    assert [e["description"] for e in all_items["items"]] == ["Cab", "Pizza", "Rent"]  # newest first
    assert client.get(base, params={"category": "food"}, headers=headers).json()["total"] == 1
    november = client.get(base, params={"from_date": "2026-11-01", "to_date": "2026-11-30"}, headers=headers).json()
    assert november["total"] == 2
    aman = client.get(base, params={"member_id": roommates["Aman"]["id"]}, headers=headers).json()
    assert {e["description"] for e in aman["items"]} == {"Rent", "Cab"}
    page2 = client.get(base, params={"page": 2, "page_size": 2}, headers=headers).json()
    assert page2["total"] == 3 and [e["description"] for e in page2["items"]] == ["Rent"]
    assert client.get(base, params={"category": "invalid"}, headers=headers).status_code == 422


def test_database_check_constraint_blocks_bad_rows(client, roommates):
    """Even if application validation were bypassed, PostgreSQL rejects bad data."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO expenses (group_id, paid_by, description, amount_paise, category, split_type, expense_date) "
                "VALUES (:g, :u, 'bad', -1, 'food', 'equal', '2026-11-01')"
            ), {"g": roommates["group_id"], "u": roommates["Sarvesh"]["id"]})
