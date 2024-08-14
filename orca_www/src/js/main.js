import { State } from "./state.js";
import { startPolling } from "./api.js";
import { initializeUI, updateUI } from "./ui.js";

const pollingInterval = 5000;
const state = new State({
    isPollingEnabled: true,
    isStillLoading: true,
    isConnected: false,
    lastChecked: null,
    error: null,
})

document.addEventListener("DOMContentLoaded", async () => {
    state.subscribe(updateUI);
    initializeUI(state);
    startPolling(state, pollingInterval);
});
