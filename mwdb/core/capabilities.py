class Capabilities(object):
    # Can create/update users and groups
    manage_users = "manage_users"
    # All new uploaded objects are automatically shared with this group
    access_all_objects = "access_all_objects"
    # Can share objects with all groups, have access to complete list of groups
    sharing_with_all = "sharing_with_all"
    # Can view who uploaded object and filter by uploader
    access_uploader_info = "access_uploader_info"
    # Can add tags
    adding_tags = "adding_tags"
    # Can remove tags
    removing_tags = "removing_tags"
    # Can add comments
    adding_comments = "adding_comments"
    # Can remove comments
    removing_comments = "removing_comments"
    # Can add parents
    adding_parents = "adding_parents"
    # Can remove parents and inherited permissions from relation
    removing_parents = "removing_parents"
    # Can read all attributes, regardless of ACLs
    reading_all_attributes = "reading_all_attributes"
    # Can set all attributes, regardless of ACLs
    adding_all_attributes = "adding_all_attributes"
    # Can remove attributes from objects
    removing_attributes = "removing_attributes"
    # Can upload files
    adding_files = "adding_files"
    # Can upload configs
    adding_configs = "adding_configs"
    # Can upload blobs
    adding_blobs = "adding_blobs"
    # Requests are not rate-limited for members of this group
    unlimited_requests = "unlimited_requests"
    # Can remove objects
    removing_objects = "removing_objects"
    # Can manage own profile (add API keys, change a password)
    manage_profile = "manage_profile"
    # Can personalize own profile (mark as favorite, manage quick queries)
    personalize = "personalize"
    # Can assign existing Karton analysis to the object
    karton_assign = "karton_assign"
    # Can resubmit object to Karton
    karton_reanalyze = "karton_reanalyze"
    # Can remove Karton analysis from the object
    karton_unassign = "karton_unassign"
    # Can mark object as shareable with 3rd parties
    modify_3rd_party_sharing = "modify_3rd_party_sharing"
    # Can access Prometheus metrics
    access_prometheus_metrics = "access_prometheus_metrics"

    @classmethod
    def all(cls):
        return [
            k
            for k in cls.__dict__.keys()
            if not k.startswith("__") and type(cls.__dict__[k]) is str
        ]
