import { useContext } from "react";
import { ObjectContext } from "@mwdb-web/commons/context";
import { renderValue } from "../../RichAttribute/MarkedMustache";
import { AttributeDefinition } from "@mwdb-web/types/types";
import { makeAttributeQuery } from "@mwdb-web/components/RichAttribute/RichAttributeRenderer";

type Props = {
    attributeDefinition: Pick<AttributeDefinition, "rich_template" | "key">;
    value: string;
};

export function RichAttributeValue({ attributeDefinition, value }: Props) {
    // TODO: RichAttributeValue and RichAttributeRenderer should be unified
    const { rich_template: richTemplate, key } = attributeDefinition;
    const object = useContext(ObjectContext);
    try {
        const context = {
            key,
            value,
            object: object.object,
        };
        return renderValue(richTemplate, context, {
            searchEndpoint: object.searchEndpoint,
            makeQuery: (path, value) => makeAttributeQuery(path, value, key),
        });
    } catch (e) {
        return (
            <pre className="attribute-object" style={{ color: "red" }}>
                {"(template error)"} {JSON.stringify(value, null, 4)}
            </pre>
        );
    }
}
