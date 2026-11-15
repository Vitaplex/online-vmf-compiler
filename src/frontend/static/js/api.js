import { RESPONSE_OUTPUT } from "./main.js";

export async function getExistingGameFiles(filePaths, game) {
    const params = new URLSearchParams({ game: game });

    const response = await sendRequestAsync("POST", "/api/resolve-files?" + params, filePaths);
    await isOk(response);
    return await response.json();
}

export async function getConfiguration() {
    const response = await fetch("/api/config");
    await isOk(response)
    return await response.json();
}

export async function getCompileJob(jobId) {
    const response = await fetch("/api/compile/" + jobId);
    return await response.json();
}

export async function cancelCompileJob(jobId) {
    const response = await fetch("/api/compile/" + jobId, { method: "DELETE" });
    return await response.json();
}

export async function getJob(jobId) {
    const response = await fetch("/api/compile/" + jobId);
    await isOk(response);
    return await response.json();
}

export async function getJobCount() {
    const response = await fetch("/api/jobs-count/");
    await isOk(response);
    return await response.text();
}

export async function compileVmfFile(selectedGame, vmfFile, fileName, compileParams) {
    const params = new URLSearchParams({ game: selectedGame, fileName: fileName });
    if (compileParams?.vbsp) params.append("vbspParams", compileParams.vbsp);
    if (compileParams?.vvis) params.append("vvisParams", compileParams.vvis);
    if (compileParams?.vrad) params.append("vradParams", compileParams.vrad);

    const response = await sendFileAsync("/api/compile?" + params, vmfFile);
    await isOk(response);
    return await response.json();
}

export async function uploadFileForGame(fileData, path, selectedGame) {
    const params = new URLSearchParams({ game: selectedGame, filePath: path });
    const response = await sendFileAsync("/api/upload-file?" + params, fileData);
    await isOk(response);
    return await response.json();
}

async function isOk(response) {
    // Backend unavailable

    if (response.status != 200) {
        const text = await response.text();
        if (response.status == 502) {
            RESPONSE_OUTPUT.classList.add("error");
            RESPONSE_OUTPUT.value = "Backend unavailable\n" + text;
            throw new Error(text);
        }
        else {
            alert(text);
            throw new Error(text);
        }
    }
}

async function sendRequestAsync(method, url, body) {
    return await fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: method == "GET" ? null : {
            "Content-Type": "application/json; charset=UTF-8"
        }
    })
}

async function sendFileAsync(url, file) {
    return await fetch(url, {
        method: "POST",
        body: file,
        headers: {
            "Content-Type": "application/octet-stream"
        }
    })
}