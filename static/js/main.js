import * as api from "./api.js"
import { parseVmfFile } from "./vmfParser.js";
import { handleCompileVmfClick } from "./vmfCompile.js";
import { addUserCustomFilesInputs } from "./userCustomFilesHelpers.js";
import { disableElement, enableElement } from "./htmlHelpers.js";

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
const RESPONSE_OUTPUT = document.getElementById("response-output");

let VMF_FILE;

async function setupGameSelect() {
    const localDirectory = await api.getConfiguration();

    const options = [...localDirectory].map(ld => createOptionForGame(ld));
    const optgroup = document.createElement("optgroup");
    optgroup.label = "Select game";

    for (const opt of options) {
        optgroup.appendChild(opt);
    }

    SELECT_GAME.appendChild(optgroup);
}

function createOptionForGame(configElement) {
    const option = document.createElement("option");

    option.innerText = configElement.name;
    return option;
}

async function setupVmfFileInput() {
    BUTTON_COMPILE_VMF.disabled = true;

    const vmfInputLabelOriginalText = LABEL_INPUT_VMF.innerText;

    INPUT_VMF.addEventListener("change", (event) => handleVmfUpload(event));

    INPUT_VMF.addEventListener("cancel", (event) => {
        LABEL_INPUT_VMF.innerHTML = vmfInputLabelOriginalText;
        disableElement(BUTTON_COMPILE_VMF);
        enableElement(SELECT_GAME);
        enableElement(INPUT_VMF);
        enableElement(LABEL_INPUT_VMF);

    });

    BUTTON_COMPILE_VMF.addEventListener("click", async () => {
        const selectedGame = SELECT_GAME.options[SELECT_GAME.selectedIndex].innerText;
        const originalText = BUTTON_COMPILE_VMF.querySelector("span")?.innerText;
        disableElement(SELECT_GAME);
        disableElement(INPUT_VMF);
        disableElement(LABEL_INPUT_VMF);

        await handleCompileVmfClick(BUTTON_COMPILE_VMF, RESPONSE_OUTPUT, selectedGame, VMF_FILE);

        enableElement(SELECT_GAME);
        enableElement(INPUT_VMF);
        enableElement(LABEL_INPUT_VMF);
        enableElement(BUTTON_COMPILE_VMF, originalText);
    });
}

async function handleVmfUpload(event) {
    enableElement(BUTTON_COMPILE_VMF);

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