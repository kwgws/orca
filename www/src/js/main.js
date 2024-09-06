"use strict";

import "../scss/main.scss";
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
  // Set theme based on system preference
  const setTheme = (theme) => {
    document.documentElement.style.transition = // Add a slight transition effect
      "background-color 0.3s ease, color 0.3s ease";
    document.documentElement.setAttribute("data-bs-theme", theme);
  };

  const getPreferredTheme = () => {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };

  const applyTheme = () => {
    setTheme(getPreferredTheme());
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      setTheme(getPreferredTheme());
    });
  };

  applyTheme();

  ui.initialize(stateManager);
  stateManager.subscribe(ui.update);

  api.initialize(stateManager);
});
