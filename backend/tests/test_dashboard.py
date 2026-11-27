from datetime import date, timedelta

from tests.conftest import add_expense

ALL = ("Sarvesh", "Rahul", "Kiran", "Aman")


def test_dashboard_for_new_user_is_empty(client, make_user):
    user = make_user("Fresh")
    body = client.get("/api/v1/dashboard", headers=user["headers"]).json()
    assert body["group_count"] == 0
    assert body["total_group_spending_paise"] == 0
    assert body["recent_expenses"] == []
    assert len(body["monthly_summary"]) == 6


def test_dashboard_totals(client, roommates):
    gid = roommates["group_id"]
    today = date.today().isoformat()
    everyone = [roommates[n]["id"] for n in ALL]
    h = roommates["Sarvesh"]["headers"]
    add_expense(client, gid, h, amount_paise=120000, expense_date=today, paid_by=roommates["Sarvesh"]["id"], participant_ids=everyone)
    add_expense(client, gid, h, description="Pizza", category="food", amount_paise=40000, expense_date=today,
                paid_by=roommates["Rahul"]["id"], participant_ids=[roommates["Rahul"]["id"], roommates["Kiran"]["id"]])

    body = client.get("/api/v1/dashboard", headers=h).json()
    assert body["group_count"] == 1
    assert body["total_group_spending_paise"] == 160000
    assert body["my_total_paid_paise"] == 120000
    assert body["my_total_share_paise"] == 30000
    assert body["my_net_balance_paise"] == 90000
    assert {c["category"]: c["total_paise"] for c in body["category_breakdown"]} == {"groceries": 120000, "food": 40000}
    assert body["monthly_summary"][-1] == {"month": today[:7], "total_paise": 160000, "my_share_paise": 30000}
    # Pizza: Sarvesh was not a participant, so his share is 0
    pizza = next(e for e in body["recent_expenses"] if e["description"] == "Pizza")
    assert pizza["my_share_paise"] == 0
    # Suggestions only include payments involving the current user
    assert all(roommates["Sarvesh"]["id"] in (s["from_user_id"], s["to_user_id"]) for s in body["suggested_settlements"])
    assert sum(s["amount_paise"] for s in body["suggested_settlements"]) == 90000


def test_dashboard_chart_data_respects_date_range_without_changing_all_time_totals(client, roommates):
    gid = roommates["group_id"]
    today = date.today()
    everyone = [roommates[n]["id"] for n in ALL]
    headers = roommates["Sarvesh"]["headers"]
    add_expense(
        client, gid, headers, description="In range", category="groceries", amount_paise=120000,
        expense_date=today.isoformat(), paid_by=roommates["Sarvesh"]["id"], participant_ids=everyone,
    )
    add_expense(
        client, gid, headers, description="Out of range", category="food", amount_paise=40000,
        expense_date=(today - timedelta(days=1)).isoformat(),
        paid_by=roommates["Rahul"]["id"], participant_ids=[roommates["Rahul"]["id"], roommates["Kiran"]["id"]],
    )

    response = client.get(
        "/api/v1/dashboard",
        params={"start_date": today.isoformat(), "end_date": today.isoformat()},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_group_spending_paise"] == 160000
    assert body["category_breakdown"] == [{"category": "groceries", "total_paise": 120000}]
    assert body["monthly_summary"] == [{"month": today.strftime("%Y-%m"), "total_paise": 120000, "my_share_paise": 30000}]


def test_dashboard_rejects_reversed_date_range(client, roommates):
    response = client.get(
        "/api/v1/dashboard",
        params={"start_date": "2026-11-02", "end_date": "2026-11-01"},
        headers=roommates["Sarvesh"]["headers"],
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "start_date must be on or before end_date"
