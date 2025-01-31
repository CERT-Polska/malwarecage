import { GenericOrJSX } from "@mwdb-web/types/types";

export { downloadData } from "./download";
export * from "./search";
export * from "./filesize";
export * from "./paginate";
export { getErrorMessage } from "./getErrorMessage";

export const capitalize = (s: string): string => {
    if (typeof s !== "string") return "";
    return s.charAt(0).toUpperCase() + s.slice(1);
};

export function intersperse<T>(
    array: GenericOrJSX<T>[],
    separator: GenericOrJSX<T> | GenericOrJSX<T>[]
): GenericOrJSX<T>[] {
    if (array.length === 0) {
        return [];
    }

    const separatorArray = Array.isArray(separator) ? separator : [separator];

    return array.reduce(
        (
            result: GenericOrJSX<T>[],
            current: GenericOrJSX<T>,
            index: number
        ) => {
            if (index !== array.length - 1) {
                return [...result, current, ...separatorArray];
            } else {
                return [...result, current];
            }
        },
        []
    );
}

export function mapObjectType(objectType: string): string {
    return (
        {
            object: "object",
            file: "file",
            static_config: "config",
            text_blob: "blob",
        }[objectType] || objectType
    );
}

// negate the buffer contents (xor with key equal 0xff)
export function negateBuffer(buffer: ArrayBuffer) {
    const uint8View = new Uint8Array(buffer);
    const xored = uint8View.map((item) => item ^ 0xff);
    return xored.buffer;
}
