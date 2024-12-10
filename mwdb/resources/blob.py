from flask import request
from werkzeug.exceptions import Conflict

from mwdb.core.capabilities import Capabilities
from mwdb.core.deprecated import DeprecatedFeature, deprecated_endpoint
from mwdb.core.plugins import hooks
from mwdb.model import TextBlob
from mwdb.model.object import ObjectTypeConflictError
from mwdb.schema.blob import (
    BlobCreateRequestSchema,
    BlobItemAndRelationsResponseSchema,
    BlobItemResponseSchema,
    BlobLegacyCreateRequestSchema,
    BlobListResponseSchema,
)

from . import loads_schema, requires_authorization, requires_capabilities
from .object import ObjectItemResource, ObjectResource, ObjectUploader


class TextBlobUploader(ObjectUploader):
    def on_created(self, object, params):
        super().on_created(object, params)
        hooks.on_created_text_blob(object)

    def on_reuploaded(self, object, params):
        super().on_reuploaded(object, params)
        hooks.on_reuploaded_text_blob(object)

    def _create_object(
        self, spec, parent, share_with, attributes, analysis_id, tags, share_3rd_party
    ):
        try:
            return TextBlob.get_or_create(
                spec["content"],
                spec["blob_name"],
                spec["blob_type"],
                share_3rd_party=share_3rd_party,
                parent=parent,
                share_with=share_with,
                attributes=attributes,
                analysis_id=analysis_id,
                tags=tags,
            )
        except ObjectTypeConflictError:
            raise Conflict("Object already exists and is not a blob")


class TextBlobResource(ObjectResource, TextBlobUploader):
    ObjectType = TextBlob
    ListResponseSchema = BlobListResponseSchema
    ItemResponseSchema = BlobItemResponseSchema

    @requires_authorization
    def get(self):
        """
        ---
        summary: Search or list blobs
        description: |
            Returns list of text blobs matching provided query,
            ordered from the latest one.
            If you want to fetch older blobs use `older_than` parameter.

            Number of returned blobs is limited by 'count' parameter
            (default value is 10).

            `Note:` Maximal number of returned blobs is limited in
            MWDB's configuration (default value is 1 000)
        security:
            - bearerAuth: []
        tags:
            - blob
        parameters:
            - in: query
              name: older_than
              schema:
                type: string
              description: |
                Fetch text blobs which are older than the object
                specified by identifier.

                Used for pagination
              required: false
            - in: query
              name: query
              schema:
                type: string
              description: Filter results using Lucene query
              required: false
            - in: query
              name: count
              schema:
                type: integer
              description: Number of objects to return
              required: false
              default: 10
        responses:
            200:
                description: List of text blobs
                content:
                  application/json:
                    schema: BlobListResponseSchema
            400:
                description: |
                    When wrong parameters were provided
                    or syntax error occurred in Lucene query
            404:
                description: When user doesn't have access to the `older_than` object
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        return super().get()

    @requires_authorization
    @requires_capabilities(Capabilities.adding_blobs)
    def post(self):
        """
        ---
        summary: Upload text blob
        description: |
            Uploads a new text blob.

            Requires `adding_blobs` capability.
        security:
            - bearerAuth: []
        tags:
            - blob
        requestBody:
            required: true
            description: Text blob to be uploaded
            content:
              application/json:
                schema: BlobCreateRequestSchema
                examples:
                  simple:
                    summary: Simple blob upload
                    value:
                      blob_name: malwarex_blob123
                      blob_type: raw_cfg
                      content: "blob contents"
                  full:
                    summary: Fully-featured configuration upload
                    value:
                      blob_name: malwarex_blob123
                      blob_type: raw_cfg
                      content: "blob contents"
                      parent: null
                      upload_as: "*"
                      metakeys:
                        - key: string
                          value: string
                      attributes:
                        - key: string
                          value: string
                      tags:
                        - tag: string
                      karton_id: string
                      karton_arguments:
                        string: string
        responses:
            200:
                description: Text blob uploaded succesfully
                content:
                  application/json:
                    schema: BlobItemResponseSchema
            403:
                description: |
                    No permissions to perform additional operations
                    (e.g. adding metakeys)
            404:
                description: Specified group doesn't exist
            409:
                description: Object exists yet but has different type
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = BlobCreateRequestSchema()
        obj = loads_schema(request.get_data(as_text=True), schema)

        return self.create_object(obj)


class TextBlobItemResource(ObjectItemResource, TextBlobUploader):
    ObjectType = TextBlob
    ItemResponseSchema = BlobItemResponseSchema
    ItemAndRelationsResponseSchema = BlobItemAndRelationsResponseSchema
    CreateRequestSchema = BlobLegacyCreateRequestSchema

    def call_specialised_remove_hook(self, text_blob):
        hooks.on_removed_text_blob(text_blob)

    @requires_authorization
    def get(self, identifier):
        """
        ---
        summary: Get blob
        description: |
            Returns text blob information and contents
        security:
            - bearerAuth: []
        tags:
            - blob
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: Blob identifier
        responses:
            200:
                description: Blob information and contents
                content:
                  application/json:
                    schema: BlobItemResponseSchema
            404:
                description: |
                    When blob doesn't exist, object is not a blob
                    or user doesn't have access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        return super().get(identifier)

    @deprecated_endpoint(DeprecatedFeature.legacy_object_upload)
    @requires_authorization
    @requires_capabilities(Capabilities.adding_blobs)
    def put(self, identifier):
        """
        ---
        summary: Upload text blob
        description: |
            Uploads a new text blob.

            Requires `adding_blobs` capability.

            Deprecated: use POST /blob method instead.
        security:
            - bearerAuth: []
        deprecated: true
        tags:
            - blob
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              default: root
              description: |
                Parent object identifier or `root` if there is no parent.

                User must have `adding_parents` capability to specify a parent object.
        requestBody:
            required: true
            content:
              multipart/form-data:
                schema:
                  type: object
                  description: |
                    Blob to be uploaded with additional parameters
                    (verbose mode)
                  properties:
                    json:
                      type: object
                      properties:
                          blob_name:
                             type: string
                          blob_type:
                             type: string
                          content:
                             type: string
                      description: JSON-encoded blob object specification
                    metakeys:
                      type: object
                      properties:
                          metakeys:
                            type: array
                            items:
                                $ref: '#/components/schemas/MetakeyItemRequest'
                      description: |
                        Attributes to be added after file upload

                        User must be allowed to set specified attribute keys.
                    upload_as:
                      type: string
                      default: '*'
                      description: |
                        Group that object will be shared with.

                        If user doesn't have `sharing_with_all` capability,
                        user must be a member of specified group
                        (unless `Group doesn't exist` error will occur).

                        If default value `*` is specified - object will be
                        exclusively shared with all user's groups excluding `public`.
                  required:
                    - json
              application/json:
                schema: BlobCreateSpecSchema
        responses:
            200:
                description: Text blob uploaded succesfully
                content:
                  application/json:
                    schema: BlobItemResponseSchema
            403:
                description: |
                    No permissions to perform additional operations
                    (e.g. adding metakeys)
            404:
                description: Specified group doesn't exist
            409:
                description: Object exists yet but has different type
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        return super().put(identifier)

    @requires_authorization
    @requires_capabilities(Capabilities.removing_objects)
    def delete(self, identifier):
        """
        ---
        summary: Delete blob
        description: |
            Removes a blob from the database along with its references.

            Requires `removing_objects` capability.
        security:
            - bearerAuth: []
        tags:
            - blob
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: Blob identifier
        responses:
            200:
                description: When blob was deleted
            403:
                description: When user doesn't have `removing_objects` capability
            404:
                description: |
                    When blob doesn't exist, object is not a blob
                    or user doesn't have access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        return super().delete(identifier)
