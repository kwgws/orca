import { StateManager } from "./state.js";
import { startPolling } from "./api.js";
import { initializeUI, updateUI } from "./ui.js";

const pollingInterval = 5000;
const stateManager = new StateManager({
    isPollingEnabled: true,
    isStillLoading: true,
    isConnected: false,
    lastChecked: null,
    error: null,
})

document.addEventListener("DOMContentLoaded", async () => {
    console.log("DOM content loaded");
    stateManager.subscribe(updateUI);
    initializeUI(stateManager);
    startPolling(stateManager, pollingInterval);
});
