import { Routes, Route } from "react-router-dom";

import { Capability } from "@mwdb-web/types/types";
import { SampleRouteFallback } from "./SampleRouteFallback";
import { NavigateFor404 } from "./NavigateFor404";
import { fromPlugins } from "../plugins";

import { AboutView } from "@mwdb-web/components/Views/AboutView";
import { UserLoginView } from "@mwdb-web/components/Views/UserLoginView";
import { UserRegisterView } from "@mwdb-web/components/Views/UserRegisterView";
import { UserPasswordRecoverView } from "@mwdb-web/components/Views/UserPasswordRecoverView";
import { UserSetPasswordView } from "@mwdb-web/components/UserSetPasswordView";
import { OAuthAuthorizeView } from "@mwdb-web/components/Views/OAuthAuthorizeView";
import { RequiresAuth, RequiresCapability } from "../ui";
import { RecentSamplesView } from "@mwdb-web/components/File/Views/RecentSamplesView";
import { RecentConfigsView } from "@mwdb-web/components/Config/Views/RecentConfigsView";
import { RecentBlobsView } from "@mwdb-web/components/Blob/Views/RecentBlobsView";
import { ConfigStatsView } from "@mwdb-web/components/Config/Views/ConfigStatsView";
import { DocsView } from "@mwdb-web/components/Views/DocsView";
import { ShowSampleView } from "@mwdb-web/components/Views/ShowSampleView";
import { ShowConfigView } from "@mwdb-web/components/Config/Views/ShowConfigView";
import { ShowTextBlobView } from "@mwdb-web/components/Blob/Views/ShowTextBlobView";
import { ProfileView } from "@mwdb-web/components/Profile/ProfileView";
import { ProfileGroup } from "@mwdb-web/components/Profile/Views/ProfileGroup";
import { ProfileDetails } from "@mwdb-web/components/Profile/Views/ProfileDetails";
import { ProfileGroupMembers } from "@mwdb-web/components/Profile/Views/ProfileGroupMembers";
import { ProfileGroups } from "@mwdb-web/components/Profile/Views/ProfileGroups";
import { UserCapabilitiesView } from "@mwdb-web/components/Settings/Views/UserCapabilitiesView";
import { ProfileAPIKeys } from "@mwdb-web/components/Profile/Views/ProfileAPIKeys";
import { ProfileResetPassword } from "@mwdb-web/components/Profile/Views/ProfileResetPassword";
import { ProfileOAuth } from "@mwdb-web/components/Profile/Views/ProfileOAuth";
import { DiffTextBlobView } from "@mwdb-web/components/Blob/Views/DiffTextBlobView";
import { RelationsPlotView } from "@mwdb-web/components/Views/RelationsPlotView";
import { RemoteViews } from "@mwdb-web/components/Remote/RemoteViews";
import { SettingsView } from "@mwdb-web/components/Settings/Views/SettingsView";
import { SettingsOverviewView } from "@mwdb-web/components/Settings/Views/SettingsOverviewView";
import { UsersPendingListView } from "@mwdb-web/components/Settings/Views/UsersPendingListView";
import { UsersListView } from "@mwdb-web/components/Settings/Views/UsersListView";
import { UserCreateView } from "@mwdb-web/components/Settings/Views/UserCreateView";
import { UserView } from "@mwdb-web/components/Settings/Views/UserView";
import { UserDetailsView } from "@mwdb-web/components/Settings/Views/UserDetailsView";
import { UserAPIKeysView } from "@mwdb-web/components/Settings/Views/UserAPIKeysView";
import { UserResetPasswordView } from "@mwdb-web/components/Settings/Views/UserResetPasswordView";
import { UserSingleGroupsView } from "@mwdb-web/components/Settings/Views/UserSingleGroupsView";
import { GroupsListView } from "@mwdb-web/components/Settings/Views/GroupsListView";
import { GroupCreateView } from "@mwdb-web/components/Settings/Views/GroupCreateView";
import { GroupView } from "@mwdb-web/components/Settings/Views/GroupView";
import { GroupDetailsView } from "@mwdb-web/components/Settings/Views/GroupDetailsView";
import { GroupCapabilitiesView } from "@mwdb-web/components/Settings/Views/GroupCapabilitiesView";
import { GroupMembersView } from "@mwdb-web/components/Settings/Views/GroupMembersView";
import { AccessControlView } from "@mwdb-web/components/Settings/Views/AccessControlView";
import { OAuthListProvidersView } from "@mwdb-web/components/Settings/Views/OAuthListProvidersView";
import { OAuthRegisterView } from "@mwdb-web/components/Settings/Views/OAuthRegisterView";
import { OAuthProviderView } from "@mwdb-web/components/Settings/Views/OAuthProviderView";
import { AttributesListView } from "@mwdb-web/components/Settings/Views/AttributesListView";
import { AttributeCreateView } from "@mwdb-web/components/Settings/Views/AttributeCreateView";
import { AttributeView } from "@mwdb-web/components/Settings/Views/AttributeView";
import { AttributeDetailsView } from "@mwdb-web/components/Settings/Views/AttributeDetailsView";
import { AttributesPermissionsView } from "@mwdb-web/components/Settings/Views/AttributePermissionsView";
import { AttributeEditTemplateView } from "@mwdb-web/components/Settings/Views/AttributeEditTemplateView";
import { UploadConfigView } from "@mwdb-web/components/Upload/Views/UploadConfigView";
import { UploadBlobView } from "@mwdb-web/components/Upload/Views/UploadBlobView";
import { UploadFileView } from "@mwdb-web/components/Upload/Views/UploadFileView";
import { SearchView } from "@mwdb-web/components/Views/SearchView";
import { GroupJoinView } from "@mwdb-web/components/Views/GroupJoinView";

export function AppRoutes() {
    return (
        <Routes>
            <Route path="login" element={<UserLoginView />} />
            <Route path="register" element={<UserRegisterView />} />
            <Route
                path="recover_password"
                element={<UserPasswordRecoverView />}
            />
            <Route path="setpasswd" element={<UserSetPasswordView />} />
            <Route path="oauth/callback" element={<OAuthAuthorizeView />} />
            <Route element={<RequiresAuth />}>
                <Route path="/" element={<RecentSamplesView />} />
                <Route path="configs" element={<RecentConfigsView />} />
                <Route path="blobs" element={<RecentBlobsView />} />
                <Route path="search" element={<SearchView />} />
                <Route
                    path="upload"
                    element={
                        <RequiresCapability capability={Capability.addingFiles}>
                            <UploadFileView />
                        </RequiresCapability>
                    }
                />
                <Route
                    path="blob_upload"
                    element={
                        <RequiresCapability capability={Capability.addingBlobs}>
                            <UploadBlobView />
                        </RequiresCapability>
                    }
                />
                <Route
                    path="config_upload"
                    element={
                        <RequiresCapability
                            capability={Capability.addingConfigs}
                        >
                            <UploadConfigView />
                        </RequiresCapability>
                    }
                />
                <Route path="configs/stats" element={<ConfigStatsView />} />
                <Route path="about" element={<AboutView />} />
                <Route path="docs" element={<DocsView />} />
                <Route
                    path="sample/:hash/*"
                    element={<SampleRouteFallback />}
                />
                <Route path="file/:hash/*" element={<ShowSampleView />} />
                <Route path="config/:hash/*" element={<ShowConfigView />} />
                <Route path="blob/:hash/*" element={<ShowTextBlobView />} />
                <Route path="profile" element={<ProfileView />}>
                    <Route index element={<ProfileDetails />} />
                    <Route path="user/:user" element={<ProfileDetails />} />
                    <Route path="group/:group" element={<ProfileGroup />} />
                    <Route path="group/join" element={<GroupJoinView />} />
                    <Route
                        path="group/:group/members"
                        element={<ProfileGroupMembers />}
                    />
                    <Route path="groups" element={<ProfileGroups />} />
                    <Route
                        path="capabilities"
                        element={<UserCapabilitiesView />}
                    />
                    <Route path="api-keys" element={<ProfileAPIKeys />} />
                    <Route
                        path="reset-password"
                        element={<ProfileResetPassword />}
                    />
                    <Route path="oauth" element={<ProfileOAuth />} />
                </Route>
                <Route
                    path="diff/:current/:previous"
                    element={<DiffTextBlobView />}
                />
                <Route path="relations" element={<RelationsPlotView />} />
                <Route path="remote/:remote" element={<RemoteViews />}>
                    <Route index element={<RecentSamplesView />} />
                    <Route path="configs" element={<RecentConfigsView />} />
                    <Route path="blobs" element={<RecentBlobsView />} />
                    <Route path="search" element={<SearchView />} />
                    <Route path="file/:hash/*" element={<ShowSampleView />} />
                    <Route path="config/:hash/*" element={<ShowConfigView />} />
                    <Route path="blob/:hash/*" element={<ShowTextBlobView />} />
                    <Route
                        path="diff/:current/:previous"
                        element={<DiffTextBlobView />}
                    />
                </Route>
                <Route
                    path="settings"
                    element={
                        <RequiresCapability capability={Capability.manageUsers}>
                            <SettingsView />
                        </RequiresCapability>
                    }
                >
                    <Route index element={<SettingsOverviewView />} />
                    <Route path="pending" element={<UsersPendingListView />} />
                    <Route path="users" element={<UsersListView />} />
                    <Route path="user/new" element={<UserCreateView />} />
                    <Route path="user/:login/*" element={<UserView />}>
                        <Route index element={<UserDetailsView />} />
                        <Route
                            path="capabilities"
                            element={<UserCapabilitiesView />}
                        />
                        <Route path="api-keys" element={<UserAPIKeysView />} />
                        <Route
                            path="password"
                            element={<UserResetPasswordView />}
                        />
                        <Route
                            path="groups"
                            element={<UserSingleGroupsView />}
                        />
                    </Route>
                    <Route path="groups" element={<GroupsListView />} />
                    <Route path="group/new" element={<GroupCreateView />} />
                    <Route path="group/:name/*" element={<GroupView />}>
                        <Route index element={<GroupDetailsView />} />
                        <Route
                            path="capabilities"
                            element={<GroupCapabilitiesView />}
                        />
                        <Route path="members" element={<GroupMembersView />} />
                    </Route>
                    <Route
                        path="capabilities"
                        element={<AccessControlView />}
                    />
                    <Route path="oauth" element={<OAuthListProvidersView />} />
                    <Route
                        path="oauth/register"
                        element={<OAuthRegisterView />}
                    />
                    <Route path="oauth/:name" element={<OAuthProviderView />} />
                    <Route path="attributes" element={<AttributesListView />} />
                    <Route
                        path="attribute/new"
                        element={<AttributeCreateView />}
                    />
                    <Route
                        path="attribute/:attributeKey/*"
                        element={<AttributeView />}
                    >
                        <Route index element={<AttributeDetailsView />} />
                        <Route
                            path="permissions"
                            element={<AttributesPermissionsView />}
                        />
                        <Route
                            path="edit-template"
                            element={<AttributeEditTemplateView />}
                        />
                    </Route>
                </Route>
                {fromPlugins("protectedRoutes")}
            </Route>
            {fromPlugins("routes")}
            <Route path="*" element={<NavigateFor404 />} />
        </Routes>
    );
}
