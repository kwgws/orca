import { pollInterval } from "./config.js";
import { StateManager } from "./state.js";
import { startPollAPI } from "./api.js";
import { updateUI } from "./ui.js";

const stateManager = new StateManager({
  isConnected: false,
  lastPoll: null,
  error: null,
});

document.addEventListener("DOMContentLoaded", async () => {
  console.log("DOM content loaded");
  stateManager.subscribe(updateUI);
  startPollAPI(stateManager, pollInterval);
});
