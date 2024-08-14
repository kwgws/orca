export class State {
    constructor(initialState = {}) {
        this.state = initialState;
        this.listeners = [];
    }

    update(state) {
        this.state = { ...this.state, ...state };
        this.notify();
    }

    subscribe(listener) {
        this.listeners.push(listener);
    }

    notify() {
        this.listeners.forEach(listener => listener(this.state));
    }

    get() {
        return this.state;
    }
}