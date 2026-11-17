import { toggleStyle, anyChildOfParentByClassName } from "./htmlHelpers.js";

const COMPILE_PARAMS_LIST = [...document.querySelectorAll(".compile-parameters-list")];

export function setupCompilerParameterSnippets() {

    const compileParams = document.querySelectorAll(".compile-parameters");
    compileParams.forEach(cp => {
        const option = cp.querySelector("datalist option");
        option.addEventListener("click", () => {
            input.value += pm.innerText;
        });
    });
}