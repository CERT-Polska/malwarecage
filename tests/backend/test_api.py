import pytest
import requests
from dateutil.parser import parse

from .relations import RelationTestCase
from .utils import rand_string, ShouldRaise


def test_login(admin_session):
    res = admin_session.userinfo
    assert 'token' in res and res['login'] == 'admin'


def test_add_sample(admin_session):
    filename = rand_string()
    file_content = rand_string()

    res = admin_session.add_sample(filename, file_content)

    assert res['file_name'] == filename
    assert res['file_size'] == len(file_content)
    assert res['parents'] == []
    assert res['children'] == []
    assert res['tags'] == []
    parse(res['upload_time'])


def test_get_sample(admin_session):
    filename = rand_string()
    file_content = rand_string()

    sample = admin_session.add_sample(filename, file_content)
    res = admin_session.get_sample(sample['id'])

    assert res['file_name'] == filename
    assert res['file_size'] == len(file_content)
    assert res['parents'] == []
    assert res['children'] == []
    assert res['tags'] == []
    parse(res['upload_time'])


def test_get_sample_2_times_uploaded(admin_session):
    filename_1 = rand_string()
    filename_2 = rand_string()
    file_content = rand_string()

    sample_1 = admin_session.add_sample(filename_1, file_content)
    admin_session.add_sample(filename_2, file_content)
    res = admin_session.get_sample(sample_1['id'])

    assert res['file_name'] == filename_1
    assert res['alt_names'] == [filename_2]
    parse(res['upload_time'])


def test_search(admin_session):
    filename = rand_string()
    file_content = rand_string()

    sample = admin_session.add_sample(filename, file_content)
    allowed_names = [
        sample['id'], sample['md5'], sample['sha1'],
        sample['sha256'], sample['sha256'].upper()
    ]

    for name in allowed_names:
        res = admin_session.get_sample(name)
        assert res['id'] == sample['id']
        assert res['file_name'] == filename
        assert res['file_size'] == len(file_content)
        parse(res['upload_time'])


@pytest.mark.parametrize('num_parents,num_children', [
    (1, 1),
    (1, 2),
    (2, 1),
    (2, 2)
])
def test_relations(num_parents, num_children, admin_session):
    parents_id = set()
    children_id = set()

    for p in range(num_parents):
        parent = admin_session.add_sample()
        parents_id.add(parent['id'])

    for c in range(num_children):
        content = rand_string()
        for p_hash in parents_id:
            child_res = admin_session.add_sample(content, content, p_hash)
            children_id.add(child_res['id'])

    for p_hash in parents_id:
        parent = admin_session.get_sample(p_hash)
        assert len(parent['children']) == num_children
        for c in children_id:
            assert c in [x['id'] for x in parent['children']]

    for c_hash in children_id:
        child = admin_session.get_sample(c_hash)
        assert len(child['parents']) == num_parents
        for p in parents_id:
            assert p in [x['id'] for x in child['parents']]


def test_add_tags(admin_session):
    sample = admin_session.add_sample()

    tags_expected = [rand_string() for _ in range(4)]
    for tag in tags_expected:
        admin_session.add_tag(sample['id'], tag)

    tags_response = admin_session.get_tags(sample['id'])
    tags_returned = [t['tag'] for t in tags_response if not t["tag"].startswith("misc:")]

    assert len(tags_returned) == len(tags_expected)
    assert all([t in tags_returned for t in tags_expected])


def test_delete_tags(admin_session):
    tag1 = 'tag1'
    tag2 = 'tag2'

    sample = admin_session.add_sample()
    identifier = sample['id']
    admin_session.add_tag(identifier, tag1)
    admin_session.add_tag(identifier, tag2)
    admin_session.delete_tag(identifier, tag1)

    tags = [t['tag'] for t in admin_session.get_tags(identifier) if not t["tag"].startswith("misc:")]
    assert len(tags) == 1
    assert tag1 not in tags
    assert tag2 in tags


@pytest.mark.parametrize('num_comments', [
    0,
    1,
    5
])
def test_comment(num_comments, admin_session):
    expected_comments = [rand_string() for _ in range(num_comments)]
    sample = admin_session.add_sample()
    identifier = sample['id']

    for c in expected_comments:
        admin_session.add_comment(identifier, c)

    comments = admin_session.get_comments(identifier)
    assert len(comments) == num_comments
    assert all([c['comment'] in expected_comments for c in comments])


def test_delete_comment(admin_session):
    comment_1 = rand_string()
    comment_2 = rand_string()
    
    file_name_1 = rand_string()
    file_name_2 = rand_string()
    content_1 = rand_string()
    content_2 = rand_string()
    sample_1 = admin_session.add_sample(file_name_1, content_1)
    sample_2 = admin_session.add_sample(file_name_2, content_2)
    
    identifier_1 = sample_1['id']
    identifier_2 = sample_2['id']
    
    comment_added_1 = admin_session.add_comment(identifier_1, comment_1)
    comment_added_2 = admin_session.add_comment(identifier_2, comment_2)
    
    # delete comment associated with object
    admin_session.delete_comment(identifier_1, comment_added_1['id'])
    
    # delete comment not associated with object    
    with ShouldRaise(status_code=404):
        admin_session.delete_comment(identifier_1, comment_added_2['id'])


def test_download_sample(admin_session):
    expected = rand_string()
    sample = admin_session.add_sample(content=expected)

    downloaded = admin_session.download_file(sample['id'])
    assert downloaded.decode() == expected


def test_download_sample_with_token(admin_session):
    expected = rand_string()
    sample = admin_session.add_sample(content=expected)

    token = admin_session.get_download_token(sample['id'])
    r = requests.get(
        admin_session.mwdb_url + f'/file/{sample["id"]}/download',
        params={
            "token": token
        }
    )
    r.raise_for_status()
    downloaded = r.text

    assert downloaded == expected


def test_object_conflict(admin_session):
    name = rand_string()
    content = rand_string()
    admin_session.add_sample(name, content)
    with ShouldRaise(status_code=409):
        admin_session.add_blob(None, name, name, content)


def test_zero_starting_crc32(admin_session):
    name = rand_string()
    content = b'\xf7\xb8\xb4\xab\x6b\x35\x31\x8a'
    sample = admin_session.add_sample(name, content)
    assert sample["crc32"] == "000d06ec"


def test_user_delete(admin_session):
    # Make user and use it to comment new sample
    case = RelationTestCase(admin_session)
    alice = case.new_user("Alice", capabilities=["adding_comments", "manage_users"])
    # Upload sample
    sample = case.new_sample("Sample")
    sample.create(alice)
    # Set comment for sample
    alice.session.add_comment(sample.dhash, "random comment")
    # Register new user using Alice
    bob_identity = rand_string(16)
    alice.session.register_user(bob_identity, bob_identity)
    # Issue new API key for bob
    bob_api_key_resp = alice.session.api_key_create(bob_identity, "new api key").json()
    bob_api_key_id = bob_api_key_resp["id"]
    # Then try to remove that user
    admin_session.remove_user(alice.identity)
    # Bob should still exist
    bob_data = admin_session.get_user(bob_identity)
    assert bob_data["registrar_login"] is None
    assert bob_data["api_keys"][0]["id"] == bob_api_key_id
    # Object should be still reachable
    admin_session.get_sample(sample.dhash)
    # And should still have one comment (with nulled author)
    comments = admin_session.get_comments(sample.dhash)
    assert len(comments) == 1
    assert comments[0]["comment"] == "random comment"
    assert comments[0]["author"] is None
