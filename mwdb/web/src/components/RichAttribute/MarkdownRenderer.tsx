import { uniqueId } from "lodash";
import { Link } from "react-router-dom";

const tableClasses = {
    table: "marked-table",
    row: "marked-table-row",
    cell: "marked-table-cell",
    header: "marked-table-header",
};

export type Token = {
    type:
        | "text"
        | "escape"
        | "strong"
        | "em"
        | "del"
        | "hr"
        | "blockquote"
        | "paragraph"
        | "link"
        | "list"
        | "list_item"
        | "html"
        | "table"
        | "codespan"
        | "code"
        | "space";
    raw?: string;
    text?: string;
    tokens?: Token[];
    href?: string;
    items?: Token[];
    header?: Token[];
    rows?: Token[][];
};

export type Option = {
    searchEndpoint: string;
    lambdaResults?: { [id: string]: any };
};

// Custom renderer into React components
export function markdownRenderer(tokens: Token[], options: Option): any {
    const renderers = {
        text(token: Token) {
            return token.tokens
                ? markdownRenderer(token.tokens, options)
                : token.text ?? "";
        },
        escape(token: Token) {
            return token.text ?? "";
        },
        strong(token: Token) {
            return (
                <strong key={uniqueId()}>
                    {markdownRenderer(token.tokens ?? [], options)}
                </strong>
            );
        },
        em(token: Token) {
            return (
                <em key={uniqueId()}>
                    {markdownRenderer(token.tokens ?? [], options)}
                </em>
            );
        },
        del(token: Token) {
            return (
                <del key={uniqueId()}>
                    {markdownRenderer(token.tokens ?? [], options)}
                </del>
            );
        },
        hr() {
            return <hr key={uniqueId()} />;
        },
        blockquote(token: Token) {
            return (
                <blockquote key={uniqueId()} className="blockquote">
                    {markdownRenderer(token.tokens ?? [], options)}
                </blockquote>
            );
        },
        paragraph(token: Token) {
            return (
                <p key={uniqueId()} style={{ margin: "0" }}>
                    {markdownRenderer(token.tokens ?? [], options)}
                </p>
            );
        },
        link(token: Token) {
            if (token.href) {
                if (token.href.startsWith("search#")) {
                    const query = token.href.slice("search#".length);
                    const search =
                        "?" +
                        new URLSearchParams({
                            q: decodeURIComponent(query),
                        }).toString();
                    return (
                        <Link
                            key={uniqueId()}
                            to={{
                                pathname: options?.searchEndpoint,
                                search,
                            }}
                        >
                            {markdownRenderer(token.tokens ?? [], options)}
                        </Link>
                    );
                } else if (token.href.startsWith("lambda#")) {
                    const id = token.href.slice("lambda#".length);
                    if (!options.lambdaResults?.hasOwnProperty(id)) {
                        return <i>{`(BUG: No lambda result for ${id})`}</i>;
                    }
                    return options.lambdaResults[id];
                }
            }
            return (
                <a key={uniqueId()} href={token.href}>
                    {markdownRenderer(token.tokens ?? [], options)}
                </a>
            );
        },
        list(token: Token) {
            return (
                <ul key={uniqueId()} style={{ margin: "0" }}>
                    {token.items?.map((item: Token) =>
                        markdownRenderer([item], options)
                    )}
                </ul>
            );
        },
        list_item(token: Token) {
            return (
                <li key={uniqueId()}>
                    {markdownRenderer(token.tokens ?? [], options)}
                </li>
            );
        },
        html(token: Token) {
            return token.text;
        },
        table(token: Token) {
            return (
                <div className="table-responsive" key={uniqueId()}>
                    <div
                        className={`${tableClasses.table} table table-striped table-bordered table-hover`}
                    >
                        <div
                            className={`${tableClasses.header} ${tableClasses.row}`}
                        >
                            {token.header?.map((head: Token, index: number) => (
                                <div className={tableClasses.cell} key={index}>
                                    {markdownRenderer(head.tokens ?? [], options)}
                                </div>
                            ))}
                        </div>
                        {token.rows?.map((row: Token[], rowsIndex: number) => (
                            <div key={rowsIndex} className={tableClasses.row}>
                                {row.map((cell: Token, cellIndex: number) => (
                                    <div
                                        key={cellIndex}
                                        className={tableClasses.cell}
                                    >
                                        {markdownRenderer(
                                            cell.tokens ?? [],
                                            options
                                        )}
                                    </div>
                                ))}
                            </div>
                        ))}
                    </div>
                </div>
            );
        },
        codespan(token: Token) {
            return <code key={uniqueId()}>{token.text}</code>;
        },
        code(token: Token) {
            return <pre key={uniqueId()}>{token.text}</pre>;
        },
        space() {
            return [];
        },
    };

    return tokens.map((token: Token) => {
        const renderer = renderers[token.type];
        if (!renderer) {
            return [<i>{`(No renderer for ${token.type})`}</i>];
        }
        return renderer(token);
    });
}
