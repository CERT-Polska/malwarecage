9. Sharing objects with other collaborators
===========================================

Access control to the objects and features in MWDB is based on **groups**.

For MWDB users: group is a workspace, that allows to share the same view of uploaded objects across the various users. For MWDB administrators: group is also a way to give a specific set of permissions, depending on the role and level of trust.

In mwdb.cert.pl, we use them to group the users collaborating within the same organisation, to allow them to share their uploads and insights with other workmates or keep the information to be accessible only within trusted group of people.

Every user account is a member of at least two groups:

* user's private group, named the same as user login, which represents the exclusive user permissions.
* ``public`` group with permissions that apply to all users in MWDB.

Additionally, user can be member of ``registered`` group with permissions that apply only to non-guest users in MWDB.

Users' permissions are the sum of permissions of their groups.

Object access rules
-------------------

The basic rule of sharing model in MWDB is that **group sees only their own uploads and all descendant objects**. In that model, you have permission to see the configuration for your sample and all the information derived from that configuration. Access to parent object implies the access to its children, but not the other way around.

.. image:: ../_static/sharing-diagram.png
   :target: ../_static/sharing-diagram.png
   :alt: Sharing diagram

As an user, you need to choose which groups you represent uploading the sample. There are four options:


* **All my groups** - the default option, which shares uploaded object with all groups you belong to, excluding ``public``. That will share the object with all your workspaces to and your own private group. It means that even if you lose access to the workspace, you will still have access to your own uploads.
* **Single group...** - allows to share an object exclusively with chosen group and your own private group.
* **Everybody** - in that case, object is shared with ``public`` group, which means that everybody will have access to the uploaded object and all its descendants.
* **Only me** - your object will be shared only with your group.

Note that all options share the uploaded object with your private group.

.. image:: ../_static/upload-share-with.png
   :target: ../_static/upload-share-with.png
   :alt: Upload sharing options

.. note::

  If you are not a member of any additional group, you will see only **Everybody** and **Only me** (default) options

Current object access rules are visible in ``Shares`` box. Entries with the same identifier as currently watched object are originating from the upload of that object. Others are marked with gray background and they are inherited from the parent objects.

.. image:: ../_static/shares.png
   :target: ../_static/shares.png
   :alt: Upload sharing options

In example presented above:

* **karton** added blob (blue colored) with config as a parent
* **certpl-systems** group has access to blob because Karton is a member of that group. Uploader (Karton) decided to share uploaded object with all groups.
* **Alice** has access to blob because she added the original archive (green colored) before
* **public** group has access because Alice decided that she want to share archive with everybody
* **Chris** added Remcos sample (red colored) directly one day later, so he has got additional exclusive access to the blob. If the archive was not added to the `public` group he would still have access.

Who is who? User visibility rules
---------------------------------

Regular users are able to see only their own groups. It means that they’re able to only see these users that are members of their groups.

Joining the group, you are allowed to:

* share objects with its members
* search for their uploads using ``shared:`` and ``uploader:`` queries (but only within groups common for both users)
* see their profiles and membership in other common groups

Rules above doesn't apply to groups marked as **Role groups** e.g. ``public`` or ``registered``.

But there are few exclusions for that, when your login may be visible for all users in MWDB regardless of group membership:

* when you are the first one sharing an object with ``public`` group
* when you add a comment (login of author)

How to add new user/group?
--------------------------

Users and groups can be managed by administrator using ``Users`` and ``Groups`` views in ``Settings`` menu.

Create a new user
~~~~~~~~~~~~~~~~~

To create a new user, go to ``Settings``/``Users`` and click on ``Register user`` button.

.. image:: ../_static/admin-register-user.png
   :target: ../_static/admin-register-user.png
   :alt: Register user button

.. image:: ../_static/create-user-form.png
   :target: ../_static/create-user-form.png
   :alt: Create user form

Then fill the form with the following information:

* **Login** and **E-mail** that will be used for authentication, password recovery etc.
* **Additional info** (optional) to store additional description of user account
* **Feed quality** which is useful for plugins to determine if user account is associated with automatic feed (low) or human user (high, default).

By default - MWDB sends an e-mail to the new user with set password link, but if you have not configured SMTP service: disable **Send e-mail with set password link** first.

After clicking on ``Submit``, you will be redirected to user settings.

Using user settings, you can add user to additional groups and generate set password link. Go to the bottom of the page and click on the ``Change password`` action.

Pass the reset password link to the user to let them set a new password for an account.

Create a new group
~~~~~~~~~~~~~~~~~~

To create a new group, go to ``Settings``/``Groups`` and click on ``Create group`` button.

.. image:: ../_static/admin-register-group.png
   :target: ../_static/admin-register-group.png
   :alt: Register group button

.. image:: ../_static/create-group-form.png
   :target: ../_static/create-group-form.png
   :alt: Create group form

Set name for a new group. After clicking on ``Submit``, you will be redirected to group settings.

.. image:: ../_static/group-details.png
   :target: ../_static/group-details.png
   :alt: Group details

In group settings view, you can add members to the new group. Go to ``Access control`` if you want to set additional capabilities for group.

Group capabilities (superpowers)
--------------------------------

All groups can have additional permissions that apply to all members. MWDB by default is quite restrictive and regular user accounts are allowed only to upload samples and access the object information. That default prevents breaking the existing conventions or making potentially irreversible actions, but even in CERT.pl we don't apply such limitations for users.

You can change the capabilities for group and users, using ``Access control`` view.

.. image:: ../_static/access-control.png
   :target: ../_static/access-control.png
   :alt: Access control view

By default, ``admin`` private group has enabled all capabilities. All other groups are created with all disabled.

Each capability has its own name and scope:

* 
  **manage_users - Managing users and groups (system administration)**

  Allows to access all users and groups in MWDB. Rules described in *Who is who?* don't apply to users with that permission. Enables user to create new user accounts, new groups and change their capabilities and membership. Allows to manage attribute keys, define new ones, delete and set the group permissions for them.

* 
  **access_all_objects - Has access to all uploaded objects into system**

  Grants access to all uploaded objects in MWDB.

* 
  **sharing_with_all - Can share objects with all groups in system**

  Implies the access to the list of all group names, but without access to the membership information and management features. Allows to share object with arbitrary group in MWDB. It also allows the user to view full history of sharing an object (if the user has access to the object).

*
  **access_uploader_info - Can view who uploaded object and filter by uploader**

  Can view who uploaded object and filter by uploader. Without this capability users can filter by / see only users in their workspaces.

* 
  **adding_tags - Can add tags**

  Allows to tag objects. This feature is disabled by default, as you may want to have only tags from automated analyses.

* 
  **removing_tags - Can remove tags**

  Allows to remove tags. Tag doesn't have "owner", so user will be able to remove all tags from the object.

* 
  **adding_comments - Can add comments**

  Allows to add comments to the objects. Keep in mind that comments are public.

* 
  **removing_comments - Can remove (all) comments**

  Allows to remove **all** comments, not only these authored by the user.

* 
  **adding_parents - Can add parents**

  Allows to add new relationships by specifying object parent during upload or adding new relationship between existing objects.

*
  **removing_parents - Can remove parent of object and inherited permissions from that relation**
  
  Allows to remove relationships along with all inherited permissions.

*
  **adding_files - Can upload files**

  Enables upload of files. Enabled by default for ``registered`` group.

* 
  **adding_configs - Can upload configs**

  Enables upload of configurations. Configurations are intended to be uploaded by automated systems or trusted entities that follow the conventions.

* 
  **adding_blobs - Can upload text blobs**

  Enables upload of blobs. Blobs may have similar meaning as configurations in terms of user roles.

* 
  **reading_all_attributes - Has access to all attributes of object (including hidden)**

  With that capability, you can read all the attributes, even if you don't have ``read`` permission for that attribute key. It allows to list hidden attribute values.

* 
  **adding_all_attributes - Can add all attributes to object**

  Enables group to add all the attributes, even if it doesn't have ``set`` permission for that attribute key.

*
  **removing_attributes - Can remove attribute from objects**

  Allows to remove attribute from object. To remove attribute, you need to have ``set`` permission for key. Combined with ``adding_all_attributes``\ , allows to remove all attributes.

* 
  **unlimited_requests - API requests are not rate-limited for this group**

  Disables rate limiting for users from that group, if rate limiting feature is enabled.

* 
  **removing_objects - Can remove objects**

  Can remove all accessible objects from the MWDB. May be quite destructive, we suggest to keep that capability enabled only for ``admin`` account.

*
  **manage_profile - Can manage profile**

  Allows to change personal authentication settings like issuing/deleting own API keys and reseting password.

*
  **personalize - Can mark favorites and manage own quick queries**

  Allows to use personalization features like favorites or quick queries.

*  
  **karton_assign - Can assign existing analysis to the object**

  Allows to assign Karton analysis to the object by setting ``karton`` attribute or using dedicated API.

*
  **karton_reanalyze - Can resubmit any object for analysis**

  Can manually resubmit object to Karton.

*
  **modify_3rd_party_sharing - Can mark objects as shareable with 3rd parties**

  Can manually mark object as shareable with 3rd parties - it can be done only for objects, which are visible for this user.

User capabilities are the sum of all group capabilities. If you want to enable capability system-wide (e.g. enable all users to add tags), enable that capability for ``registered`` group or ``public`` group if you want to include guests.

In mwdb.cert.pl service - ``registered`` group is allowed to:

* add new tags
* add new comments
* add relationships (parents)
* have access to extended features provided by internal plugins

You can easily check your capabilities in ``Profile`` view.

Plugins are allowed to extend the set of capabilities in case MWDB administrator wants to require additional permission for using them.

Sharing with third parties
--------------------------

Files, configs and blobs uploaded to ``mwdb.cert.pl`` may be shared with our partners.
Sharing occurs when the object is analyzed by :ref:`karton <Karton integration guide>` - some pipelines may share data with third parties.
If you want your upload not to be shared with third parties, you can specify it during upload (with MWDB 2.9.0 or newer).

After upload, marking objects as shareable is possible only for users with ``modify_3rd_party_sharing`` capability.

If object was shareable at any time, we reserve right to share it:
   - If one object was uploaded multiple times and at least one of them was marked as shareable with third parties, 
   the object will be marked as shareable
   - Marking objects as shareable is irreversible
