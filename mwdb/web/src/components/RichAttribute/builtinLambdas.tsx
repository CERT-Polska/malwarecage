import { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCheck, faWarning, faInfoCircle } from "@fortawesome/free-solid-svg-icons";

function count(input: any[]): any {
    return input.length;
}

function sort(input: any[]): any {
    return input.sort((a, b) => a.localeCompare(b, undefined, {numeric: true, sensitivity: 'base'}))
}

function first(input: any[]): any {
    if(input.length > 0) {
        return [input[0]]
    } else {
        return []
    }
}

function last(input: any[]): any {
    if(input.length > 0) {
        return [input[input.length - 1]]
    } else {
        return []
    }
}

function groupBy(key: any, options: any): any {
    options.context.lambdaContext["groupBy"] = key.trim();
    return "";
}

function group(input: any[], options: any): any {
    const groupBy = options.context.lambdaContext["groupBy"];
    let result: any = {};
    for(let item of input) {
        const key = item[groupBy];
        if(!result[key]) {
            result[key] = [];
        }
        result[key].push(item);
    }
    return result;
}

function keys(input: any): any {
    return Object.keys(input)
}

function values(input: any): any {
    return Object.values(input)
}

function entries(input: any): any {
    return Object.entries(input).map(([k, v]) => ({"key": k, "value": v}))
}

function jsonify(input: any[]): any {
    return JSON.stringify(input);
}

function _if(text: any, options: any): any {
    /**
     * {{if}} clauses are useful if you want to render something conditionally
     * Simple sections work the same, but then value references are in nested
     * contexts
     */
    // TODO: render but make it mustache only
    options.context.lambdaContext["if"] = !!(text.trim());
}

function _then(text: any, options: any): any {
    if(options.context.lambdaContext["if"])
        return options.renderer(text);
    else
        return "";
}

function _else(text: any, options: any): any {
    if(!options.context.lambdaContext["if"])
        return options.renderer(text);
    else
        return "";
}

function sectionHeader(header: any, options: any): any {
    options.context.lambdaContext["sectionHeader"] = options.renderer(header);
    return "";
}

function section(text: any, options: any): any {
    return (
        <>
            <div className="py-2 pl-4 bg-light">
                <b>{options.context.lambdaContext["sectionHeader"]}</b>
            </div>
            {options.renderer(text)}
        </>
    )
}

function collapseHeader(header: any, options: any): any {
    options.context.lambdaContext["collapseHeader"] = options.renderer(header);
    return "";
}

function collapse(text: any, options: any): any {
    // todo
    return "";
}

function indicatorType(this: any, value: any, options: any): any {
    options.context.lambdaContext["indicatorType"] = value.trim()
}

function indicator(text: any, options: any): any {
    const indicatorType = options.context.lambdaContext["indicatorType"];
    let icon = [];
    if(indicatorType == "success") {
        icon = [<FontAwesomeIcon icon={faCheck} className="text-success mx-2" />]
    }
    else if(indicatorType == "warning") {
        icon = [<FontAwesomeIcon icon={faWarning} className="text-warning mx-2" />]
    }
    else if(indicatorType == "danger") {
        icon = [<FontAwesomeIcon icon={faWarning} className="text-danger mx-2" />]
    } else {
        icon = [<FontAwesomeIcon icon={faInfoCircle} className="text-primary mx-2" />]
    }
    // TODO: Markdown adds paragraph. We can style it to make inline-block from first p
    return (
        <div className="py-2">
            {icon} {text}
        </div>
    )
}

export type LambdaFunction = (
    this: object,
    input: any,
    options: { callType: "section" | "pipeline"; renderer?: Function, context: any },
) => any;

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
    "section": section,
    "indicator.type": indicatorType,
    "indicator": indicator,
    "collapse.header": collapseHeader,
    "collapse": collapse,
    "if": _if,
    "then": _then,
    "else": _else,
};
