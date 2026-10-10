import * as api from "./api.js"
import { parseVmfFile } from "./vmfParser.js";
import { handleCompileVmfClick } from "./vmfCompile.js";
import { addUserCustomFilesInputs } from "./UserCustomFileshelpers.js";

document.addEventListener("DOMContentLoaded", async () => {
    document.querySelectorAll("button").forEach(btn => {
        btn.addEventListener("mousedown", () => { btn.style = "background-color: var(--button-click);" });
        btn.addEventListener("mouseup", () => { btn.style = "background-color: var(--button-active);" });
    });
    addUserCustomFilesInputs();
    await setupVmfFileInput();
    await setupGameSelect();
});

const BUTTON_COMPILE_VMF = document.getElementById("button-compile-vmf");
const LABEL_INPUT_VMF = document.getElementById("label-input-vmf");
const INPUT_VMF = document.getElementById("input-vmf");
const SELECT_GAME = document.getElementById("select-game-vmf");

let VMF_FILE;

async function setupGameSelect() {
    const localDirectory = await api.getConfiguration();

    const options = [...localDirectory].map(ld => createOptionForGame(ld.name));
    const optgroup = document.createElement("optgroup");
    optgroup.label = "Select game";

    for (const opt of options) {
        optgroup.appendChild(opt);
    }

    SELECT_GAME.appendChild(optgroup);
}

function createOptionForGame(name) {
    const option = document.createElement("option");

    option.innerText = name;
    return option;
}

async function setupVmfFileInput() {
    BUTTON_COMPILE_VMF.disabled = true;

    const vmfInputLabelOriginalText = LABEL_INPUT_VMF.innerText;

    INPUT_VMF.addEventListener("change", (event) => handleVmfUpload(event));

    INPUT_VMF.addEventListener("cancel", (event) => {
        LABEL_INPUT_VMF.innerHTML = vmfInputLabelOriginalText;
        BUTTON_COMPILE_VMF.disabled = true;
        BUTTON_COMPILE_VMF.classList.add("inactive")
    });

    BUTTON_COMPILE_VMF.addEventListener("click", async () => {
        const selectedGame = SELECT_GAME.options[SELECT_GAME.selectedIndex].innerText;
        handleCompileVmfClick(BUTTON_COMPILE_VMF, selectedGame, VMF_FILE);
    });
}

async function handleVmfUpload(event) {
    BUTTON_COMPILE_VMF.classList.remove("inactive")
    BUTTON_COMPILE_VMF.disabled = false;

    const file = event.target.files[0];
    LABEL_INPUT_VMF.innerHTML = `Loading .vmf file...`;
    VMF_FILE = await readAndParseVmfFile(file);
    console.log(VMF_FILE);

    LABEL_INPUT_VMF.innerHTML = `<code>${file.name}</code>`;
}


function readAndParseVmfFile(fileHandle) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = function (event) {
            const vmfFile = parseVmfFile(event.target.result);
            resolve(vmfFile);
        };

        reader.onerror = function () {
            reject(new Error("Error reading file"));
        };

        reader.readAsText(fileHandle, "UTF-8");
    });
}