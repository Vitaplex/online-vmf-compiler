export function disableElement(element, text){
    element.disabled = true;
    element.classList.add("inactive");
    if(!text) return;
    element.querySelector("span").innerText = text;
}

export function enableElement(element, text){
    element.disabled = false;
    element.classList.remove("inactive");
    if(!text) return;
    element.querySelector("span").innerText = text;
}