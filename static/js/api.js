export async function getGameFiles(game) {
    const params = new URLSearchParams({game: game});
    const response = await fetch("/api/files?" + params);
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