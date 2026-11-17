const summary = document.getElementById("stats-summary");
const errorOutput = document.getElementById("stats-error");
const nodesOutput = document.getElementById("stats-nodes");
const refreshButton = document.getElementById("refresh-stats");
let refreshing = false;

async function refreshStats() {
    if (refreshing) return;
    refreshing = true;
    refreshButton.disabled = true;
    try {
        const response = await fetch("/api/stats", { cache: "no-store" });
        if (!response.ok) throw new Error(`Statistics request failed (HTTP ${response.status}): ${await response.text()}`);
        const stats = await response.json();
        const online = stats.nodes.filter(node => node.online).length;
        summary.innerText = `${online}/${stats.nodes.length} nodes online - ${stats.totalRunningJobs} running jobs on reachable nodes`;
        nodesOutput.replaceChildren(...stats.nodes.map(renderNode));
        if (stats.nodes.length === 0) summary.innerText = "No backend nodes configured.";
        errorOutput.hidden = true;
    } catch (error) {
        console.error("Could not load cluster statistics", error);
        summary.innerText = "Statistics unavailable.";
        nodesOutput.replaceChildren();
        errorOutput.innerText = `Could not load cluster statistics: ${error.message}`;
        errorOutput.hidden = false;
    } finally {
        refreshing = false;
        refreshButton.disabled = false;
    }
}

function renderNode(node) {
    const section = document.createElement("fieldset");
    section.className = "main-section stats-node";
    const title = document.createElement("legend");
    title.innerText = node.name;
    const address = document.createElement("p");
    address.innerText = `${node.address} - Weight: ${node.weight}`;
    const status = document.createElement("p");
    status.innerText = node.online ? `Online - ${node.jobCount} running jobs` : `Unavailable: ${node.error}`;
    section.append(title, address, status);
    if (!node.online) {
        status.className = "stats-node-error";
        return section;
    }
    if (node.runningJobs.length === 0) {
        const empty = document.createElement("p");
        empty.innerText = "No running jobs.";
        section.appendChild(empty);
        return section;
    }
    const list = document.createElement("ul");
    for (const job of node.runningJobs) {
        const item = document.createElement("li");
        const id = document.createElement("code");
        id.innerText = job.jobId;
        const details = document.createElement("span");
        details.innerText = ` - ${job.game}${job.fileName ? ` - ${job.fileName}` : ""}`;
        item.append(id, details);
        list.appendChild(item);
    }
    section.appendChild(list);
    return section;
}

refreshButton.addEventListener("click", refreshStats);
refreshStats();
setInterval(refreshStats, 5000);
