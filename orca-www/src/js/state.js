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
    this.listeners.forEach((listener) => listener(this));
  }

  get() {
    return this.state;
  }

  getPrev() {
    return this.prevState;
  }
}

export function togglePoll(isEnabled) {
  /* Call with null argument to return status.
   * We use this checkbox to track state instead of the state manager proper so
   * that it's always visible to the user (and accessible via the DOM).
   */
  const pollCheckbox = document.getElementById("isPollEnabled");
  if (typeof isEnabled === "undefined") {
    return pollCheckbox.checked;
  }
  pollCheckbox.checked = isEnabled;
  console.log(`Polling ${isEnabled ? "enabled" : "disabled"}`);
}

export function toggleSearch(isEnabled) {
  const searchForm = document.getElementById("searchForm");
  searchForm.querySelectorAll("*").forEach((e) => (e.disabled = !isEnabled));
  console.log(`Search form ${isEnabled ? "enabled" : "disabled"}`);
}
