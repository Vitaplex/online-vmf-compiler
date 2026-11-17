import * as api from "./api.js";
import { getUserCustomFilesFromPage, addUserCustomFilesInputs } from "./userCustomFilesHelpers.js"
import { enableElement, disableElement } from "./htmlHelpers.js";
import { getCustomFilesForAssets, resolveAssetsInVmfFile, resolveCustomFilesInVmf } from "./vmfParser.js";

export async function handleCompileVmfClick(button, outputArea, selectedGame, ignoreMissingFiles, vmfFileObject, fileName, compileParams) {
    if (!vmfFileObject) alert("No .vmf file selected!");

    disableElement(button, "Getting custom files...");
    const userCustomFiles = getUserCustomFilesFromPage();

    disableElement(button, "Resolving assets in .vmf file...");
    const vmfFiles = resolveAssetsInVmfFile(vmfFileObject.object);
    const referencedFiles = [...vmfFiles.materials, ...vmfFiles.models, ...vmfFiles.sounds];
    const customFiles = getCustomFilesForAssets(userCustomFiles, referencedFiles);
    const filePathList = [...new Set([...referencedFiles, ...customFiles.map(file => file.path)])];

    disableElement(button, "Finding local files...");
    const filesNotInLocalDir = await api.getExistingGameFiles(filePathList, selectedGame);

    if (filesNotInLocalDir.length > 0) {
        console.warn(`Could not find these files in selected game directory for ${selectedGame} (including vpks)`, filesNotInLocalDir);
    }

    const missingFiles = resolveCustomFilesInVmf(customFiles, filesNotInLocalDir);

    if (missingFiles.size > 0 && !ignoreMissingFiles) {
        console.warn("Missing files not provided by the user!", missingFiles);
        outputArea.classList.add("error");
        outputArea.value = `Missing assets! (${missingFiles.size})\nThese assets are missing locally, and are not provided by the user using the "Select custom files" option:\n\n` + Array.from(missingFiles).join("\n");
        return;
    }
    else if (missingFiles) {
        disableElement(button, "Uploading custom files...");
        const response = await uploadFiles(customFiles, filesNotInLocalDir, selectedGame);
        const errors = response.filter(e => !e.success);
        if (errors) errors.forEach(err => { outputArea.value += "Error uploading file: " + JSON.stringify(err.path) + "\n" });
    }

    disableElement(button, "Compiling vmf-file...");
    return await sendVmfToBackend(selectedGame, vmfFileObject.stringrepresentation, fileName, compileParams)
}

async function sendVmfToBackend(selectedGame, vmfFile, fileName, compileParams) {
    const response = await api.compileVmfFile(selectedGame, vmfFile, fileName, compileParams);
    return response;
}

async function uploadFiles(userCustomFiles, filesNotInLocalDir, selectedGame) {
    const missingPaths = new Set(filesNotInLocalDir);
    const uploads = userCustomFiles.filter(file => missingPaths.has(file.path)).map(async file =>
        api.uploadFileForGame(await file.file.arrayBuffer(), file.path, selectedGame));
    return await Promise.all(uploads);
}