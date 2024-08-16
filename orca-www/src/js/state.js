export class StateManager {
    constructor(initialState = {}) {
        this.state = initialState;
        this.prevState = null;
        this.listeners = [];
    }

    update(state) {
        this.prevState = { ...this.state };
        this.state = { ...this.state, ...state };
        this.notify();
    }

    subscribe(listener) {
        this.listeners.push(listener);
    }

    notify() {
        this.listeners.forEach(listener => listener(this));
    }

    get() {
        return this.state;
    }

    getPrev() {
        return this.prevState;
    }
}


export function togglePoll(isEnabled) {
    // Call with null argument to return status. We can use this checkbox
    // to track state instead of the state manager proper so that it's
    // always visible to the user.
    const pollCheckbox = document.getElementById("isPollEnabled");
    if (typeof isEnabled === "undefined") { return pollCheckbox.checked; }
    pollCheckbox.checked = isEnabled
}


export function toggleSearch(isEnabled) {
    const searchForm = document.getElementById("searchForm");
    searchForm.querySelectorAll("*").forEach((e) => e.disabled = !isEnabled);
    console.log(`Search form has been ${isEnabled ? "enabled" : "disabled"}`);
}
