import { StateManager } from "./state.js";
import { startPollAPI } from "./api.js";
import { initializeUI, updateUI } from "./ui.js";

const pollInterval = 5000;  // 5 seconds

const stateManager = new StateManager({
    isConnected: false,
    isPollEnabled: true,
    lastPoll: null,
    error: null,
})

document.addEventListener("DOMContentLoaded", async () => {
    console.log("DOM content loaded");
    stateManager.subscribe(updateUI);
    initializeUI(stateManager);
    startPollAPI(stateManager, pollInterval);
});
