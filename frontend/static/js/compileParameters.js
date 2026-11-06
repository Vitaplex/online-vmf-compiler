
export function setupCompilerParameterSnippets() {
    const COMPILE_PARAMS = document.querySelectorAll(".compile-parameters");
    COMPILE_PARAMS.forEach(cp => {
        const button = cp.querySelector("button");
        const paramsList = cp.querySelector(".compile-parameters-list");
        const params = [... cp.querySelectorAll(".compile-parameters-list li")];
        const input = cp.querySelector("input");
        button.addEventListener("click", () => {});
         console.log(params);
        params.forEach(pm => pm.addEventListener("click", () => {
            input.value = pm.innerHTML;
        }));
    });
}