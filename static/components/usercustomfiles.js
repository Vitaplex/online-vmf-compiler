import { addUserCustomFilesInputs } from "../js/userCustomFilesHelpers.js"

class UserCustomFiles extends HTMLElement {
    constructor() {
        super();
        this.materials = [];
        this.models = [];
        this.scripts = [];
        this.sounds = [];

        this.folderName = null;

        this.state = "unselected";
    }

    getFiles() {
        if (this.state === "unselected") {
            return;
        }

        while (this.state === "loading") { }

        if (this.state === "ready") {
            return this.materials.concat(this.models).concat(this.scripts).concat(this.sounds);
        }
    }

    async connectedCallback() {
        let response;
        try {
            response = await fetch("/static/components/UserCustomFiles.html");
            if (!response.ok) throw new Error("UserCustomFiles.html found");
        }
        catch (err) {
            console.error("Load error:", err);
            this.innerHTML = `<div style="color: red;">Failed to UserCustomFiles component</div>`;
        }

        this.innerHTML = await response.text();

        const label = this.querySelector("label");
        const input = this.querySelector("input");

        const existingText = label.innerText;

        label.addEventListener("click", () => {
            document.body.classList.add("loading");
            input.click();
            label.innerHTML = `<img style="height:24px" src="/static/media/loading.gif"> Loading files...`;
        });

        input.addEventListener("cancel", () => {
            if (this.state === "ready") {
                this.remove();
            } else {
                label.innerText = existingText;
            }
            document.body.classList.remove("loading");
        });

        input.addEventListener("change", async (event) => {
            this.state = "loading";
            const files = event.target.files;
            this.folderName = getUploadedFolderName(files);
            const folderNameRegex = new RegExp(`^${this.folderName}/`);
            for (const file of files) {
                const fileObject = { path: file.webkitRelativePath.replace(folderNameRegex, ""), file: file };
                if (this.resolveFolder(file, "materials")) {
                    this.materials.push(fileObject);
                }
                else if (this.resolveFolder(file, "models")) {
                    this.models.push(fileObject);
                }
                else if (this.resolveFolder(file, "scripts")) {
                    this.scripts.push(fileObject);
                }
                else if (this.resolveFolder(file, "sound")) {
                    this.sounds.push(fileObject);
                }
            }

            label.innerHTML = this.formatLabel();

            this.state = "ready";
            addUserCustomFilesInputs();
            document.body.classList.remove("loading");
        });

    }

    resolveFolder(file, directoryFolderName) {
        return file.webkitRelativePath.startsWith(this.folderName + `/${directoryFolderName}/`);
    }

    formatLabel() {
        return `<code>/${this.folderName}</code>
        <small><br>
            🖼 Materials: ${this.materials.length}<br>
            🍶 Models: ${this.models.length}<br>
            📜 Scripts: ${this.scripts.length}<br>
            🔊 Sounds: ${this.sounds.length}
        </small>`
    }
}

customElements.define("game-directory", UserCustomFiles);




function getUploadedFolderName(files) {
    let firstFile = files.length > 0 ? files[0] : null;
    let folderName = firstFile.webkitRelativePath.split("/");

    return folderName[0];
}
