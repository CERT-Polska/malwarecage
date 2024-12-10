from flask import Response, g, request
from werkzeug.exceptions import BadRequest, Conflict, Forbidden, NotFound, Unauthorized

from mwdb.core.capabilities import Capabilities
from mwdb.core.deprecated import DeprecatedFeature, deprecated_endpoint
from mwdb.core.plugins import hooks
from mwdb.core.service import Resource
from mwdb.model import File
from mwdb.model.file import EmptyFileError
from mwdb.model.object import ObjectTypeConflictError
from mwdb.schema.file import (
    FileCreateRequestSchema,
    FileDownloadTokenResponseSchema,
    FileItemAndRelationsResponseSchema,
    FileItemResponseSchema,
    FileLegacyCreateRequestSchema,
    FileListResponseSchema,
)

from . import load_schema, requires_authorization, requires_capabilities
from .object import ObjectItemResource, ObjectResource, ObjectUploader


class FileUploader(ObjectUploader):
    def on_created(self, object, params):
        super().on_created(object, params)
        hooks.on_created_file(object)

    def on_reuploaded(self, object, params):
        super().on_reuploaded(object, params)
        hooks.on_reuploaded_file(object)

    def _create_object(
        self, spec, parent, share_with, attributes, analysis_id, tags, share_3rd_party
    ):
        try:
            return File.get_or_create(
                request.files["file"].filename,
                request.files["file"].stream,
                share_3rd_party=share_3rd_party,
                parent=parent,
                share_with=share_with,
                attributes=attributes,
                analysis_id=analysis_id,
                tags=tags,
            )
        except ObjectTypeConflictError:
            raise Conflict("Object already exists and is not a file")
        except EmptyFileError:
            raise BadRequest("File cannot be empty")


class FileResource(ObjectResource, FileUploader):
    ObjectType = File
    ListResponseSchema = FileListResponseSchema
    ItemResponseSchema = FileItemResponseSchema

    @requires_authorization
    def get(self):
        """
        ---
        summary: Search or list files
        description: |
            Returns list of files matching provided query,
            ordered from the latest one.
            If you want to fetch older files use `older_than` parameter.

            Number of returned files is limited by 'count' parameter
            (default value is 10).

            `Note:` Maximal number of returned files is limited in
            MWDB's configuration (default value is 1 000)
        security:
            - bearerAuth: []
        tags:
            - file
        parameters:
            - in: query
              name: older_than
              schema:
                type: string
              description: |
                Fetch files which are older than the object specified by identifier.

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
                description: List of files
                content:
                  application/json:
                    schema: FileListResponseSchema
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
    @requires_capabilities(Capabilities.adding_files)
    def post(self):
        """
        ---
        summary: Upload file
        description: |
            Uploads a new file.

            Requires `adding_files` capability.
        security:
            - bearerAuth: []
        tags:
            - file
        requestBody:
            required: true
            content:
              multipart/form-data:
                schema:
                  type: object
                  properties:
                    file:
                      type: string
                      format: binary
                      description: File contents to be uploaded
                    options:
                      type: object
                      description: |
                        Additional upload options
                      properties:
                        parent:
                          type: string
                        karton_id:
                          type: string
                        karton_arguments:
                          type: object
                          additionalProperties:
                            type:string
                        attributes:
                          type: array
                          items:
                            $ref: '#/components/schemas/AttributeItemRequest'
                        metakeys:
                          type: array
                          items:
                            $ref: '#/components/schemas/MetakeyItemRequest'
                        tags:
                          type: array
                          items:
                            $ref: '#/components/schemas/TagRequest'
                        upload_as:
                          type: string
                      schema: ObjectCreateRequestSchemaBase
                  required:
                    - file
        responses:
            200:
                description: Information about uploaded file
                content:
                  application/json:
                    schema: FileItemResponseSchema
            403:
                description: |
                    No permissions to perform additional operations
                    (e.g. adding parent, attributes)
            404:
                description: |
                    One of attribute keys doesn't exist
                    or user doesn't have permission to set it.

                    Specified `upload_as` group doesn't exist
                    or user doesn't have permission to share objects with that group
            409:
                description: Object exists yet but has different type
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        schema = FileCreateRequestSchema()
        obj = load_schema(request.form.to_dict(), schema)

        return self.create_object(obj["options"])


class FileItemResource(ObjectItemResource, FileUploader):
    ObjectType = File
    ItemResponseSchema = FileItemResponseSchema
    ItemAndRelationsResponseSchema = FileItemAndRelationsResponseSchema
    CreateRequestSchema = FileLegacyCreateRequestSchema

    def call_specialised_remove_hook(self, file):
        hooks.on_removed_file(file)

    @requires_authorization
    def get(self, identifier):
        """
        ---
        summary: Get file information
        description: |
            Returns information about file.
        security:
            - bearerAuth: []
        tags:
            - file
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: File identifier (SHA256/SHA512/SHA1/MD5)
            - in: query
              name: exclude_relations
              schema:
                type: integer
              description: |
                If set, results doesn't include relations
                which will be default behavior on next major release of MWDB
              required: false
              default: 0
        responses:
            200:
                description: Information about file
                content:
                  application/json:
                    schema: FileItemResponseSchema
            404:
                description: |
                    When file doesn't exist, object is not a file
                    or user doesn't have access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        return super().get(identifier)

    @deprecated_endpoint(DeprecatedFeature.legacy_object_upload)
    @requires_authorization
    @requires_capabilities(Capabilities.adding_files)
    def post(self, identifier):
        """
        ---
        summary: Upload file
        description: |
            Uploads a new file.

            Requires `adding_files` capability.

            Deprecated: use POST /file instead.
        security:
            - bearerAuth: []
        deprecated: true
        tags:
            - file
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              default: 'root'
              description: |
                Parent object identifier or `root` if there is no parent.

                User must have `adding_parents` capability to specify a parent object.
        requestBody:
            required: true
            content:
              multipart/form-data:
                schema:
                  type: object
                  properties:
                    file:
                      type: string
                      format: binary
                      description: File contents to be uploaded
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
                    - file
        responses:
            200:
                description: Information about uploaded file
                content:
                  application/json:
                    schema: FileItemResponseSchema
            403:
                description: |
                    No permissions to perform additional operations
                    (e.g. adding parent, attributes)
            404:
                description: |
                    One of attribute keys doesn't exist or user doesn't have
                    permission to set it.

                    Specified `upload_as` group doesn't exist or user doesn't have
                    permission to share objects with that group
            409:
                description: Object exists yet but has different type
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        return super().post(identifier)

    @requires_authorization
    @requires_capabilities(Capabilities.removing_objects)
    def delete(self, identifier):
        """
        ---
        summary: Delete file
        description: |
            Removes a file from the database along with its references.

            Requires `removing_objects` capability.
        security:
            - bearerAuth: []
        tags:
            - file
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: File identifier (SHA256/SHA512/SHA1/MD5)
        responses:
            200:
                description: When file was deleted
            403:
                description: When user doesn't have `removing_objects` capability
            404:
                description: |
                    When file doesn't exist, object is not a file
                    or user doesn't have access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        return super().delete(identifier)


class FileDownloadResource(Resource):
    def get(self, identifier):
        """
        ---
        summary: Download file
        description: |
            Returns file contents.

            Optionally accepts file download token to get
            the file via direct link (without Authorization header)
        security:
            - bearerAuth: []
        tags:
            - file
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: File identifier (SHA256/SHA512/SHA1/MD5)
            - in: query
              name: token
              schema:
                type: string
              description: |
                File download token for direct link purpose
              required: false
            - in: query
              name: obfuscate
              schema:
                type: string
              description: |
                Obfuscated response flag to avoid AV detection on preview
              required: false
        responses:
            200:
                description: File contents
                content:
                  application/octet-stream:
                    schema:
                      type: string
                      format: binary
            403:
                description: |
                    When file download token is no longer valid
                    or was generated for different object
            404:
                description: |
                    When file doesn't exist, object is not a file
                    or user doesn't have access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        access_token = request.args.get("token")
        obfuscate = request.args.get("obfuscate")

        if access_token:
            file_obj = File.get_by_download_token(access_token)
            if not file_obj:
                raise Forbidden("Download token expired, please re-request download.")
            if not (
                file_obj.sha1 == identifier
                or file_obj.sha256 == identifier
                or file_obj.sha512 == identifier
                or file_obj.md5 == identifier
            ):
                raise Forbidden(
                    "Download token doesn't apply to the chosen object. "
                    "Please re-request download."
                )
        else:
            if not g.auth_user:
                raise Unauthorized("Not authenticated.")
            file_obj = File.access(identifier)
            if file_obj is None:
                raise NotFound("Object not found")

        if obfuscate == "1":
            return Response(
                file_obj.iterate_obfuscated(),
                content_type="application/octet-stream",
                headers={
                    "Content-disposition": f"attachment; filename={file_obj.sha256}"
                },
            )
        else:
            return Response(
                file_obj.iterate(),
                content_type="application/octet-stream",
                headers={
                    "Content-disposition": f"attachment; filename={file_obj.sha256}"
                },
            )

    @requires_authorization
    def post(self, identifier):
        """
        ---
        summary: Generate file download token
        description: |
            Returns download token for given file.
        security:
            - bearerAuth: []
        tags:
            - file
        parameters:
            - in: path
              name: identifier
              description: Requested file identifier (SHA256/MD5/SHA1/SHA512)
              schema:
                type: string
        responses:
            200:
                description: File download token, valid for 60 seconds
                content:
                  application/json:
                    schema: FileDownloadTokenResponseSchema
            404:
                description: |
                    When file doesn't exist, object is not a file
                    or user doesn't have access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        file = File.access(identifier)
        if file is None:
            raise NotFound("Object not found")

        download_token = file.generate_download_token()
        schema = FileDownloadTokenResponseSchema()
        return schema.dump({"token": download_token})


class FileDownloadZipResource(Resource):
    def get(self, identifier):
        """
        ---
        summary: Download zipped file
        description: |
            Returns zipped file contents, encrypted using password "infected".

            Optionally accepts file download token to get
            the zipped file via direct link (without Authorization header)
        security:
            - bearerAuth: []
        tags:
            - file
        parameters:
            - in: path
              name: identifier
              schema:
                type: string
              description: File identifier (SHA256/SHA512/SHA1/MD5)
            - in: query
              name: token
              schema:
                type: string
              description: |
                Zipped file download token for direct link purpose
              required: false
        responses:
            200:
                description: Zipped file contents
                content:
                  application/octet-stream:
                    schema:
                      type: string
                      format: binary
            403:
                description: |
                    When file download token is no longer valid
                    or was generated for different object
            404:
                description: |
                    When file doesn't exist, object is not a file
                    or user doesn't have access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        access_token = request.args.get("token")

        if access_token:
            file_obj = File.get_by_download_token(access_token)
            if not file_obj:
                raise Forbidden("Download token expired, please re-request download.")
            if not (
                file_obj.sha1 == identifier
                or file_obj.sha256 == identifier
                or file_obj.sha512 == identifier
                or file_obj.md5 == identifier
            ):
                raise Forbidden(
                    "Download token doesn't apply to the chosen object. "
                    "Please re-request download."
                )
        else:
            if not g.auth_user:
                raise Unauthorized("Not authenticated.")
            file_obj = File.access(identifier)
            if file_obj is None:
                raise NotFound("Object not found")

        return Response(
            file_obj.zip_file(),
            content_type="application/octet-stream",
            headers={"Content-disposition": f"attachment; filename={file_obj.sha256}"},
        )

    @requires_authorization
    def post(self, identifier):
        """
        ---
        summary: Generate zip file download token
        description: |
            Returns download token for given zipped file.
        security:
            - bearerAuth: []
        tags:
            - file
        parameters:
            - in: path
              name: identifier
              description: Requested file identifier (SHA256/MD5/SHA1/SHA512)
              schema:
                type: string
        responses:
            200:
                description: File download token, valid for 60 seconds
                content:
                  application/json:
                    schema: FileDownloadTokenResponseSchema
            404:
                description: |
                    When file doesn't exist, object is not a file
                    or user doesn't have access to this object.
            503:
                description: |
                    Request canceled due to database statement timeout.
        """
        file = File.access(identifier)
        if file is None:
            raise NotFound("Object not found")

        download_token = file.generate_download_token()
        schema = FileDownloadTokenResponseSchema()
        return schema.dump({"token": download_token})
