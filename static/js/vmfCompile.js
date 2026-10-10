import * as api from "./api.js";
import { getUserCustomFilesFromPage, addUserCustomFilesInputs } from "./UserCustomFileshelpers.js"
import { enableButton, disableButton } from "./htmlhelpers.js";

export async function handleCompileVmfClick(button, selectedGame, vmfFile) {
    disableButton(button, "Fetching local game files...");
    
    if (!vmfFile) alert("No .vmf file selected!")
        const customFiles = getUserCustomFilesFromPage();
    const localFiles = await api.getGameFiles(selectedGame);
    
    disableButton(button, "Resolving custom assets...");
    const userCustomFiles = resolveCustomAssetsInVmfFile(vmfFile, customFiles);
    let bundledFiles = getCustomFilesFromUserCustomFiles
    if(customFiles){
        
    }
}


function resolveCustomAssetsInVmfFile(vmfFile, customFiles) {
    const entities = vmfFile.entity ?? [];
    const solids = vmfFile.world?.solid ?? [];

    const entityParameters = ["material", "model", "texture", "solid", "message"];
    const solidParameters = ["material"];

    let customAssets = {};

    for (const entity of entities.concat(solids)) {
        const material = entity.material;
        const model = entity.model;
        const texture = entity.texture;
        const solid = entity.solid;
        const message = entity.message;
        
        if (material) {

        } else if (model) {

        } else if (texture) {

        } else if (solid) {

        }
    }
}

function getSolidMaterials(solid, customFiles) {
    const materials = solid.side.map(sd => sd.material);
    return materials;
}
