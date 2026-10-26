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
    await setupCompileJobButton();
    await setupDownloadButton();
    await setupVmfFileInput();
    await setupGameSelect();
});

const BUTTON_COMPILE_VMF = document.getElementById("button-compile-vmf");
const BUTTON_COMPILE_VMF_ORIGINALTEXT = BUTTON_COMPILE_VMF.querySelector("span")?.innerText;

const LABEL_INPUT_VMF = document.getElementById("label-input-vmf");
const INPUT_VMF = document.getElementById("input-vmf");
const SELECT_GAME = document.getElementById("select-game-vmf");
const RESPONSE_OUTPUT = document.getElementById("response-output");
const COMPILER_OUTPUT = document.getElementById("compiler-output");
const PROGRESS_BAR = document.getElementById("progress-bar");
const DOWNLOAD_BUTTON = document.getElementById("download-button");

const COMPILE_JOB_BUTTON = document.getElementById("button-input-ticket");
const COMPILE_JOB_INPUT = document.getElementById("input-ticket");


let VMF_FILE;
let JOB_ID;

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

async function setupCompileJobButton(){
    COMPILE_JOB_BUTTON.addEventListener("click", async () => {
        const jobId = COMPILE_JOB_INPUT.value;
        JOB_ID = jobId;
        getCompileJobStatus(jobId);
    });
}

async function setupDownloadButton(){
    disableElement(DOWNLOAD_BUTTON);
    DOWNLOAD_BUTTON.addEventListener("click", async () => {
        api.getBsp(JOB_ID)
    });
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
        const ignoreMissingFiles = document.getElementById("ignore-missing-files")?.checked ?? false;
        const fileName = LABEL_INPUT_VMF.innerText;

        disableElement(SELECT_GAME);
        disableElement(INPUT_VMF);
        disableElement(LABEL_INPUT_VMF);
        try {
            const compileResponse = await handleCompileVmfClick(BUTTON_COMPILE_VMF, RESPONSE_OUTPUT, selectedGame, ignoreMissingFiles, VMF_FILE, fileName);
            if(compileResponse) {
                JOB_ID = compileResponse.jobId;
                // 500ms wait for the compile process to start, and the log file to be written
                setTimeout(async () => await getCompileJobStatus(JOB_ID), 500);
            }
        } catch (error) {
            alert(error);
        }
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
    return new Promise((fufill, reject) => {
        const reader = new FileReader();

        reader.onload = function (event) {
            const vmfFile = parseVmfFile(event.target.result);
            fufill({ object: vmfFile, stringrepresentation: event.target.result });
        };

        reader.onerror = function () {
            reject(new Error("Error reading file"));
        };

        reader.readAsText(fileHandle, "UTF-8");
    });
}

async function getCompileJobStatus(jobId) {
    RESPONSE_OUTPUT.classList.remove("error");
    if(!jobId) return;

    let finished = false;
    let response;
    let errorCount;

    while (!finished) {
        try {
            if (errorCount > 5) alert("Job has maybe not started!");

            response = await api.getCompileJob(jobId);
            if(response.success == false){
                RESPONSE_OUTPUT.classList.add("error");
                RESPONSE_OUTPUT.value = "No job with id " + jobId + " found";
                break;
            }
            COMPILER_OUTPUT.value = response.log;
            
            updateStatuses(response.statuses);

            if(response.statuses.filter(rs => rs.status == "finished").length > 0)
            {
                enableElement(SELECT_GAME);
                enableElement(INPUT_VMF);
                enableElement(LABEL_INPUT_VMF);
                enableElement(BUTTON_COMPILE_VMF, BUTTON_COMPILE_VMF_ORIGINALTEXT);
                
                enableElement(DOWNLOAD_BUTTON);

                break;
            }

            await new Promise(resolve => setTimeout(resolve, 500));
        }
        catch (err) {
            console.error("Log fetch error, it will probably be created soon...", err);
            errorCount++;
        }
    }
}

function updateStatuses(statuses){

}
