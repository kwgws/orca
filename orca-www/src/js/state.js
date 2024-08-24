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
