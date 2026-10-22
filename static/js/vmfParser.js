

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

export function resolveAssetsInVmfFile(vmfFile, customFiles) {
    const entities = vmfFile.entity ?? [];
    const solids = vmfFile.world?.solid ?? [];

    const assetsInVmf = {
        materials: new Set(),
        models: new Set(),
        sounds: new Set(),
    };

    for (const entity of entities.concat(solids)) {
        const material = entity.material;
        const model = entity.model;
        const texture = entity.texture;
        const solid = entity.solid;
        const sound = entity.message;

        if (material && material.length > 1) {
            assetsInVmf.materials.add("materials/" + material);
        } else if (model) {
            assetsInVmf.models.add(model);
        } else if (texture) {
            assetsInVmf.materials.add("materials/" + texture);
        } else if (solid) {
            const solidTextures = getSolidMaterials(solid);
            solidTextures?.forEach(st => assetsInVmf.materials.add("materials/" + st));
        } 
        // else if (sound) {
        //     assetsInVmf.sounds.add("sound/" + sound);
        // }
    }

    return assetsInVmf;
}

function getSolidMaterials(solid) {
    if (typeof solid !== 'object') return;
    // Becuase of entities.concat(solids), function input (the variable named solid) 
    // can either be an array of solids or a single solid - the null coalesce accounts for both
    // (one "entity" can be a brush entity consisting of multiple "solids" (brushes))  
    const materials = (solid.side ?? solid.flatMap(sol => sol.side)).map(sd => sd.material + ".vmt");
    return materials;
}

export function resolveCustomFilesInVmf(userCustomFiles, filesNotInLocalDir) {
    const userCustomFilesSet = new Set(userCustomFiles.map(ucf => ucf.path));
    const fileNotInLocalDirSet = new Set(filesNotInLocalDir);

    const difference = fileNotInLocalDirSet.difference(userCustomFilesSet);
    return difference.size > 0 ? difference : null;
}

function getFormattedWebkitPath(fileObject) {
    return fileObject.webkitRelativePath.substr(fileObject.webkitRelativePath.indexOf("/") + 1,);
}
