export async function getExistingGameFiles(filePaths, game){
    const params = new URLSearchParams({game: game});

    const response = await sendRequestAsync("POST", "api/files?" + params, filePaths);
    await isOk(response);
    return await response.json();
}

export async function compileVmfFile(userCustomFiles, selectedGame, vmfFile){
    const params = new URLSearchParams({game: selectedGame});
    
    await Promise.all(userCustomFiles.map(async ucf =>{
        
        const response = await sendRequestAsync("POST", "api/file?" + params, filePaths);

    }));

    const response = await sendRequestAsync("POST", "api/compile?" + params, filePaths);
    await isOk(response);
    return await response.json();
}

export async function getConfiguration() {
    const response = await fetch("/api/config");
    await isOk(response)
    return await response.json();
}

async function isOk(response) {
    if (response.status != 200) {
        const text = await response.text();
        alert(text);
        throw new Error(text);
    }
}

async function sendRequestAsync(method, url, body){
    return await fetch(url, {
        method: method,
        body: JSON.stringify(body),
        headers: method == "GET" ? null : {
            "Content-Type": "application/json; charset=UTF-8"
        }
    })
}