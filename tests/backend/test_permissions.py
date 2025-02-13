from .relations import *
from .utils import *


def test_manage_users(admin_session):
    testCase = RelationTestCase(admin_session)

    Alice = testCase.new_user("Alice")
    Bob = testCase.new_user("Bob", capabilities=["manage_users"])

    def request(*args, **kwargs):
        with ShouldRaise(status_code=403):
            Alice.session.request(*args, **kwargs)
        Bob.session.request(*args, **kwargs)

    user_login = random_name()
    user_email = random_name() + "@" + random_name() + ".com"
    group_name = random_name()

    request("GET", "/user")
    request("GET", "/user/"+admin_login())
    request("POST", "/user/{}".format(user_login), json={"email": user_email, "additional_info": "Test user"})
    request("PUT", "/user/{}".format(user_login), json={"email": user_email, "additional_info": "Test user"})

    request("GET", "/user/{}/change_password".format(admin_login()))

    request("GET", "/group")
    request("GET", "/group/{}".format(admin_login()))
    request("POST", "/group/{}".format(group_name), json={"capabilities": []})
    request("PUT", "/group/{}".format(group_name), json={"capabilities": []})


def test_access_all_objects(admin_session):
    testCase = RelationTestCase(admin_session)

    testCase.new_user("Alice")
    Bob = testCase.new_user("Bob", capabilities=["access_all_objects"])

    SampleA = testCase.new_sample("SampleA")
    SampleB = testCase.new_sample("SampleB")
    SampleC = testCase.new_sample("SampleC")

    SampleA([
        SampleB(should_access=[Bob]),
        SampleC(should_access=[Bob])
    ], should_access=[Bob]).test()


def test_sharing_with_all(admin_session):
    testCase = RelationTestCase(admin_session)

    Alice = testCase.new_user("Alice")
    Bob = testCase.new_user("Bob", capabilities=["sharing_with_all"])

    Sample = testCase.new_sample("Sample")
    Sample.create(Bob)

    Bob.session.request("GET", "/object/{}/share".format(Sample.dhash))

    Sample.should_not_access(Alice)

    Bob.session.request("PUT", "/object/{}/share".format(Sample.dhash), json={"group": Alice.identity})

    Sample.should_access(Alice)


def test_adding_tags(admin_session):
    testCase = RelationTestCase(admin_session)

    Alice = testCase.new_user("Alice")
    Bob = testCase.new_user("Bob", capabilities=["adding_tags"])

    Sample = testCase.new_sample("Sample")
    Sample.create(Alice)
    Sample.create(Bob)

    with ShouldRaise(status_code=403):
        Alice.session.add_tag(Sample.dhash, "tag123")

    assert {"tag": "tag123"} not in admin_session.get_tags(Sample.dhash)

    Bob.session.add_tag(Sample.dhash, "tag123")

    assert {"tag": "tag123"} in admin_session.get_tags(Sample.dhash)


def test_removing_tags(admin_session):
    testCase = RelationTestCase(admin_session)

    Alice = testCase.new_user("Alice")
    Bob = testCase.new_user("Bob", capabilities=["removing_tags"])

    Sample = testCase.new_sample("Sample")
    Sample.create(Alice)
    Sample.create(Bob)

    admin_session.add_tag(Sample.dhash, "tag123")

    with ShouldRaise(status_code=403):
        Alice.session.delete_tag(Sample.dhash, "tag123")

    assert {"tag": "tag123"} in admin_session.get_tags(Sample.dhash)

    Bob.session.delete_tag(Sample.dhash, "tag123")

    assert {"tag": "tag123"} not in admin_session.get_tags(Sample.dhash)


def test_adding_comments(admin_session):
    testCase = RelationTestCase(admin_session)

    Alice = testCase.new_user("Alice")
    Bob = testCase.new_user("Bob", capabilities=["adding_comments"])

    Sample = testCase.new_sample("Sample")
    Sample.create(Alice)
    Sample.create(Bob)

    with ShouldRaise(status_code=403):
        Alice.session.add_comment(Sample.dhash, "comment123")

    assert not list(filter(lambda c: c["comment"] == "comment123", admin_session.get_comments(Sample.dhash)))

    Bob.session.add_comment(Sample.dhash, "comment123")

    assert list(filter(lambda c: c["comment"] == "comment123", admin_session.get_comments(Sample.dhash)))


def test_removing_comments(admin_session):
    testCase = RelationTestCase(admin_session)

    Alice = testCase.new_user("Alice")
    Bob = testCase.new_user("Bob", capabilities=["removing_comments"])

    Sample = testCase.new_sample("Sample")
    Sample.create(Alice)
    Sample.create(Bob)

    comment_id = admin_session.add_comment(Sample.dhash, "comment123")["id"]

    with ShouldRaise(status_code=403):
        Alice.session.delete_comment(Sample.dhash, comment_id)

    assert list(filter(lambda c: c["comment"] == "comment123", admin_session.get_comments(Sample.dhash)))

    Bob.session.delete_comment(Sample.dhash, comment_id)

    assert not list(filter(lambda c: c["comment"] == "comment123", admin_session.get_comments(Sample.dhash)))


def test_adding_parents(admin_session):
    testCase = RelationTestCase(admin_session)

    Alice = testCase.new_user("Alice")
    Bob = testCase.new_user("Bob", capabilities=["adding_parents"])

    SampleA = testCase.new_sample("Sample")
    SampleB = testCase.new_sample("Sample")
    SampleA.create(Alice)
    SampleA.create(Bob)

    with ShouldRaise(status_code=403):
        SampleB.create(Alice, SampleA)

    assert admin_session.get_sample(SampleB.dhash)["parents"] == []

    SampleB.create(Bob, SampleA)

    assert admin_session.get_sample(SampleB.dhash)["parents"] != []


def test_removing_objects(admin_session):
    testCase = RelationTestCase(admin_session)

    Alice = testCase.new_user("Alice")
    Bob = testCase.new_user("Bob", capabilities=["removing_objects"])
    Charlie = testCase.new_user("Charlie", capabilities=["removing_objects"])

    SampleA = testCase.new_sample("Sample")
    SampleB = testCase.new_sample("Sample")

    SampleA.create(Alice)
    SampleA.create(Bob)
    SampleB.create(Bob)

    SampleA([
        SampleB()
    ]).create()

    admin_session.add_tag(SampleA.dhash, "tag123")
    admin_session.add_tag(SampleB.dhash, "tag123")

    with ShouldRaise(status_code=403):
        Alice.session.remove_object(SampleA.dhash)

    Bob.session.get_sample(SampleA.dhash)

    with ShouldRaise(status_code=404):
        Charlie.session.remove_object(SampleA.dhash)

    Bob.session.get_sample(SampleA.dhash)

    Bob.session.remove_object(SampleA.dhash)

    with ShouldRaise(status_code=404):
        Bob.session.get_sample(SampleA.dhash)

    Bob.session.get_sample(SampleB.dhash)

    assert {"tag": "tag123"} in admin_session.get_tags(SampleB.dhash)


def test_removing_object_with_comments(admin_session):
    testCase = RelationTestCase(admin_session)
    sample = testCase.new_sample("Sample")
    sample.create()

    admin_session.add_comment(sample.dhash, "comment1")
    admin_session.add_comment(sample.dhash, "comment2")
    admin_session.add_comment(sample.dhash, "comment3")
    admin_session.remove_object(sample.dhash)

    with ShouldRaise(status_code=404):
        admin_session.get_sample(sample.dhash)
