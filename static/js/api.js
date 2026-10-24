export async function getExistingGameFiles(filePaths, game) {
    const params = new URLSearchParams({ game: game });

    const response = await sendRequestAsync("POST", "api/resolve-files?" + params, filePaths);
    await isOk(response);
    return await response.json();
}

export async function getConfiguration() {
    const response = await fetch("/api/config");
    await isOk(response)
    return await response.json();
}

export async function compileVmfFile(selectedGame, vmfFile){
    const params = new URLSearchParams({ game: selectedGame });

    const response = await sendFileAsync("api/compile?" + params, vmfFile);
    await isOk(response);
    return await response.json();
}

export async function uploadFileForGame(fileData, path, selectedGame){
    const params = new URLSearchParams({ game: selectedGame, filePath: path });
    const response = await sendFileAsync("api/upload-file?" + params, fileData);
    await isOk(response);
    return await response.json();
}

async function isOk(response) {
    if (response.status != 200) {
        const text = await response.text();
        alert(text);
        throw new Error(text);
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