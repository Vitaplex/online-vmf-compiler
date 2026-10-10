export function disableButton(button, text){
    button.disabled = "true";
    button.classList.add("inactive");
    button.querySelector("span").innerText = text;
}

export function enableButton(button, text){
    button.disabled = "false";
    button.classList.remove("inactive");
    button.querySelector("span").innerText = text;
}