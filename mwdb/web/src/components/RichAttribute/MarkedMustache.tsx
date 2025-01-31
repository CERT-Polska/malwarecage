import _, { uniqueId } from "lodash";
import Mustache, { Context } from "mustache";
import { marked, Tokenizer } from "marked";
import { escapeSearchValue } from "@mwdb-web/commons/helpers";
import { fromPlugins } from "@mwdb-web/commons/plugins";
import { markdownRenderer, Option, Token } from "./MarkdownRenderer"
import { builtinLambdas, LambdaFunction } from "./builtinLambdas";

/**
 * Markdown with Mustache templates for React
 * Based on Marked (https://github.com/markedjs/marked) and
 * mustache.js library (https://github.com/janl/mustache.js)
 *
 * Applied modifications:
 * - Rendering React components for chosen Markdown language subset
 * - Support for arbitrary widgets
 * - Markdown-specific escaping instead of HTML-specific on Mustache level
 * - Removed HTML escaping on Marked level
 */

function appendToLastElement(array: string[], value: string) {
    // (["a", "b", "c"], "d") => ["a", "b", "cd"]
    return [...array.slice(0, -1), array[array.length - 1] + value];
}

function isFunction(obj: Object): boolean {
    return typeof obj === "function";
}

function splitByUnescapedSeparator(name: string, separator: string) {
    const splitRegex = new RegExp(
        String.raw`(?<!\\)((?:\\\\)*[${separator}])`,
        "g"
    );
    const replaceRegex = new RegExp(String.raw`\\([${separator}\\])`, "g");
    return name
        .split(splitRegex)
        .reduce((acc: string[], current: string, index: number) => {
            const unescapedCurrent = current.replaceAll(replaceRegex, "$1");
            if (index % 2) {
                // Last character is a dot, rest must be appended to last element
                const currentWithoutLast = unescapedCurrent.slice(0, -1);
                return appendToLastElement(acc, currentWithoutLast);
            } else {
                // Regular name part
                return [...acc, unescapedCurrent];
            }
        }, []);
}

function splitName(name: string) {
    if (name === ".")
        // Special case for "this"
        return [];
    return splitByUnescapedSeparator(name, ".");
}

function makeQuery(path: string[], value: string, attributeKey: string) {
    if (path[0] !== "value" && path[0] !== "value*")
        /**
         * TODO: value* should be interpreted as attribute.<attributeKey>*
         * but that form is currently unsupported by backend
         */
        return undefined;
    const queryPath = ["attribute", attributeKey, ...path.slice(1)].join(".");
    return `${queryPath}:${escapeSearchValue(value)}`;
}

abstract class Reference {
    abstract toMarkdown(): string;
}

class LambdaResultReference extends Reference {
    resultId: string;

    constructor(resultId: string) {
        super()
        this.resultId = resultId;
    }

    toMarkdown(): string {
        return `[](lambda#${this.resultId})`;
    }
}

class SearchReference extends Reference {
    query: string;
    value: string;
    constructor(query: string, value: string) {
        super();
        this.query = query;
        this.value = value;
    }

    toMarkdown() {
        return `[${escapeMarkdown(this.value)}](search#${escapeMarkdown(
            encodeURIComponent(this.query)
        )})`;
    }
}

function escapeMarkdown(string: string) {
    // Escape Markdown characters
    // https://www.markdownguide.org/basic-syntax/#escaping-characters
    return String(string).replace(/([\\`*_{}[\]<>()#+-,!|])/g, "\\$1");
}

// Extended context to provide special Mustache values in future
class MustacheContext extends Mustache.Context {
    renderContext: MarkedMustache
    lambdaResults: { [id: string]: any };
    lambdaContext: { [key: string]: any};
    parentPath: string[];
    lastPath: string[];

    constructor(view: Object, renderContext: MarkedMustache, parent?: MustacheContext, initialPath?: string[]) {
        super(view, parent);
        this.renderContext = renderContext;
        this.lambdaResults = parent ? parent.lambdaResults : {};
        this.lambdaContext = parent ? parent.lambdaContext : {};
        if(parent) {
            this.lambdaResults = parent.lambdaResults;
            this.lambdaContext = parent.lambdaContext;
            this.parentPath = parent.lastPath;
        } else {
            this.lambdaResults = {};
            this.lambdaContext = {};
            this.parentPath = initialPath || [];
        }
        this.lastPath = this.parentPath.slice();
    }

    push(view: Object): Context {
        // Creates new nested context (for section)
        return new MustacheContext(view, this.renderContext, this);
    }

    lookupView(name: string) {
        // Make a lookup within a view object
        if (!name) return undefined;
        const path = splitName(name);

        let currentObject = this.view;
        for (let element of path) {
            if (!Object.prototype.hasOwnProperty.call(currentObject, element))
                return undefined;
            currentObject = currentObject[element];
        }

        this.lastPath = [...this.parentPath, ...path];
        if(Array.isArray(currentObject) && this.lastPath.length > 0) {
            this.lastPath[this.lastPath.length - 1] += "*"
        }
        return currentObject;
    }

    emitLambdaResult(result: any): any {
        if (typeof result !== "string") {
            let lambdaResultId = uniqueId("lambda_result");
            this.lambdaResults[lambdaResultId] = result;
            // Emit reference in markdown
            return new LambdaResultReference(lambdaResultId);
        } else {
            return result;
        }
    }

    lookupLambda(name: string) {
        const lambda = this.renderContext.lambdas[name];
        if (!lambda) return undefined;
        const context = this;

        return function lambdaFunction(
            this: any,
            template: string,
        ): string {
            const subrender = ((template: string) => {
                return context.renderContext.render(template, this, context.lastPath);
            })
            let result = lambda.call(this, template, {
                callType: "section",
                renderer: subrender,
                context,
            });
            let lambdaResult = context.emitLambdaResult(result);
            if(lambdaResult instanceof LambdaResultReference)
                return lambdaResult.toMarkdown()
            else
                return lambdaResult;
        };
    }

    lookupPipeline(pipeline: string) {
        const [name, ...lambdaNames] = pipeline
            .split("|")
            .map((name) => name.trim());
        let result = this.lookupView(name);
        if (typeof result === "undefined") return undefined;
        for (let lambdaName of lambdaNames) {
            const lambda = this.renderContext.lambdas[lambdaName];
            if (!lambda) return undefined;
            result = lambda.call(this.view, result, { callType: "pipeline", context: this });
            if (typeof result === "undefined") return undefined;
        }
        return result;
    }

    lookupSearchable(name: string) {
        if (!name) return undefined;
        let currentObject = this.lookupView(name);
        if (typeof currentObject === "undefined") return undefined;
        if (isFunction(currentObject) || typeof currentObject === "object")
            // Non-primitives are not directly searchable
            return undefined;
        const query = this.renderContext.options.makeQuery(
            this.lastPath,
            currentObject
        );
        if (!query) return undefined;
        return new SearchReference(query, currentObject);
    }

    lookup(name: string) {
        // Check for searchable mark at the beginning
        if (name[0] === "@") {
            // Searchable field mark
            name = name.slice(1);
            return this.lookupSearchable(name);
        } else if (name.includes("|")) {
            // Pipeline expression
            return this.lookupPipeline(name);
        }

        let object = this.lookupView(name);
        if (typeof object !== "undefined") return object;

        let lambda = this.lookupLambda(name);
        if (typeof lambda !== "undefined") return lambda;

        return undefined;
    }
}

// Extended Writer to escape Markdown characters instead of HTML
class MustacheWriter extends Mustache.Writer {
    getConfigEscape() {
        // Override default (HTML) escape function
        return escapeMarkdown;
    }

    escapedValue(token: string[], context: Context) {
        // https://github.com/janl/mustache.js/blob/550d1da9e3f322649d04b4795f5356914f6fd7e8/mustache.js#L663
        const value = context.lookup(token[1]);
        if (value instanceof Reference) {
            return value.toMarkdown();
        } else if (value != null)
            return typeof value === "number"
                ? String(value)
                : escapeMarkdown(value);
        return "";
    }
}

// Overrides to not use HTML escape
// https://github.com/markedjs/marked/blob/e3f8cd7c7ce75ce4f7e22bd082c45deb1678846d/src/Tokenizer.js#L67
class MarkedTokenizer extends Tokenizer {
    rules: any;
    escape(src: string): any {
        const cap = this.rules.inline.escape.exec(src);
        if (cap) {
            return {
                type: "escape",
                raw: cap[0],
                text: cap[1],
            };
        }
        return false;
    }

    codespan(src: string): any {
        const cap = this.rules.inline.code.exec(src);
        if (cap) {
            let text = cap[2].replace(/\n/g, " ");
            const hasNonSpaceChars = /[^ ]/.test(text);
            const hasSpaceCharsOnBothEnds = /^ /.test(text) && / $/.test(text);
            if (hasNonSpaceChars && hasSpaceCharsOnBothEnds) {
                text = text.substring(1, text.length - 1);
            }
            return {
                type: "codespan",
                raw: cap[0],
                text,
            };
        }
    }

    inlineText(src: string, smartypants: (cap: string) => string): any {
        const cap = this.rules.inline.text.exec(src);
        if (cap) {
            let text = this.options.smartypants ? smartypants(cap[0]) : cap[0];
            return {
                type: "text",
                raw: cap[0],
                text,
            };
        }
    }
}

const mustacheWriter = new MustacheWriter();
const markedTokenizer = new MarkedTokenizer();

type MarkedMustacheOptions = {
    searchEndpoint: string;
    lambdas: {[name: string]: Function};
    makeQuery: (path: string[], value: any) => string;
}

class MarkedMustache {
    globalView: object
    options: MarkedMustacheOptions

    constructor(globalView: any, options: MarkedMustacheOptions) {
        this.globalView = globalView;
        this.options = options;
    }

    get lambdas() {
        return this.options.lambdas;
    }

    render(template: string, view: object, initialPath?: string[]) {
        const context = new MustacheContext(view, this, undefined, initialPath);
        const markdown = mustacheWriter.render(template, context);
        const tokens = marked.lexer(markdown, {
            ...marked.defaults,
            tokenizer: markedTokenizer,
        }) as Token[];
        return markdownRenderer(tokens, {
            searchEndpoint: this.options.searchEndpoint,
            lambdaResults: context.lambdaResults
        });
    }
}

export function renderValue(template: string, value: Object, options: Option) {
    const pluginLambdas = [
        builtinLambdas,
        ...fromPlugins("mustacheExtensions"),
    ];

    function makeQuery(path: string[], value: string): string {
        console.log(path);
        // TODO: make it context-aware
        return "";
    }

    let lambdas = {}
    for(let lambdaSet of pluginLambdas)
        lambdas = {...lambdas, ...lambdaSet}

    const markedMustache = new MarkedMustache(value, {
        searchEndpoint: options.searchEndpoint,
        lambdas,
        makeQuery
    })
    return (
        <div>
            {markedMustache.render(template, value)}
        </div>
    );
}
