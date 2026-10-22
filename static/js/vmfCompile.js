import * as api from "./api.js";
import { getUserCustomFilesFromPage, addUserCustomFilesInputs } from "./userCustomFilesHelpers.js"
import { enableElement, disableElement } from "./htmlHelpers.js";
import { resolveAssetsInVmfFile, resolveCustomFilesInVmf } from "./vmfParser.js";

export async function handleCompileVmfClick(button, outputArea, selectedGame, vmfFile) {
    outputArea.classList.remove("error");

    if (!vmfFile) alert("No .vmf file selected!");

    disableElement(button, "Getting custom files...");
    const userCustomFiles = getUserCustomFilesFromPage();

    disableElement(button, "Resolving assets in .vmf file...");
    const vmfFiles = resolveAssetsInVmfFile(vmfFile);
    const filePathList = [...vmfFiles.materials, ...vmfFiles.models, ...vmfFiles.sounds];

    disableElement(button, "Finding local files...");
    const filesNotInLocalDir = await api.getExistingGameFiles(filePathList, selectedGame);
    
    if (filesNotInLocalDir.length > 0) {
        console.warn(`Could not find these files in selected game directory for ${selectedGame} (including vpks)`, filesNotInLocalDir);
    }
    
    const missingFiles = resolveCustomFilesInVmf(userCustomFiles, filesNotInLocalDir);
    
    if (missingFiles) {
        console.warn("Missing files not provided by the user!", missingFiles);
        outputArea.classList.add("error");
        outputArea.value = `Missing assets!\nThese assets are missing locally, and is not provided by the user using the "Select custom files" option:\n\n` + Array.from(missingFiles).join("\n");
    }
    else {
        disableElement(button, "Processing .vmf and custom files...");
        return await api.compileVmfFile(userCustomFiles, selectedGame, vmfFile);
    }
}

