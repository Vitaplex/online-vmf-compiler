
export function getUserCustomFilesFromPage() {
    const UserCustomFiles = document.querySelectorAll("game-directory");
    return [... UserCustomFiles].map(gdr => gdr.getFiles()).filter(gdr => gdr != undefined).flat();
}

export function addUserCustomFilesInputs() {
    const leftSection = document.getElementById("section-left");
    const UserCustomFiles = document.createElement("game-directory");
    leftSection.appendChild(UserCustomFiles);
}
