import assert from "node:assert/strict";
import test from "node:test";
import {
    getCustomFilesForAssets,
    resolveCustomFilesInVmf,
} from "../src/frontend/static/js/vmfParser.js";

const customFiles = paths => paths.map(path => ({ path, file: {} }));

test("models include every provided same-stem companion without prefix or directory collisions", () => {
    const expected = [
        "models/props/chair.mdl",
        "models/props/chair.phy",
        "models/props/chair.vvd",
        "models/props/chair.dx80.vtx",
        "models/props/chair.dx90.vtx",
        "models/props/chair.sw.vtx",
        "models/props/chair.ani",
        "models/props/chair.other-companion",
    ];
    const provided = customFiles([
        ...expected,
        "models/props/chair_large.mdl",
        "models/props/chair_large.phy",
        "models/other/chair.phy",
        "models/props/chair.extra/nested.phy",
    ]);

    assert.deepEqual(
        getCustomFilesForAssets(provided, ["models/props/chair.mdl"]).map(file => file.path),
        expected,
    );
});

test("model matching supports dotted names, case differences, and Windows separators", () => {
    const provided = customFiles([
        "models/props/chair.v2.mdl",
        "models/props/chair.v2.dx90.vtx",
        "models/props/chair.v3.phy",
    ]);
    assert.deepEqual(
        getCustomFilesForAssets(provided, ["MODELS\\PROPS\\CHAIR.V2.MDL"]),
        provided.slice(0, 2),
    );
});

test("duplicate custom paths are uploaded only once", () => {
    const provided = customFiles(["models/chair.phy", "MODELS\\CHAIR.PHY"]);
    assert.deepEqual(getCustomFilesForAssets(provided, ["models/chair.mdl"]), [provided[1]]);
});

test("extensionless material references include their VMT and VTF files", () => {
    const provided = customFiles([
        "materials/test/custom_texture.vmt",
        "materials/test/custom_texture.vtf",
        "materials/test/custom_texture_other.vtf",
    ]);
    assert.deepEqual(
        getCustomFilesForAssets(provided, ["materials/test/custom_texture"]),
        provided.slice(0, 2),
    );
    assert.equal(resolveCustomFilesInVmf(provided, ["materials/test/custom_texture"]).size, 0);
});

test("a missing base model is not satisfied by its companions", () => {
    const provided = customFiles(["models/chair.phy", "models/chair.dx90.vtx"]);
    assert.deepEqual(
        [...resolveCustomFilesInVmf(provided, ["models/chair.mdl", "models/chair.phy"])],
        ["models/chair.mdl"],
    );
});

test("explicit companion requests and unrelated assets retain exact matching", () => {
    const provided = customFiles(["models/chair.phy", "models/chair.vvd", "sound/test.wav"]);
    assert.deepEqual(
        getCustomFilesForAssets(provided, ["models/chair.phy", "sound/test.wav"]),
        [provided[0], provided[2]],
    );
});
