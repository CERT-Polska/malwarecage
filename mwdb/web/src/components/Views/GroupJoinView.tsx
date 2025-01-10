import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@mwdb-web/commons/api";
import { ConfirmationModal } from "@mwdb-web/commons/ui";
import { getErrorMessage } from "@mwdb-web/commons/helpers";
import { toast } from "react-toastify";

export function GroupJoinView() {
    const params = useSearchParams()[0];
    const token = params.get("token") ?? "";
    const [groupName, setGroupName] = useState<string>("");
    const navigate = useNavigate();

    async function getInvitationDetails() {
        try {
            let response = await api.getInvitationData(token);
            setGroupName(response.data.name);
        } catch (error) {
            toast(getErrorMessage(error), {
                type: "error",
            });
            navigate("/profile/groups");
        }
    }
    async function acceptInvitation() {
        try {
            await api.acceptGroupInvitation(token);
            toast("You are now a member", {
                type: "success",
            });
            navigate("/profile/groups");
        } catch (error) {
            toast(getErrorMessage(error), {
                type: "error",
            });
        }
    }

    useEffect(() => {
        getInvitationDetails();
    }, []);

    return (
        <div style={{ textAlign: "center" }}>
            <div className="background" />
            <ConfirmationModal
                isOpen={true}
                message={`Do you want to accept the invitation to '${groupName}' group?`}
                buttonStyle="btn-success"
                cancelText="No"
                onRequestClose={() => {
                    navigate("/profile/groups");
                }}
                onConfirm={acceptInvitation}
            ></ConfirmationModal>
        </div>
    );
}
