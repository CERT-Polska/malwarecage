import os

import jwt

from .utils import MwdbTest, ShouldRaise, admin_login, random_name


def test_profile_change_invalidate(typical_session, admin_session):
    typical_login = typical_session.userinfo["login"]
    typical_session.add_sample()

    # "Typical" shouldn't be able to create api key for admin
    with ShouldRaise(status_code=403):
        typical_session.api_key_create(admin_login(), "test key")
    api_key = typical_session.api_key_create(typical_login, "test key").json()

    typical_via_api = MwdbTest()
    typical_via_api.set_auth_token(api_key["token"])

    # All sessions OK
    typical_session.recent_samples(1)
    typical_via_api.recent_samples(1)

    admin_session.request("PUT", "/user/" + typical_login, json={"disabled": True})

    # Password-based session: invalidated, APIKey-based session: forbidden
    with ShouldRaise(status_code=403):
        typical_via_api.recent_samples(1)
    with ShouldRaise(status_code=401):
        typical_session.recent_samples(1)

    admin_session.request("PUT", "/user/" + typical_login, json={"disabled": False})

    # Password-based session: need to reauth, APIKey-based session: Ok
    typical_via_api.recent_samples(1)
    with ShouldRaise(status_code=401):
        typical_session.recent_samples(1)

    typical_session.login_as(typical_login, typical_login)
    typical_session.recent_samples(1)


def test_profile_password_change(typical_session, admin_session):
    typical_login = typical_session.userinfo["login"]
    typical_session.add_sample()

    set_pass_token = admin_session.request(
        "GET", f"/user/{typical_login}/change_password"
    )["token"]

    # Shouldn't be able to use as session token
    typical_session.set_auth_token(set_pass_token)
    with ShouldRaise(status_code=401):
        typical_session.recent_samples(1)

    typical_session.request(
        "POST",
        "/auth/change_password",
        json={"password": "very_new_password", "token": set_pass_token},
    )

    typical_session.login_as(typical_login, "very_new_password")

    # Valid only once
    with ShouldRaise(status_code=403):
        typical_session.request(
            "POST",
            "/auth/change_password",
            json={"password": typical_login, "token": set_pass_token},
        )

    set_pass_token = admin_session.request(
        "GET", f"/user/{typical_login}/change_password"
    )["token"]
    typical_session.request(
        "POST",
        "/auth/change_password",
        json={"password": typical_login, "token": set_pass_token},
    )
    typical_session.login_as(typical_login, typical_login)
    typical_session.recent_samples(1)


def test_api_key_management(typical_session, admin_session):
    typical = typical_session.clone_session()
    typical_login = typical_session.userinfo["login"]
    admin_key = admin_session.api_key_create(admin_login(), "admin key").json()
    typical_key = admin_session.api_key_create(typical_login, "typical key 1").json()
    typical_key_2 = admin_session.api_key_create(typical_login, "typical key 2").json()

    # It should be possible to create API key without sending any payload
    # Should fall back to empty name
    res = admin_session.session.post(
        admin_session.mwdb_url + f"/user/{typical_login}/api_key"
    )
    res.raise_for_status()
    assert res.json()["name"] == ""

    typical.set_auth_token(typical_key["token"])
    typical.add_sample()

    with ShouldRaise(status_code=404):
        typical.api_key_delete(admin_key["id"])
    typical.api_key_delete(typical_key["id"])

    with ShouldRaise(status_code=401):
        typical.add_sample()

    typical.set_auth_token(typical_key_2["token"])
    typical.add_sample()

    admin_session.api_key_delete(admin_key["id"])
    admin_session.api_key_delete(typical_key_2["id"])

    with ShouldRaise(status_code=401):
        typical.add_sample()


def test_jwt_legacy_api_keys(admin_session):
    secret_key = "e2e-testing-key"
    api_key_id = admin_session.api_key_create("admin", "testing-key").json()["id"]

    pre2_0_payload = {"login": "admin", "version_uid": None}
    pre2_7_payload = {"login": "admin", "api_key_id": api_key_id}

    pre2_0_token = jwt.encode(pre2_0_payload, secret_key, algorithm="HS512")
    pre2_7_token = jwt.encode(pre2_7_payload, secret_key, algorithm="HS512")

    session = MwdbTest()
    response = session.request("get", "/server")
    assert not response["is_authenticated"]

    session.set_auth_token(pre2_0_token)
    response = session.request("get", "/server")
    assert response["is_authenticated"]

    session.set_auth_token(pre2_7_token)
    response = session.request("get", "/server")
    assert response["is_authenticated"]


def test_invalid_jwt(admin_session):
    secret_key = "e2e-testing-key"
    correct_claims = jwt.decode(admin_session.auth_token, options={"verify_signature": False})

    session = MwdbTest()

    # Test if JWT is correctly validated
    incorrect_audience = {**correct_claims, "aud": "http://evil.com"}
    session.set_auth_token(jwt.encode(incorrect_audience, secret_key, algorithm="HS512"))
    response = session.request("get", "/server")
    assert not response["is_authenticated"]

    expired_jwt = {**correct_claims, "exp": correct_claims["iat"]}
    session.set_auth_token(jwt.encode(expired_jwt, secret_key, algorithm="HS512"))
    response = session.request("get", "/server")
    assert not response["is_authenticated"]

    wrong_scope_jwt = {**correct_claims, "scope": "420_no_scope"}
    session.set_auth_token(jwt.encode(wrong_scope_jwt, secret_key, algorithm="HS512"))
    response = session.request("get", "/server")
    assert not response["is_authenticated"]

    # Test missing fields to check if old token doesn't cause ISE 500
    only_login_jwt = {"login": "admin"}
    session.set_auth_token(jwt.encode(only_login_jwt, secret_key, algorithm="HS512"))
    response = session.request("get", "/server")
    assert not response["is_authenticated"]

    missing_scope_jwt = {**correct_claims}
    del missing_scope_jwt["scope"]
    session.set_auth_token(jwt.encode(missing_scope_jwt, secret_key, algorithm="HS512"))
    response = session.request("get", "/server")
    assert not response["is_authenticated"]

    missing_sub_jwt = {**correct_claims}
    del missing_sub_jwt["sub"]
    session.set_auth_token(jwt.encode(missing_sub_jwt, secret_key, algorithm="HS512"))
    response = session.request("get", "/server")
    assert not response["is_authenticated"]


def test_group_invite(admin_session):
    alice_username = random_name()
    bob_username = random_name()
    charlie_username = random_name()
    group_name = random_name()
    admin_session.register_user(alice_username, "AliceAlice")
    admin_session.register_user(bob_username, "BobBobBob")
    admin_session.register_user(charlie_username, "CharlieCharlie")
    admin_session.create_group(group_name)
    admin_session.add_member(group_name, alice_username)
    # set Alice as group_admin
    admin_session.update_group_admin(group_name, alice_username, True)

    alice_session = MwdbTest()
    bob_session = MwdbTest()
    charlie_session = MwdbTest()
    alice_session.login_as(alice_username, "AliceAlice")
    bob_session.login_as(bob_username, "BobBobBob")
    charlie_session.login_as(charlie_username, "CharlieCharlie")

    data = alice_session.request_group_invite_link(group_name, bob_username)
    token = data["link"].split("=")[-1]

    with ShouldRaise(403):
        charlie_session.join_group_with_invitation_link(token)

    bob_session.join_group_with_invitation_link(token)

    members = admin_session.get_group(group_name)["users"]
    assert bob_username in members
