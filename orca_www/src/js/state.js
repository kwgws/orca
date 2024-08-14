export class StateManager {
    constructor(initialState = {}) {
        this.state = initialState;
        this.oldState = null;
        this.listeners = [];
    }

    update(state) {
        this.oldState = { ...this.state };
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

    getOld() {
        return this.oldState;
    }
}