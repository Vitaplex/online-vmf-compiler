import * as api from "./api.js"
import { parseVmfFile } from "./vmfParser.js";
import { handleCompileVmfClick } from "./vmfCompile.js";
import { addUserCustomFilesInputs } from "./userCustomFilesHelpers.js";
import { disableElement, enableElement } from "./htmlHelpers.js";
import { setupCompilerParameterSnippets } from "./compileParameters.js";
import { addJobToHistory, parseJobHistory } from "./jobHistory.js";

document.addEventListener("DOMContentLoaded", async () => {
    document.querySelectorAll("button").forEach(btn => {
        btn.addEventListener("mousedown", () => { btn.style = "background-color: var(--button-click);" });
        btn.addEventListener("mouseup", () => { btn.style = "background-color: var(--button-active);" });
    });

    addUserCustomFilesInputs();
    setupPreviousJobs();
    await setupCancelCompileButton();
    await setupCompileJobButton();
    await setupDownloadButton();
    await setupCheckJobCount();
    await setupVmfFileInput();
    await setupGameSelect();
    setupCompilerParameterSnippets();
    setupScrollingForCompilerOutput();

    uiState_InitialState();
});

export const RESPONSE_OUTPUT = document.getElementById("response-output");
const CLUSTER_NODE = document.getElementById("cluster-node");
const DROPDOWN_PREVIOUS_JOBS = document.getElementById("users-previous-jobs");
const BUTTON_COMPILE_VMF = document.getElementById("button-compile-vmf");
const BUTTON_COMPILE_VMF_ORIGINALTEXT = BUTTON_COMPILE_VMF.querySelector("span")?.innerText;
const BUTTON_DOWNLOAD = document.getElementById("download-button");
const BUTTON_CANCEL_COMPILE_JOB = document.getElementById("button-cancel-compile");
const BUTTON_GET_COMPILE_JOB = document.getElementById("button-input-ticket");
const INPUT_GET_COMPILE_JOB = document.getElementById("input-ticket");
const LABEL_INPUT_VMF = document.getElementById("label-input-vmf");
const INPUT_VMF = document.getElementById("input-vmf");
const SELECT_GAME = document.getElementById("select-game-vmf");
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
let PREVIOUS_JOBS = [];
const JOB_HISTORY_STORAGE_KEY = "ovmfc.previousJobs";

export function updateClusterNode(nodeName) {
    CLUSTER_NODE.innerText = nodeName;
    CLUSTER_NODE.style.display = nodeName ? "" : "none";
}

function setCurrentJob(jobId) {
    JOB_ID = jobId;
    INPUT_GET_COMPILE_JOB.value = jobId;
    updatePreviousJobSelection();
    updateStatuses([]);
}

function setupPreviousJobs() {
    try {
        const storedHistory = localStorage.getItem(JOB_HISTORY_STORAGE_KEY);
        PREVIOUS_JOBS = parseJobHistory(storedHistory);
        if (storedHistory !== null && storedHistory !== JSON.stringify(PREVIOUS_JOBS)) {
            savePreviousJobs();
        }
    } catch (error) {
        reportJobHistoryError("load", error);
    }

    populatePreviousJobs();
    const summary = DROPDOWN_PREVIOUS_JOBS.querySelector("summary");
    summary.addEventListener("click", event => {
        if (PREVIOUS_JOBS.length === 0) event.preventDefault();
    });
    DROPDOWN_PREVIOUS_JOBS.addEventListener("click", event => {
        const button = event.target.closest("button[data-job-id]");
        if (!button) return;
        INPUT_GET_COMPILE_JOB.value = button.dataset.jobId;
        DROPDOWN_PREVIOUS_JOBS.open = false;
        summary.focus();
        BUTTON_GET_COMPILE_JOB.click();
    });
    DROPDOWN_PREVIOUS_JOBS.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            DROPDOWN_PREVIOUS_JOBS.open = false;
            summary.focus();
        }
    });
    document.addEventListener("click", event => {
        if (!DROPDOWN_PREVIOUS_JOBS.contains(event.target)) DROPDOWN_PREVIOUS_JOBS.open = false;
    });
}

function populatePreviousJobs() {
    const list = DROPDOWN_PREVIOUS_JOBS.querySelector(".job-history-list");
    list.replaceChildren();
    for (const job of PREVIOUS_JOBS) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "job-history-item";
        button.dataset.jobId = job.jobId;
        renderJobDetails(button, job);
        list.appendChild(button);
    }
    DROPDOWN_PREVIOUS_JOBS.querySelector("summary").setAttribute("aria-disabled", PREVIOUS_JOBS.length === 0);
    updatePreviousJobSelection();
}

function updatePreviousJobSelection() {
    const job = PREVIOUS_JOBS.find(entry => entry.jobId === JOB_ID);
    renderJobDetails(DROPDOWN_PREVIOUS_JOBS.querySelector("summary"), job);
    DROPDOWN_PREVIOUS_JOBS.querySelectorAll("button[data-job-id]").forEach(button => {
        button.setAttribute("aria-current", button.dataset.jobId === JOB_ID);
    });
}

function renderJobDetails(element, job) {
    const id = document.createElement("span");
    id.className = "job-history-id";
    id.innerText = job?.jobId ?? "Previous jobs";
    const date = document.createElement("small");
    date.className = "job-history-date";
    date.innerText = job?.startedAt ? new Date(job.startedAt).toLocaleString() : "";
    date.hidden = !job?.startedAt;
    element.replaceChildren(id, date);
    element.title = date.innerText ? `${id.innerText} - ${date.innerText}` : id.innerText;
}

function rememberJob(jobId, startedAt = null) {
    const updatedJobs = addJobToHistory(PREVIOUS_JOBS, jobId, startedAt);
    if (updatedJobs === PREVIOUS_JOBS) return;
    PREVIOUS_JOBS = updatedJobs;
    populatePreviousJobs();
    savePreviousJobs();
}

function savePreviousJobs() {
    try {
        localStorage.setItem(JOB_HISTORY_STORAGE_KEY, JSON.stringify(PREVIOUS_JOBS));
    } catch (error) {
        reportJobHistoryError("save", error);
    }
}

function reportJobHistoryError(action, error) {
    console.error(`Could not ${action} previous jobs`, error);
    RESPONSE_OUTPUT.classList.add("error");
    RESPONSE_OUTPUT.value = `Could not ${action} previous jobs: ${error.message}`;
}

function setupScrollingForCompilerOutput() {
    setInterval(() => {
        const atBottom = COMPILER_OUTPUT.scrollHeight - COMPILER_OUTPUT.scrollTop >= COMPILER_OUTPUT.clientHeight;
        if (atBottom && (!COMPILER_OUTPUT.matches(":focus"))) {
            COMPILER_OUTPUT.scrollTop = COMPILER_OUTPUT.scrollHeight;
        }
    }, 100);
}

async function setupCheckJobCount() {
    setInterval(async () => {
        const count = await api.getJobCount();
        LABEL_RUNNING_JOBS.innerText = count;
    }, 2000);
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
        const jobId = INPUT_GET_COMPILE_JOB.value.trim();
        if (!jobId) return;
        setCurrentJob(jobId);
        await getCompileJobStatus(jobId, true);
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
                const jobId = compileResponse.jobId;
                setCurrentJob(jobId);
                rememberJob(jobId);
                // 500ms wait for the compile process to start, and the log file to be written
                setTimeout(async () => await getCompileJobStatus(jobId), 500);
                return;
            }
            else {
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
    if (!jobId || JOB_ID !== jobId) return;
    RESPONSE_OUTPUT.classList.remove("error");

    let finished = false;
    let response;
    let errorCount = 0;

    uiState_CompilingMap();

    while (!finished && JOB_ID === jobId) {
        try {
            response = await api.getCompileJob(jobId);
            if (JOB_ID !== jobId) return;

            if (response.success == false) {
                COMPILER_OUTPUT.value = "";
                RESPONSE_OUTPUT.classList.add("error");
                RESPONSE_OUTPUT.value = "No job with id " + jobId + " found";
                finished = true;
                if (VMF_FILE) uiState_ReadyToCompile();
                else uiState_InitialState();
                break;
            }

            const statuses = response.statuses ?? [];
            if (response.success === true) rememberJob(jobId, statuses[0]?.time ?? null);

            if (errorCount > 5) {
                finished = true;
                uiState_ReadyToCompile();
            }

            COMPILER_OUTPUT.value = response.log?.trim();

            updateStatuses(statuses);

            finished = statuses.some(status => status.tag === "finished");

            if (fromCompileJobButton && finished) {
                uiState_GetFinishedCompileJob();
                BUTTON_DOWNLOAD.querySelector("a").href = "/api/bsp/" + jobId;
                BUTTON_DOWNLOAD.querySelector("a").target = "_blank";

                break;
            }

            if (finished) {
                BUTTON_DOWNLOAD.querySelector("a").href = "/api/bsp/" + jobId;
                BUTTON_DOWNLOAD.querySelector("a").target = "_blank";

                uiState_CompileJobFinished();
                break;
            }

        }
        catch (err) {
            console.error(err);
            errorCount++;
        }
        finally {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
    }
}

function updateStatuses(statuses) {
    const statusTypes = ["queued", "failed", "running", "finished"];
    const stages = [
        ["vbsp", PROGRESS_BAR.vbspStatus],
        ["vvis", PROGRESS_BAR.vvisStatus],
        ["vrad", PROGRESS_BAR.vradStatus],
        ["finished", PROGRESS_BAR.finishedStatus]
    ].map(([tag, element]) => ({ element, status: statuses.find(status => status.tag === tag) }));
    const currentStage = stages.findLastIndex(stage => stage.status);

    enableElement(PROGRESS_BAR.progressBar);
    stages.forEach(({ element, status }, index) => {
        element.classList.remove(...statusTypes);
        element.classList.add(currentStage === stages.length - 1 || index < currentStage
            ? "finished"
            : index === currentStage ? "running" : "queued");
        const date = element.querySelector(".progress-date");
        date.innerText = status?.time ? new Date(status.time).toLocaleString() : "";
        date.title = status?.time ?? "";
        date.hidden = !status?.time;
    });
}

function uiState_ReadyToCompile() {
    uiState_CompileJobFinished();
    enableElement(BUTTON_COMPILE_VMF);
    disableElement(BUTTON_DOWNLOAD);
}

function uiState_InitialState() {
    uiState_CompileJobFinished();
    disableElement(BUTTON_CANCEL_COMPILE_JOB);
    disableElement(BUTTON_DOWNLOAD);
    disableElement(BUTTON_COMPILE_VMF);
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