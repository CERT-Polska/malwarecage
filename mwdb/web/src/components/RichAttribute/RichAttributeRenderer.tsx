import { useEffect, useState } from "react";
import { renderValue } from "./MarkedMustache";

import { makeContext } from "./exampleTemplates";
import { escapeSearchValue } from "@mwdb-web/commons/helpers";

type Props = {
    template: string;
    value: string;
    setInvalid: (valid: boolean) => void;
};

export function makeAttributeQuery(
    path: string[],
    value: string,
    attributeKey: string
): string | undefined {
    if (path[0] !== "value" && path[0] !== "value*") return undefined;
    if (path[0] === "value*") attributeKey = attributeKey + "*";
    const queryPath = ["attribute", attributeKey, ...path.slice(1)].join(".");
    return `${queryPath}:${escapeSearchValue(value)}`;
}

export function RichAttributeRenderer({ template, value, setInvalid }: Props) {
    const [renderResult, setRenderResult] = useState(<></>);

    useEffect(() => {
        try {
            const context = makeContext(JSON.parse(value));
            const key = context["key"];
            const renderedValue = renderValue(template, context, {
                searchEndpoint: "/",
                makeQuery: (path, value) =>
                    makeAttributeQuery(path, value, key),
            });
            setRenderResult(renderedValue);
            setInvalid(false);
        } catch (e: any) {
            setRenderResult(e.toString());
            if (setInvalid) {
                setInvalid(true);
            }
        }
    }, [template, value]);

    return renderResult;
}
