import { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
    faCheck,
    faWarning,
    faInfoCircle,
    faPlus,
    faMinus,
} from "@fortawesome/free-solid-svg-icons";

export type LambdaSectionOptions = {
    callType: "section";
    renderer: (template: string) => any;
    mustacheRenderer: (template: string) => string;
    context: any;
};

export type LambdaPipelineOptions = {
    callType: "pipeline";
    context: any;
};

export type LambdaFunction = (
    this: object,
    input: any,
    options: LambdaSectionOptions | LambdaPipelineOptions
) => any;

function count(input: any[]): any {
    return input.length;
}

function sort(input: any[]): any {
    return input.sort((a, b) =>
        a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" })
    );
}

function first(input: any[]): any {
    if (input.length > 0) {
        return [input[0]];
    } else {
        return [];
    }
}

function last(input: any[]): any {
    if (input.length > 0) {
        return [input[input.length - 1]];
    } else {
        return [];
    }
}

function renderParam(input: any, options: LambdaSectionOptions): any {
    // Renders section that is meant to be a parameter for another lambda.
    return options.mustacheRenderer(input).trim();
}

function groupBy(key: any, options: LambdaSectionOptions): any {
    options.context.lambdaContext["groupBy"] = renderParam(key, options);
    return "";
}

function group(input: any[], options: LambdaSectionOptions): any {
    const groupBy = options.context.lambdaContext["groupBy"];
    let result: any = {};
    for (let item of input) {
        const key = item[groupBy];
        if (!result[key]) {
            result[key] = [];
        }
        result[key].push(item);
    }
    return result;
}

function keys(input: any): any {
    return Object.keys(input);
}

function values(input: any): any {
    return Object.values(input);
}

function entries(input: any): any {
    return Object.entries(input).map(([k, v]) => ({ key: k, value: v }));
}

function jsonify(input: any[]): any {
    return JSON.stringify(input);
}

function _if(text: any, options: LambdaSectionOptions): any {
    /**
     * {{if}} clauses are useful if you want to render something conditionally
     * Simple sections work the same, but then value references are in nested
     * contexts
     */
    options.context.lambdaContext["if"] = !!renderParam(text, options);
}

function _then(text: any, options: LambdaSectionOptions): any {
    if (options.context.lambdaContext["if"]) return options.renderer(text);
    else return "";
}

function _else(text: any, options: LambdaSectionOptions): any {
    if (!options.context.lambdaContext["if"]) return options.renderer(text);
    else return "";
}

function sectionHeader(header: any, options: LambdaSectionOptions): any {
    options.context.lambdaContext["sectionHeader"] = options.renderer(header);
    return "";
}

function section(text: any, options: LambdaSectionOptions): any {
    return (
        <>
            <div className="py-2 pl-4 bg-light">
                <b>{options.context.lambdaContext["sectionHeader"]}</b>
            </div>
            {options.renderer(text)}
        </>
    );
}

function collapseHeader(header: any, options: LambdaSectionOptions): any {
    options.context.lambdaContext["collapseHeader"] = options.renderer(header);
    return "";
}

function collapse(text: any, options: LambdaSectionOptions): any {
    const [collapsed, setCollapsed] = useState(true);
    return (
        <>
            <div
                className="md-p-inline my-2"
                onClick={() => setCollapsed((collapsed) => !collapsed)}
                style={{ cursor: "pointer" }}
            >
                <FontAwesomeIcon
                    className="mx-2"
                    icon={collapsed ? faPlus : faMinus}
                />
                {options.context.lambdaContext["collapseHeader"]}
            </div>
            {!collapsed ? options.renderer(text) : []}
        </>
    );
}

function indicatorType(
    this: any,
    value: any,
    options: LambdaSectionOptions
): any {
    options.context.lambdaContext["indicatorType"] = renderParam(
        value,
        options
    );
}

function indicator(text: any, options: LambdaSectionOptions): any {
    const indicatorType = options.context.lambdaContext["indicatorType"];
    let icon = [];
    if (indicatorType == "success") {
        icon = [
            <FontAwesomeIcon icon={faCheck} className="text-success mx-2" />,
        ];
    } else if (indicatorType == "warning") {
        icon = [
            <FontAwesomeIcon icon={faWarning} className="text-warning mx-2" />,
        ];
    } else if (indicatorType == "danger") {
        icon = [
            <FontAwesomeIcon icon={faWarning} className="text-danger mx-2" />,
        ];
    } else {
        icon = [
            <FontAwesomeIcon
                icon={faInfoCircle}
                className="text-primary mx-2"
            />,
        ];
    }
    return (
        <div className="py-2 md-p-inline">
            {icon} {options.renderer(text)}
        </div>
    );
}

export const builtinLambdas = {
    count,
    sort,
    first,
    last,
    group,
    keys,
    values,
    entries,
    jsonify,
    "group.by": groupBy,
    "section.header": sectionHeader,
    section: section,
    "indicator.type": indicatorType,
    indicator: indicator,
    "collapse.header": collapseHeader,
    collapse: collapse,
    if: _if,
    then: _then,
    else: _else,
};
