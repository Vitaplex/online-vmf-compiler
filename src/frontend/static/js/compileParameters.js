import { toggleStyle, anyChildOfParentByClassName } from "./htmlHelpers.js";

const COMPILE_PARAMS_LIST = [... document.querySelectorAll(".compile-parameters-list")];

export function setupCompilerParameterSnippets() {
    document.addEventListener("click", (event) => {
        if(anyChildOfParentByClassName(event.target, "compile-parameters-list") == true)
            COMPILE_PARAMS_LIST.forEach(cpl => cpl.style.display = "none");
    });

    const compileParams = document.querySelectorAll(".compile-parameters");
    compileParams.forEach(cp => {
        const button = cp.querySelector("button");
        const paramsList = cp.querySelector(".compile-parameters-list");
        const params = [... cp.querySelector(".compile-parameters-list").childNodes];
        const input = cp.querySelector("input");
        button.addEventListener("click", () => {
            paramsList.style.display = toggleStyle(paramsList.style.display, "none");
        });
         console.log(params);
        params.forEach(pm => pm.addEventListener("click", () => {   
            input.value = pm.innerText;
        }));
    });
}