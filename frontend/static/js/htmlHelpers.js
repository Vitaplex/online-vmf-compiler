export function disableElement(element, text) {
    element.disabled = true;
    element.classList.add("inactive");
    handleText(element,text);
}

export function enableElement(element, text) {
    if(!element) return;
    element.disabled = false;
    element.classList.remove("inactive");
    if (!text) return;
    handleText(element,text);
}

function handleText(element, text) {
    if (!text || !element) return;

    const span = element.querySelector("span");

    if (span) {
        span.innerText = text;
    }
    else {
        element.innerText = text;
    }
}