import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCheck, faWarning, faInfoCircle } from "@fortawesome/free-solid-svg-icons";

function noop() {}

function count(input: any[]): any {
    return input.length;
}

function sort(input: any[]): any {
    return input.sort((a, b) => a.localeCompare(b, undefined, {numeric: true, sensitivity: 'base'}))
}

function sectionHeader(this: any, header: any, options: any): any {
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
    // TODO: Markdown adds paragraph. Make mustache-only renderer for such cases
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
    makeList: noop,
    count,
    sort,
    "section.header": sectionHeader,
    "section": section,
    "indicator.type": indicatorType,
    "indicator": indicator,
};
