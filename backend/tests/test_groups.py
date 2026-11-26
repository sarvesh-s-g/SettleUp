from tests.conftest import add_expense


def test_create_group_makes_creator_admin(client, make_user):
    sarvesh = make_user("Sarvesh")
    response = client.post("/api/v1/groups", json={"name": "Room 204"}, headers=sarvesh["headers"])
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Room 204"
    assert body["my_role"] == "admin"
    assert [m["name"] for m in body["members"]] == ["Sarvesh"]


def test_group_name_is_validated(client, make_user):
    user = make_user("Sarvesh")
    assert client.post("/api/v1/groups", json={"name": "  "}, headers=user["headers"]).status_code == 422


def test_list_groups_shows_only_my_groups(client, roommates, make_user):
    outsider = make_user("Outsider")
    client.post("/api/v1/groups", json={"name": "Outsider's group"}, headers=outsider["headers"])

    mine = client.get("/api/v1/groups", headers=roommates["Rahul"]["headers"]).json()
    assert [g["name"] for g in mine] == ["Room 204"]
    assert mine[0]["member_count"] == 4
    assert mine[0]["my_role"] == "member"


def test_add_member_and_list_members(client, roommates):
    members = client.get(
        f"/api/v1/groups/{roommates['group_id']}/members", headers=roommates["Kiran"]["headers"]
    ).json()
    assert [m["name"] for m in members] == ["Sarvesh", "Rahul", "Kiran", "Aman"]
    assert members[0]["role"] == "admin"


def test_duplicate_membership_is_rejected(client, roommates):
    response = client.post(
        f"/api/v1/groups/{roommates['group_id']}/members",
        json={"email": "rahul@example.com"}, headers=roommates["Sarvesh"]["headers"],
    )
    assert response.status_code == 409
    self_add = client.post(
        f"/api/v1/groups/{roommates['group_id']}/members",
        json={"email": "sarvesh@example.com"}, headers=roommates["Sarvesh"]["headers"],
    )
    assert self_add.status_code == 409


def test_add_unregistered_email_returns_404(client, roommates):
    response = client.post(
        f"/api/v1/groups/{roommates['group_id']}/members",
        json={"email": "nobody@example.com"}, headers=roommates["Sarvesh"]["headers"],
    )
    assert response.status_code == 404


def test_only_admin_can_add_members(client, roommates, make_user):
    make_user("Newbie")
    response = client.post(
        f"/api/v1/groups/{roommates['group_id']}/members",
        json={"email": "newbie@example.com"}, headers=roommates["Rahul"]["headers"],
    )
    assert response.status_code == 403


def test_non_member_cannot_view_group(client, roommates, make_user):
    outsider = make_user("Outsider")
    gid = roommates["group_id"]
    assert client.get(f"/api/v1/groups/{gid}", headers=outsider["headers"]).status_code == 404
    assert client.get(f"/api/v1/groups/{gid}/members", headers=outsider["headers"]).status_code == 404
    # A group id that does not exist looks exactly the same to an outsider.
    assert client.get("/api/v1/groups/99999", headers=outsider["headers"]).status_code == 404


def test_member_can_leave_when_settled(client, roommates):
    gid = roommates["group_id"]
    aman = roommates["Aman"]
    response = client.delete(f"/api/v1/groups/{gid}/members/{aman['id']}", headers=aman["headers"])
    assert response.status_code == 204
    assert client.get(f"/api/v1/groups/{gid}", headers=aman["headers"]).status_code == 404


def test_member_with_balance_cannot_be_removed(client, roommates):
    gid = roommates["group_id"]
    add_expense(
        client, gid, roommates["Sarvesh"]["headers"], paid_by=roommates["Sarvesh"]["id"],
        participant_ids=[roommates[n]["id"] for n in ("Sarvesh", "Rahul", "Kiran", "Aman")],
    )
    response = client.delete(
        f"/api/v1/groups/{gid}/members/{roommates['Aman']['id']}", headers=roommates["Sarvesh"]["headers"]
    )
    assert response.status_code == 400


def test_non_admin_cannot_remove_others(client, roommates):
    gid = roommates["group_id"]
    response = client.delete(
        f"/api/v1/groups/{gid}/members/{roommates['Aman']['id']}", headers=roommates["Rahul"]["headers"]
    )
    assert response.status_code == 403


def test_only_admin_leaving_promotes_next_member(client, roommates):
    gid = roommates["group_id"]
    sarvesh = roommates["Sarvesh"]
    assert client.delete(f"/api/v1/groups/{gid}/members/{sarvesh['id']}", headers=sarvesh["headers"]).status_code == 204
    members = client.get(f"/api/v1/groups/{gid}/members", headers=roommates["Rahul"]["headers"]).json()
    assert {m["name"]: m["role"] for m in members}["Rahul"] == "admin"


def test_last_member_cannot_leave(client, make_user):
    solo = make_user("Solo")
    gid = client.post("/api/v1/groups", json={"name": "Just me"}, headers=solo["headers"]).json()["id"]
    assert client.delete(f"/api/v1/groups/{gid}/members/{solo['id']}", headers=solo["headers"]).status_code == 400
