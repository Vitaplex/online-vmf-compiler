import { RESPONSE_OUTPUT } from "./main.js";

export let NODE_NAME = null;

export async function getExistingGameFiles(filePaths, game) {
    const params = new URLSearchParams({ game: game });

    const response = await sendRequestAsync("POST", "/api/resolve-files?" + params, filePaths);
    await isOk(response);
    return await response.json();
}

export async function getConfiguration() {
    const response = await fetchFromApi("/api/config");
    await isOk(response)
    return await response.json();
}

export async function getCompileJob(jobId) {
    const response = await fetchFromApi("/api/compile/" + jobId);
    return await response.json();
}

export async function cancelCompileJob(jobId) {
    const response = await fetchFromApi("/api/compile/" + jobId, { method: "DELETE" });
    return await response.json();
}

export async function getJob(jobId) {
    const response = await fetchFromApi("/api/compile/" + jobId);
    await isOk(response);
    return await response.json();
}

export async function getJobCount() {
    const response = await fetchFromApi("/api/jobs-count");
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

    if (response.status != 200 && response.status != 307) {
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

async function fetchFromApi(url, options = {}) {
    const headers = getRequestHeaders({
        ...(options.headers || {})
    });

    const response = await fetch(url, {
        ...options,
        headers
    });

    updateNodeName(response);

    return response;
}

function getRequestHeaders(headers = {}) {
    if (NODE_NAME) {
        headers["X-Preferred-Node"] = NODE_NAME;
    }

    return headers;
}

async function sendRequestAsync(method, url, body) {
    return await fetchFromApi(url, {
        method: method,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        headers: getRequestHeaders(
            method !== "GET" ? {
                "Content-Type": "application/json; charset=UTF-8"
            } : {}
        )
    });
}

async function sendFileAsync(url, file) {
    return await fetchFromApi(url, {
        method: "POST",
        body: file,
        headers: getRequestHeaders({
            "Content-Type": "application/octet-stream"
        })
    });
}
// CLUSTER-specific
function updateNodeName(response) {
    const nodeName = response.headers.get("X-Served-By");

    if (nodeName) {
        NODE_NAME = nodeName;
        console.log("Backend node:", NODE_NAME);
    }
}