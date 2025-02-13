import { afterPluginsLoaded, fromPlugins } from "../plugins";
import { Capability } from "@mwdb-web/types/types";

export let capabilitiesList: Record<Capability, string> = {
    [Capability.manageUsers]:
        "Managing users and groups (system administration)",
    [Capability.accessAllObjects]:
        "Has access to all new uploaded objects into system",
    [Capability.sharingWithAll]: "Can share objects with all groups in system",
    [Capability.accessUploaderInfo]:
        "Can view who uploaded object and filter by uploader",
    [Capability.addingTags]: "Can add tags",
    [Capability.removingTags]: "Can remove tags",
    [Capability.addingComments]: "Can add comments",
    [Capability.removingComments]: "Can remove (all) comments",
    [Capability.addingParents]: "Can specify parent of uploaded object",
    [Capability.removingParents]:
        "Can remove parent of object and inherited permissions from that relation",
    [Capability.readingAllAttributes]:
        "Has access to all attributes of object (including hidden)",
    [Capability.addingAllAttributes]: "Can add all attributes to object",
    [Capability.removingAttributes]: "Can remove attribute from objects",
    [Capability.addingFiles]: "Can upload files",
    [Capability.addingConfigs]: "Can upload configs",
    [Capability.addingBlobs]: "Can upload text blobs",
    [Capability.unlimitedRequests]:
        "API requests are not rate-limited for this group",
    [Capability.removingObjects]: "Can remove objects",
    [Capability.manageProfile]: "Can manage own profile",
    [Capability.personalize]: "Can mark favorites and manage own quick queries",
    [Capability.kartonAssign]:
        "Can assign existing analysis to the object (required by karton-mwdb-reporter)",
    [Capability.kartonReanalyze]: "Can resubmit any object for analysis",
    [Capability.removingKarton]: "Can remove analysis from object",
    [Capability.modify3rdPartySharing]:
        "Can mark objects as shareable with 3rd parties",
    [Capability.accessPrometheusMetrics]:
        "Can access Prometheus metrics on /api/varz endpoint",
};

afterPluginsLoaded(() => {
    for (let extraCapabilities of fromPlugins("capabilities")) {
        capabilitiesList = { ...capabilitiesList, ...extraCapabilities };
    }
});
