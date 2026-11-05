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
    await setupCancelCompileButton();
    await setupCompileJobButton();
    await setupDownloadButton();
    await setupCheckJobCount();
    await setupVmfFileInput();
    await setupGameSelect();
    setupScrollingForCompilerOutput();

    uiState_InitialState();
});

const BUTTON_COMPILE_VMF = document.getElementById("button-compile-vmf");
const BUTTON_COMPILE_VMF_ORIGINALTEXT = BUTTON_COMPILE_VMF.querySelector("span")?.innerText;
const BUTTON_DOWNLOAD = document.getElementById("download-button");
const BUTTON_CANCEL_COMPILE_JOB = document.getElementById("button-cancel-compile");
const BUTTON_GET_COMPILE_JOB = document.getElementById("button-input-ticket");
const INPUT_GET_COMPILE_JOB = document.getElementById("input-ticket");
const LABEL_INPUT_VMF = document.getElementById("label-input-vmf");
const INPUT_VMF = document.getElementById("input-vmf");
const SELECT_GAME = document.getElementById("select-game-vmf");
const RESPONSE_OUTPUT = document.getElementById("response-output");
const COMPILER_OUTPUT = document.getElementById("compiler-output");
const LABEL_RUNNING_JOBS = document.getElementById("label-running-jobs");

const PROGRESS_BAR = {
    progressBar: document.getElementById("progress-bar"),
    vbspStatus: document.getElementById("progress-vbsp"),
    vvisStatus: document.getElementById("progress-vvis"),
    vradStatus: document.getElementById("progress-vrad"),
    finishedStatus: document.getElementById("progress-finished")
};

let VMF_FILE;
let JOB_ID;

function setupScrollingForCompilerOutput() {
    setInterval(() => {
        const atBottom = COMPILER_OUTPUT.scrollHeight - COMPILER_OUTPUT.scrollTop >= COMPILER_OUTPUT.clientHeight;
        if (atBottom && (!COMPILER_OUTPUT.matches(":focus"))) {
            COMPILER_OUTPUT.scrollTop = COMPILER_OUTPUT.scrollHeight;
        }
    }, 100);
}

async function setupCheckJobCount(){
    setInterval(async () => {
        const count = await api.getJobCount();
        LABEL_RUNNING_JOBS.innerText = count;
    },2000);
}

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

async function setupCompileJobButton() {
    BUTTON_GET_COMPILE_JOB.addEventListener("click", async () => {
        const jobId = INPUT_GET_COMPILE_JOB.value;
        JOB_ID = jobId;
        getCompileJobStatus(jobId, true);
    });
}

async function setupCancelCompileButton() {
    BUTTON_CANCEL_COMPILE_JOB.addEventListener("click", async () => {
        // disableElement(BUTTON_CANCEL_COMPILE_JOB,"Cancelling");
        const response = api.cancelCompileJob(JOB_ID);
        uiState_InitialState();
    });
}

async function setupDownloadButton() {
    disableElement(BUTTON_DOWNLOAD);
    BUTTON_DOWNLOAD.addEventListener("click", async () => {
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
    });


    BUTTON_COMPILE_VMF.addEventListener("click", async () => {
        const selectedGame = SELECT_GAME.options[SELECT_GAME.selectedIndex].innerText;
        const ignoreMissingFiles = document.getElementById("ignore-missing-files")?.checked ?? false;
        const fileName = LABEL_INPUT_VMF.innerText;

        const compilerParameters = {
            vbsp: document.getElementById("input-vbsp-params").value,
            vvis: document.getElementById("input-vvis-params").value,
            vrad: document.getElementById("input-vrad-params").value,
        };  

        uiState_CompilingMap();
        try {
            RESPONSE_OUTPUT.classList.remove("error");
            const compileResponse = await handleCompileVmfClick(
                BUTTON_COMPILE_VMF, 
                RESPONSE_OUTPUT, 
                selectedGame, 
                ignoreMissingFiles, 
                VMF_FILE, 
                fileName, 
                compilerParameters);
                
            if (compileResponse) {
                JOB_ID = compileResponse.jobId;
                // 500ms wait for the compile process to start, and the log file to be written
                setTimeout(async () => await getCompileJobStatus(JOB_ID), 500);
                return;
            }
            else{
                uiState_ReadyToCompile();
                return;
            }
        } catch (error) {
            alert(error);
        }

        uiState_InitialState();
    });
}


async function handleVmfUpload(event) {
    enableElement(BUTTON_COMPILE_VMF);

    const file = event.target.files[0];
    LABEL_INPUT_VMF.innerHTML = `Loading .vmf file...`;

    VMF_FILE = await readAndParseVmfFile(file);

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

async function getCompileJobStatus(jobId, fromCompileJobButton = false) {
    RESPONSE_OUTPUT.classList.remove("error");
    if (!jobId) return;

    let finished = false;
    let response;
    let errorCount = 0;
    
    uiState_CompilingMap();

    while (!finished) {
        try {
            if (errorCount > 5) {
                alert("Job has maybe not started!");
                break;
            }
            response = await api.getCompileJob(jobId);
            
            if (!response || response.success == false) {
                COMPILER_OUTPUT.value = "";
                RESPONSE_OUTPUT.classList.add("error");
                RESPONSE_OUTPUT.value = "No job with id " + jobId + " found";
                break;
            }

            COMPILER_OUTPUT.value = response.log?.trim();

            updateStatuses(response.statuses);

            finished = response.statuses.filter(rs => rs.status == "finished").length > 0;

            if (fromCompileJobButton && finished) {
                uiState_GetFinishedCompileJob();
                break;
            }

            if (finished) {
                uiState_CompileJobFinished();
                break;
            }

            await new Promise(resolve => setTimeout(resolve, 200));
        }
        catch (err) {
            console.error("Log fetch error, it will probably be created soon...", err);
            errorCount++;
        }
    }
}

function updateStatuses(statuses) {
    const statusTypes = ["queued", "failed", "running", "finished"];

    enableElement(PROGRESS_BAR.progressBar);

    const vbsp = statuses.filter(rs => rs.status == "vbsp");
    const vvis = statuses.filter(rs => rs.status == "vvis");
    const vrad = statuses.filter(rs => rs.status == "vrad");
    const finished = statuses.filter(rs => rs.status == "finished");

    if (vbsp.length > 0 && !PROGRESS_BAR.vbspStatus.classList.contains("finished")) {
        setStatus(PROGRESS_BAR.vbspStatus, "running");
        setStatus(PROGRESS_BAR.vvisStatus, "queued");
        setStatus(PROGRESS_BAR.vradStatus, "queued");
        setStatus(PROGRESS_BAR.finishedStatus, "queued");
    }
    if (vvis.length > 0 && !PROGRESS_BAR.vvisStatus.classList.contains("finished")) {
        setStatus(PROGRESS_BAR.vbspStatus, "finished");
        setStatus(PROGRESS_BAR.vvisStatus, "running");
        setStatus(PROGRESS_BAR.vradStatus, "queued");
        setStatus(PROGRESS_BAR.finishedStatus, "queued");
    }
    if (vrad.length > 0 && !PROGRESS_BAR.vradStatus.classList.contains("finished")) {
        setStatus(PROGRESS_BAR.vbspStatus, "finished");
        setStatus(PROGRESS_BAR.vvisStatus, "finished");
        setStatus(PROGRESS_BAR.vradStatus, "running");
        setStatus(PROGRESS_BAR.finishedStatus, "queued");
    }
    if (finished.length > 0) {
        setStatus(PROGRESS_BAR.vbspStatus, "finished");
        setStatus(PROGRESS_BAR.vvisStatus, "finished");
        setStatus(PROGRESS_BAR.vradStatus, "finished");
        setStatus(PROGRESS_BAR.finishedStatus, "finished");
    }

    function setStatus(element, status) {
        element.classList.remove(...statusTypes);
        element.classList.add(status);
    }
}

function uiState_ReadyToCompile() {
    uiState_CompileJobFinished();
    enableElement(BUTTON_COMPILE_VMF);
    disableElement(BUTTON_DOWNLOAD);
}

function uiState_InitialState() {
    uiState_CompileJobFinished();
    disableElement(BUTTON_COMPILE_VMF);
    disableElement(BUTTON_DOWNLOAD);
}

function uiState_GetFinishedCompileJob() {
    uiState_CompileJobFinished();
    enableElement(BUTTON_DOWNLOAD);
    disableElement(BUTTON_COMPILE_VMF);
}

function uiState_CompileJobFinished() {
    enableElement(SELECT_GAME);
    enableElement(INPUT_VMF);
    enableElement(LABEL_INPUT_VMF);
    enableElement(BUTTON_COMPILE_VMF, BUTTON_COMPILE_VMF_ORIGINALTEXT);
    enableElement(BUTTON_DOWNLOAD);
    disableElement(BUTTON_CANCEL_COMPILE_JOB);
}

function uiState_CompilingMap() {
    disableElement(SELECT_GAME);
    disableElement(INPUT_VMF);
    disableElement(LABEL_INPUT_VMF);
    disableElement(BUTTON_DOWNLOAD);
    enableElement(BUTTON_CANCEL_COMPILE_JOB);
}