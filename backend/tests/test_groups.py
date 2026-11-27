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


def test_direct_member_addition_is_disabled(client, roommates, make_user):
    newbie = make_user("Newbie")
    response = client.post(
        f"/api/v1/groups/{roommates['group_id']}/members",
        json={"email": newbie["email"]},
        headers=roommates["Sarvesh"]["headers"],
    )
    assert response.status_code == 405


def test_invite_requires_acceptance_before_joining(client, make_user):
    sarvesh = make_user("Sarvesh")
    rahul = make_user("Rahul")
    gid = client.post("/api/v1/groups", json={"name": "Goa Trip"}, headers=sarvesh["headers"]).json()["id"]

    # Sarvesh sends invite; Rahul is NOT a member yet until he accepts.
    invite = client.post(
        f"/api/v1/groups/{gid}/invites",
        json={"email": rahul["email"]},
        headers=sarvesh["headers"],
    )
    assert invite.status_code == 201
    invite_body = invite.json()
    assert invite_body["status"] == "pending"
    assert invite_body["invited_user_name"] == "Rahul"

    # Rahul cannot view the group or appear in members before accepting.
    assert client.get(f"/api/v1/groups/{gid}", headers=rahul["headers"]).status_code == 404
    assert client.get("/api/v1/groups", headers=rahul["headers"]).json() == []
    members_before = client.get(f"/api/v1/groups/{gid}/members", headers=sarvesh["headers"]).json()
    assert [m["name"] for m in members_before] == ["Sarvesh"]

    # Rahul sees the pending invite and accepts it.
    my_invites = client.get("/api/v1/invites", headers=rahul["headers"]).json()
    assert [i["id"] for i in my_invites] == [invite_body["id"]]
    accepted = client.post(f"/api/v1/invites/{invite_body['id']}/accept", headers=rahul["headers"])
    assert accepted.status_code == 200
    assert accepted.json()["member_count"] == 2
    assert accepted.json()["my_role"] == "member"

    # Now Rahul is a member and has no pending invites left.
    assert client.get("/api/v1/invites", headers=rahul["headers"]).json() == []
    members_after = client.get(f"/api/v1/groups/{gid}/members", headers=rahul["headers"]).json()
    assert [m["name"] for m in members_after] == ["Sarvesh", "Rahul"]


def test_decline_invite_does_not_add_member_and_allows_reinvite(client, make_user):
    sarvesh = make_user("Sarvesh")
    rahul = make_user("Rahul")
    gid = client.post("/api/v1/groups", json={"name": "Goa Trip"}, headers=sarvesh["headers"]).json()["id"]

    inv1 = client.post(
        f"/api/v1/groups/{gid}/invites",
        json={"email": rahul["email"]},
        headers=sarvesh["headers"],
    ).json()
    declined = client.post(f"/api/v1/invites/{inv1['id']}/decline", headers=rahul["headers"])
    assert declined.status_code == 204
    assert client.get(f"/api/v1/groups/{gid}", headers=rahul["headers"]).status_code == 404
    assert client.get("/api/v1/invites", headers=rahul["headers"]).json() == []

    # Responding a second time to an already-declined invite fails.
    assert client.post(f"/api/v1/invites/{inv1['id']}/accept", headers=rahul["headers"]).status_code == 400

    # Admin can invite Rahul again later.
    inv2 = client.post(
        f"/api/v1/groups/{gid}/invites",
        json={"email": rahul["email"]},
        headers=sarvesh["headers"],
    )
    assert inv2.status_code == 201


def test_other_user_cannot_accept_or_decline_someone_elses_invite(client, make_user):
    sarvesh = make_user("Sarvesh")
    rahul = make_user("Rahul")
    kiran = make_user("Kiran")
    gid = client.post("/api/v1/groups", json={"name": "Goa Trip"}, headers=sarvesh["headers"]).json()["id"]
    inv = client.post(
        f"/api/v1/groups/{gid}/invites",
        json={"email": rahul["email"]},
        headers=sarvesh["headers"],
    ).json()

    assert client.post(f"/api/v1/invites/{inv['id']}/accept", headers=kiran["headers"]).status_code == 404
    assert client.post(f"/api/v1/invites/{inv['id']}/decline", headers=kiran["headers"]).status_code == 404


def test_admin_can_list_and_cancel_pending_invite(client, make_user):
    sarvesh = make_user("Sarvesh")
    rahul = make_user("Rahul")
    gid = client.post("/api/v1/groups", json={"name": "Goa Trip"}, headers=sarvesh["headers"]).json()["id"]
    inv = client.post(
        f"/api/v1/groups/{gid}/invites",
        json={"email": rahul["email"]},
        headers=sarvesh["headers"],
    ).json()

    pending = client.get(f"/api/v1/groups/{gid}/invites", headers=sarvesh["headers"]).json()
    assert [i["id"] for i in pending] == [inv["id"]]

    assert client.delete(f"/api/v1/groups/{gid}/invites/{inv['id']}", headers=sarvesh["headers"]).status_code == 204
    assert client.get(f"/api/v1/groups/{gid}/invites", headers=sarvesh["headers"]).json() == []
    assert client.get("/api/v1/invites", headers=rahul["headers"]).json() == []


def test_add_member_and_list_members(client, roommates):
    members = client.get(
        f"/api/v1/groups/{roommates['group_id']}/members", headers=roommates["Kiran"]["headers"]
    ).json()
    assert [m["name"] for m in members] == ["Sarvesh", "Rahul", "Kiran", "Aman"]
    assert members[0]["role"] == "admin"


def test_duplicate_membership_and_duplicate_pending_invite_rejected(client, roommates, make_user):
    response = client.post(
        f"/api/v1/groups/{roommates['group_id']}/invites",
        json={"email": "rahul@example.com"}, headers=roommates["Sarvesh"]["headers"],
    )
    assert response.status_code == 409
    self_invite = client.post(
        f"/api/v1/groups/{roommates['group_id']}/invites",
        json={"email": "sarvesh@example.com"}, headers=roommates["Sarvesh"]["headers"],
    )
    assert self_invite.status_code == 409

    newbie = make_user("Newbie")
    first = client.post(
        f"/api/v1/groups/{roommates['group_id']}/invites",
        json={"email": newbie["email"]}, headers=roommates["Sarvesh"]["headers"],
    )
    assert first.status_code == 201
    dup_pending = client.post(
        f"/api/v1/groups/{roommates['group_id']}/invites",
        json={"email": newbie["email"]}, headers=roommates["Sarvesh"]["headers"],
    )
    assert dup_pending.status_code == 409


def test_invite_unregistered_email_returns_404(client, roommates):
    response = client.post(
        f"/api/v1/groups/{roommates['group_id']}/invites",
        json={"email": "nobody@example.com"}, headers=roommates["Sarvesh"]["headers"],
    )
    assert response.status_code == 404


def test_only_admin_can_invite_or_view_group_invites(client, roommates, make_user):
    make_user("Newbie")
    response = client.post(
        f"/api/v1/groups/{roommates['group_id']}/invites",
        json={"email": "newbie@example.com"}, headers=roommates["Rahul"]["headers"],
    )
    assert response.status_code == 403
    assert client.get(
        f"/api/v1/groups/{roommates['group_id']}/invites", headers=roommates["Rahul"]["headers"]
    ).status_code == 403


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


def test_admin_can_delete_settled_group_and_cascades(client, roommates):
    gid = roommates["group_id"]
    sarvesh, rahul = roommates["Sarvesh"], roommates["Rahul"]
    # Add an expense and settle it completely so balances return to 0.
    exp = add_expense(
        client, gid, sarvesh["headers"], amount_paise=10000, paid_by=sarvesh["id"],
        participant_ids=[sarvesh["id"], rahul["id"]],
    )
    assert exp.status_code == 201
    repay = client.post(
        f"/api/v1/groups/{gid}/settlements",
        json={"paid_by": rahul["id"], "paid_to": sarvesh["id"], "amount_paise": 5000, "settled_at": "2026-11-02"},
        headers=rahul["headers"],
    )
    assert repay.status_code == 201

    deleted = client.delete(f"/api/v1/groups/{gid}", headers=sarvesh["headers"])
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/groups/{gid}", headers=sarvesh["headers"]).status_code == 404
    assert client.get("/api/v1/groups", headers=sarvesh["headers"]).json() == []


def test_admin_cannot_delete_group_with_unsettled_balances(client, roommates):
    gid = roommates["group_id"]
    sarvesh, rahul = roommates["Sarvesh"], roommates["Rahul"]
    add_expense(
        client, gid, sarvesh["headers"], amount_paise=10000, paid_by=sarvesh["id"],
        participant_ids=[sarvesh["id"], rahul["id"]],
    )
    response = client.delete(f"/api/v1/groups/{gid}", headers=sarvesh["headers"])
    assert response.status_code == 400
    assert "unsettled balances" in response.json()["detail"].lower()


def test_non_admin_and_outsider_cannot_delete_group(client, roommates, make_user):
    gid = roommates["group_id"]
    outsider = make_user("Outsider")
    assert client.delete(f"/api/v1/groups/{gid}", headers=roommates["Rahul"]["headers"]).status_code == 403
    assert client.delete(f"/api/v1/groups/{gid}", headers=outsider["headers"]).status_code == 404
