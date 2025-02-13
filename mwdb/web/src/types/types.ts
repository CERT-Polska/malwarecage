import { AxiosError } from "axios";

export enum Capability {
    manageUsers = "manage_users",
    accessAllObjects = "access_all_objects",
    sharingWithAll = "sharing_with_all",
    accessUploaderInfo = "access_uploader_info",
    addingTags = "adding_tags",
    removingTags = "removing_tags",
    addingComments = "adding_comments",
    removingComments = "removing_comments",
    addingParents = "adding_parents",
    removingParents = "removing_parents",
    readingAllAttributes = "reading_all_attributes",
    addingAllAttributes = "adding_all_attributes",
    removingAttributes = "removing_attributes",
    addingFiles = "adding_files",
    addingConfigs = "adding_configs",
    addingBlobs = "adding_blobs",
    unlimitedRequests = "unlimited_requests",
    removingObjects = "removing_objects",
    manageProfile = "manage_profile",
    personalize = "personalize",
    kartonAssign = "karton_assign",
    kartonReanalyze = "karton_reanalyze",
    removingKarton = "karton_unassign",
    modify3rdPartySharing = "modify_3rd_party_sharing",
    accessPrometheusMetrics = "access_prometheus_metrics",
}

export type User = {
    login: string;
    name?: string;
    groups: Group[];
    capabilities: Capability[];
    additional_info?: string;
    api_keys?: ApiKey[];
    disabled?: boolean;
    email?: string;
    feed_quality?: FeedQuality;
    pending?: boolean;
    requested_on?: string;
    provider?: null | string;
    token?: string;
    logged_on?: string;
    registered_on?: string;
    registrar_login?: string;
    set_password_on?: string;
};

export type Group = {
    admins: string[];
    capabilities: Capability[];
    default: boolean;
    immutable: boolean;
    name: string;
    private: boolean;
    users: string[];
    workspace: boolean;
};

export type ObjectType = "file" | "blob" | "config" | "object";

export type ObjectLegacyType = "file" | "static_config" | "text_blob";

export type Attribute = {
    key: string;
    id: number;
    value: string;
};

export type AttributeDefinition = {
    description: string;
    example_value: string;
    hidden: boolean;
    key: string;
    label: string;
    rich_template: string;
    url_template: string;
};

export type Tag = {
    tag: string;
};

export type RelatedObject = {
    id: string;
    tags: Tag[];
    type: ObjectLegacyType;
    upload_time: string;
};

export type ConfigType = "static" | "dynamic";

type ObjectCommonData = {
    attributes: Attribute[];
    children: RelatedObject[];
    shares: Share[];
    favorite: boolean;
    id: string;
    parents: RelatedObject[];
    tags: Tag[];
    upload_time: string;
    share_3rd_party: boolean;
    analyses?: KartonAnalysis[];
    latest_config: {
        id: number;
        family: string;
    };
    comments: Comment[];
};

export type ObjectData = ObjectCommonData & {
    alt_names: string[];
    crc32: string;
    file_name: string;
    file_size: number;
    file_type: string;
    md5: string;
    sha1: string;
    sha256: string;
    sha512: string;
    ssdeep: string;
    type: "file";
};

export type ConfigData = ObjectCommonData & {
    cfg: object;
    config_type: ConfigType;
    family: string;
    type: "static_config";
};

export type BlobData = ObjectCommonData & {
    blob_name: string;
    blob_size: number;
    blob_type: string;
    content: string;
    last_seen: string;
    type: "text_blob";
};

export type ObjectListItem = {
    id: string;
    tags: Tag[];
    type: ObjectLegacyType;
    upload_time: string;
};

export type FileListItem = {
    file_name: string;
    file_size: number;
    file_type: string;
    id: string;
    md5: string;
    sha1: string;
    sha256: string;
    tags: Tag[];
    type: "file";
    upload_time: string;
};

export type ConfigListItem = {
    config_type: ConfigType;
    family: string;
    id: string;
    tags: Tag[];
    type: "static_config";
    upload_time: string;
};

export type BlobListItem = {
    blob_name: string;
    blob_size: number;
    blob_type: string;
    id: string;
    last_seen: string;
    type: "text_blob";
    tags: Tag[];
};

export type Comment = {
    author: string;
    comment: string;
    id: number;
    timestamp: number;
};

export type Share = {
    access_reason: string;
    access_time: string;
    group_name: string;
    reason_type: string;
    related_object_dhash: string;
    related_object_type: ObjectType;
    related_user_login: string;
};

export type Query = {
    id: number;
    name: string;
    query: string;
    type: ObjectType;
};

export type ApiKey = {
    id: string;
    issued_on: string;
    issuer_login: string;
    name: string;
    token?: string;
};

export type Family = {
    count: number;
    family: string;
    last_upload: string;
};

export type KartonAnalysis = {
    status: string;
    id: number;
    processing_in: Record<
        string,
        {
            status: string[];
            received_from: string[];
        }
    >;
    arguments: Record<string, string>;
    last_update: string;
};

export type AxiosServerErrors = AxiosError<{
    message?: string;
    errors?: Record<string, string>;
}>;

export type GenericOrJSX<T> = T | JSX.Element;

export type ServerInfo = {
    request_timeout: number;
    is_karton_enabled: boolean;
    statement_timeout: number;
    is_oidc_enabled: boolean;
    is_authenticated: boolean;
    is_maintenance_set: boolean;
    recaptcha_site_key: string;
    file_upload_timeout: number;
    server_version: string;
    is_registration_enabled: boolean;
    instance_name: string;
    remotes: string[];
    is_3rd_party_sharing_consent_enabled: boolean;
};

export type Permission = {
    read: boolean;
    set: boolean;
};

export type Provider = {
    name: string;
    client_id: string;
    client_secret: string;
    authorization_endpoint: string;
    token_endpoint: string;
    userinfo_endpoint: string;
    jwks_endpoint: string;
    logout_endpoint: string;
};

export type ActivePlugin = {
    active: boolean;
    version: string;
    description: string;
};

export type ServerAdminInfo = {
    active_plugins: Record<string, ActivePlugin>;
    plugins_enabled: boolean;
    rate_limit_enabled: boolean;
};

export type FeedQuality = "low" | "high";

export type CreateUser = {
    login: string;
    email: string;
    additional_info: string;
    feed_quality: FeedQuality;
    send_email: boolean;
};

export type ObjectOrConfigOrBlobData = ObjectData | ConfigData | BlobData;

export type RelationItem = {
    id: string;
    tags: Tag[];
    type: ObjectLegacyType;
    upload_time: string;
};

export type Reason = {
    reasonType: string;
    relatedObjectDHash: string;
    relatedObjectType: ObjectType;
    relatedUserLogin: string;
};

export type NodeProp = {
    id: string;
    expanded: boolean;
    object: {
        tags: Tag[];
        type: string;
        upload_time: string;
    };
};

export type Edge = {
    child: string | null;
    parent: string | null;
};
