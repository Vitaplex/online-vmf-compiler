import * as api from "./api.js";
import { getUserCustomFilesFromPage, addUserCustomFilesInputs } from "./userCustomFilesHelpers.js"
import { enableElement, disableElement } from "./htmlHelpers.js";
import { resolveAssetsInVmfFile, resolveCustomFilesInVmf } from "./vmfParser.js";

export async function handleCompileVmfClick(button, outputArea, selectedGame, ignoreMissingFiles, vmfFileObject, fileName) {
    outputArea.classList.remove("error");

    if (!vmfFileObject) alert("No .vmf file selected!");

    disableElement(button, "Getting custom files...");
    const userCustomFiles = getUserCustomFilesFromPage();

    disableElement(button, "Resolving assets in .vmf file...");
    const vmfFiles = resolveAssetsInVmfFile(vmfFileObject.object);
    const filePathList = [...vmfFiles.materials, ...vmfFiles.models, ...vmfFiles.sounds];

    disableElement(button, "Finding local files...");
    const filesNotInLocalDir = await api.getExistingGameFiles(filePathList, selectedGame);

    if (filesNotInLocalDir.length > 0) {
        console.warn(`Could not find these files in selected game directory for ${selectedGame} (including vpks)`, filesNotInLocalDir);
    }

    const missingFiles = resolveCustomFilesInVmf(userCustomFiles, filesNotInLocalDir);

    if (missingFiles && !ignoreMissingFiles) {
        console.warn("Missing files not provided by the user!", missingFiles);
        outputArea.classList.add("error");
        outputArea.value = `Missing assets!\nThese assets are missing locally, and is not provided by the user using the "Select custom files" option:\n\n` + Array.from(missingFiles).join("\n");
        return;
    }
    else if (missingFiles) {
        disableElement(button, "Uploading custom files...");
        const response = await uploadFiles(missingFiles, selectedGame);
        const errors = response.filter(e => !e.success);
        if (errors) errors.forEach(err => { outputArea.value += "Error uploading file: " + JSON.stringify(err.path) + "\n" });
    }

    disableElement(button, "Compiling vmf-file...");
    return await sendVmfToBackend(selectedGame, vmfFileObject.stringrepresentation, fileName)
}

async function sendVmfToBackend(selectedGame, vmfFile, fileName) {
    const response = await api.compileVmfFile(selectedGame, vmfFile, fileName);
    return response;
}

async function uploadFiles(userCustomFiles, selectedGame) {
    // Remove duplicate paths
    const dedupUserCustomFiles = dedupBasedOnProperty(userCustomFiles, (dd) => dd.path);

    // Create an array of tasks that each upload one of the files
    // TODO: Maybe add batching to avoid spamming HTTP requests? 
    const uploads = dedupUserCustomFiles.map(async ucf => new Promise((fufill, reject) => {
        const reader = new FileReader();
        reader.onloadstart = (event) => { console.log("START", event) };
        reader.onprogress = (event) => { console.log("PROGRESS", event) };
        reader.onloadend = (event) => { console.log("END", event) };
        reader.onabort = (event) => { console.log("ABORT", event) };

        reader.onload = async (event) => {
            const response = await api.uploadFileForGame(event.target.result, ucf.path, selectedGame);
            fufill(response);
        };

        reader.onerror = (event) => {
            console.log("ERROR", event);
            reject(new Error("Error reading file"));
        };

        reader.readAsArrayBuffer(ucf.file);
    }));

    return await Promise.all(uploads);
}

function dedupBasedOnProperty(array, func) {
    return [...array.reduce((m, r) => {
        const key = func(r);
        return m.has(key) ? m : m.set(key, r);
    }, new Map()).values()];
}