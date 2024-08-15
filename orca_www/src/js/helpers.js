export function err(msg) {
    // TODO
    console.error(msg);
}


export function fmtSize(bytes) {
    const units = ["", "k", "m", "g", "t"];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) {
        bytes /= 1024;
        i++;
    }
    return `${bytes.toFixed(1)} ${units[i]}b`;
}


export function fmtDate(timestamp, inclSecs = false) {
    const options = {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true
    }
    if (inclSecs) { options.second = "2-digit"; }
    return new Date(timestamp).toLocaleString("en-US", options);
}


export function make(tag, attributes = {}) {
    const element = document.createElement(tag);
    Object.keys(attributes).forEach((key) => {
        if (key === "className") { element.className = attributes[key]; }
        else if (key in element) { element[key] = attributes[key]; }
        else { element.setAttribute(key, attributes[key]); }
    });
    return element;
}


export function spinner() {
    const spinnerElement = make("span", { className: "spinner" });
    return spinnerElement;
}


export function text(content) {
    const textNode = document.createTextNode(content);
    return textNode;
}
