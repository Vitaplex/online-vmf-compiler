

function tokenize(text) {
    return text.match(/"(?:\\.|[^"\\])*"|[{}]|[^\s{}]+/g) || [];
}

export function parseVmfFile(text) {
    const tokens = tokenize(text);
    let pos = 0;

    function parseBlock() {
        const result = {};

        while (pos < tokens.length && tokens[pos] !== "}") {
            let key = tokens[pos++];

            // Remove quotes
            key = key.replace(/^"|"$/g, "");

            if (tokens[pos] === "{") {
                pos++; // skip {

                const value = parseBlock();

                pos++; // skip }

                addValue(result, key, value);
            } else {
                let value = tokens[pos++];

                value = value.replace(/^"|"$/g, "");

                addValue(result, key, value);
            }
        }
        return result;
    }

    function addValue(obj, key, value) {
        if (!(key in obj)) {
            obj[key] = value;
        } else if (Array.isArray(obj[key])) {
            obj[key].push(value);
        } else {
            obj[key] = [obj[key], value];
        }
    }
    return parseBlock();
}