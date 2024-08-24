import { StateManager } from "./state.js";
import * as api from "./api.js";
import * as ui from "./ui.js";

const stateManager = new StateManager({
  isConnected: false,
  isPollingEnabled: true,
  lastPolledAt: null,
  error: null,
});

document.addEventListener("DOMContentLoaded", async function () {
  // Start UI
  ui.initialize(stateManager);

  // Have UI listen for state changes
  stateManager.subscribe(ui.update);

  // Start polling the API
  api.initialize(stateManager);
});
