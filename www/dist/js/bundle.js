/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ "./www/src/js/api.js":
/*!***************************!*\
  !*** ./www/src/js/api.js ***!
  \***************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   createSearch: () => (/* binding */ createSearch),
/* harmony export */   deleteSearch: () => (/* binding */ deleteSearch),
/* harmony export */   initialize: () => (/* binding */ initialize),
/* harmony export */   poll: () => (/* binding */ poll)
/* harmony export */ });


const apiUrl = "https://api.orca.wgws.dev";
const minInterval = 1500; // 1.5 secs
const maxInterval = 768000; // ~12.5 mins
let pollTimer = null;
function initialize(stateManager) {
  poll(stateManager, minInterval);
}
async function poll(stateManager, currentInterval) {
  const {
    isPollingEnabled,
    dataChecksum
  } = stateManager.get();
  if (!isPollingEnabled) return;
  try {
    const response = await fetch(apiUrl);
    if (!response.ok) throw new Error(response.statusText);
    const data = await response.json();
    stateManager.update({
      isConnected: true,
      lastPolledAt: new Date(),
      apiVersion: data.apiVersion,
      dataChecksum: data.checksum,
      corpusChecksum: data.corpus.checksum,
      corpusTotal: data.corpus.totalDocuments,
      searches: data.corpus.searches?.reverse() || [],
      error: null
    });

    // Reset interval on successful poll with changes
    const nextInterval = dataChecksum !== data.checksum ? minInterval : Math.min(currentInterval * 2, maxInterval);
    pollTimer = setTimeout(() => poll(stateManager, nextInterval), nextInterval);
  } catch (error) {
    console.error(`Error polling API: ${error.message}`);
    stateManager.update({
      isConnected: false,
      error: error.message
    });

    // Exponential backoff on error
    const nextInterval = Math.min(currentInterval * 2, maxInterval);
    pollTimer = setTimeout(() => poll(stateManager, nextInterval), nextInterval);
  }
}
async function createSearch(searchStr, stateManager) {
  console.log(`Searching "${searchStr}" 🔦`);
  try {
    const url = `${apiUrl}/search`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        searchStr
      })
    });
    if (!response.ok) throw new Error(response.statusText);
    clearTimeout(pollTimer);
    await poll(stateManager, minInterval);
  } catch (error) {
    console.error(`Error submitting search: ${error.message}`);
  }
}
async function deleteSearch(searchUID, stateManager) {
  console.log(`Deleting search with ID ${searchUID} 🗑️`);
  try {
    const url = `${apiUrl}/search/${searchUID}`;
    const response = await fetch(url, {
      method: "DELETE"
    });
    if (!response.ok) throw new Error(response.statusText);
    clearTimeout(pollTimer);
    await poll(stateManager, minInterval);
  } catch (error) {
    console.error(`Error deleting search: ${error.message}`);
  }
}

/***/ }),

/***/ "./www/src/js/state.js":
/*!*****************************!*\
  !*** ./www/src/js/state.js ***!
  \*****************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   StateManager: () => (/* binding */ StateManager)
/* harmony export */ });


class StateManager {
  constructor() {
    let initialState = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
    this.state = initialState;
    this.prevState = null;
    this.listeners = [];
  }
  update(state) {
    this.prevState = {
      ...this.state
    };
    this.state = {
      ...this.state,
      ...state
    };
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
  getPrev() {
    return this.prevState;
  }
}

/***/ }),

/***/ "./www/src/js/ui.js":
/*!**************************!*\
  !*** ./www/src/js/ui.js ***!
  \**************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   initialize: () => (/* binding */ initialize),
/* harmony export */   update: () => (/* binding */ update)
/* harmony export */ });
/* harmony import */ var _api_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./api.js */ "./www/src/js/api.js");




/**********************
 * DOM state managers *
 **********************/

function initialize(stateManager) {
  // Add event listener to search form
  dom.searchForm.addEventListener("submit", async event => {
    event.preventDefault();
    const searchStr = dom.searchInput.value;
    dom.searchInput.value = "";
    updateElement(dom.searchSubmit, {
      disabled: true
    });
    await _api_js__WEBPACK_IMPORTED_MODULE_0__.createSearch(searchStr, stateManager);
    updateElement(dom.searchSubmit, {
      disabled: false
    });
  });

  // Add event listener to polling checkbox
  dom.optionsEnablePoll.addEventListener("change", async event => {
    event.preventDefault();
    stateManager.update({
      isPollingEnabled: dom.optionsEnablePoll.checked
    });
  });

  // Add event listener(s) to search list
  dom.searchList.addEventListener("click", async event => {
    const e = event.target;
    if (e.classList.contains(cl.deleteToggle) || e.classList.contains(cl.deleteOk) || e.classList.contains(cl.deleteCancel)) {
      event.preventDefault();
      const searchElement = event.target.closest(`.${cl.searchResult}`);
      const toggle = searchElement.querySelector(`.${cl.deleteToggle}`);
      const prompt = searchElement.querySelector(`.${cl.deletePrompt}`);
      if (e.classList.contains(cl.deleteToggle)) {
        toggleVisible(toggle, false);
        toggleVisible(prompt, true);
        stateManager.update({
          isPollingEnabled: false
        });
      } else {
        toggleVisible(prompt, false);
        toggleVisible(toggle, true);
        stateManager.update({
          isPollingEnabled: true
        });
        if (e.classList.contains(cl.deleteOk)) {
          const searchId = searchElement.dataset.id;
          await _api_js__WEBPACK_IMPORTED_MODULE_0__.deleteSearch(searchId, stateManager);
        }
      }
    }
  });
}
function update(stateManager) {
  const {
    apiVersion,
    corpusChecksum,
    corpusTotal,
    isConnected,
    lastPolledAt,
    searches
  } = stateManager.get();
  const prevState = stateManager.getPrev();
  if (isConnected !== prevState?.isConnected) {
    toggleIsConnected(isConnected);
    if (!isConnected) return;
  }
  if (apiVersion !== prevState?.apiVersion) {
    updateElement(dom.apiVersion, {
      textContent: apiVersion
    });
  }
  if (corpusChecksum !== prevState?.corpusChecksum) {
    updateElement(dom.corpusChecksum, {
      textContent: corpusChecksum
    });
  }
  if (corpusTotal !== prevState?.corpusTotal) {
    const localeTotal = corpusTotal.toLocaleString();
    updateElement(dom.corpusTotal, {
      textContent: localeTotal
    });
  }
  if (lastPolledAt !== prevState?.lastPolledAt) {
    updateTimeElement(dom.lastPolledAt, lastPolledAt);
  }
  if (searches !== prevState?.searches) {
    updateSearchResults(stateManager);
  }
}
function toggleVisible(e, isVisible) {
  if (isVisible) {
    e.classList.remove(cl.hidden);
  } else {
    e.classList.add(cl.hidden);
  }
}
function toggleIsConnected(isConnected) {
  dom.onConnect.forEach(e => toggleVisible(e, isConnected));
  dom.onDisconnect.forEach(e => toggleVisible(e, !isConnected));
  updateElement(dom.searchSubmit, {
    disabled: !isConnected
  });
  console.log(`UI has been ${isConnected ? "unhidden" : "hidden"}`);
}

/**********************************
 * Basic DOM manipulation methods *
 **********************************/

function createElement(tag) {
  let attributes = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
  return updateElement(document.createElement(tag), attributes);
}
function createSpinner() {
  return createElement("span", {
    className: cl.spinner
  });
}
function createText(content) {
  return document.createTextNode(content);
}
function createTimeElement(timestamp) {
  return updateTimeElement(createElement("time"), timestamp);
}
function updateElement(e) {
  let attributes = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
  // Loop through the attributes and update them. Some need special handling.
  for (const [attr, value] of Object.entries(attributes)) {
    if (attr in e) e[attr] = value;else e.setAttribute(attr, value);
  }
  return e;
}
function updateTimeElement(e, timestamp) {
  // Save original timestamp as the element's `datetime` property
  updateElement(e, {
    datetime: timestamp
  });

  // Convert to readable string and save as text content
  const localeTimestampOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true
  };
  const localeTimestamp = new Date(timestamp).toLocaleString("en-US", localeTimestampOptions);
  return updateElement(e, {
    textContent: localeTimestamp
  });
}

/*************************
 * Search result methods *
 *************************/

function createSearchElement(search) {
  const {
    uid: searchUID,
    checksum,
    megadocs
  } = search;
  const searchContainer = createElement("article", {
    className: cl.search
  });
  const searchElement = createElement("div", {
    className: cl.searchResult
  });
  searchElement.dataset.id = searchUID;
  searchElement.dataset["checksum"] = checksum;

  // Add search query as heading
  searchElement.appendChild(createSearchStrElement(search));

  // Add search metadata -
  const searchMeta = createElement("ul", {
    className: cl.searchMeta
  });
  searchElement.appendChild(searchMeta);

  // - Result count
  searchMeta.appendChild(createSearchCountElement(search));

  // - Timestamp
  searchMeta.appendChild(createSearchTimestampElement(search));

  // - Megadocs
  if (Array.isArray(search.megadocs) && search.megadocs.length > 0) {
    megadocs.forEach(megadoc => {
      searchMeta.appendChild(createMegadocElement(megadoc));
    });
  }

  // - Delete link
  if (getSearchStatus(search) === "SUCCESS") {
    searchElement.appendChild(createDeleteElement());
  }
  searchContainer.appendChild(searchElement);
  return searchContainer;
}
function createSearchStrElement(search) {
  const {
    searchStr
  } = search;
  return createElement("h2", {
    className: cl.searchStr,
    textContent: searchStr
  });
}
function createSearchCountElement(search) {
  const {
    results,
    status
  } = search;
  const searchCount = createElement("li", {
    className: cl.searchCount,
    textContent: `${results.toLocaleString()} results`
  });
  if (status === "STARTED") {
    searchCount.appendChild(createSpinner());
  }
  return searchCount;
}
function createSearchTimestampElement(search) {
  const {
    createdAt,
    updatedAt
  } = search;
  const status = getSearchStatus(search);
  const searchTimestamp = createElement("li", {
    className: cl.searchTimestamp,
    textContent: status === "SUCCESS" ? "Finished " : "Started "
  });
  searchTimestamp.appendChild(createTimeElement(status === "SUCCESS" ? updatedAt : createdAt));
  return searchTimestamp;
}
function createMegadocElement(megadoc) {
  const {
    uid: docUID,
    progress = 0.0,
    status,
    url
  } = megadoc;
  const filetype = megadoc.filetype.toLowerCase();
  const filesize = formatFilesize(megadoc.filesize);
  const docMeta = createElement("li");
  docMeta.dataset["id"] = docUID;
  if (status === "SUCCESS") {
    // Megadoc complete, create download link
    docMeta.className = cl.megadocDownload;
    const docLink = createElement("a", {
      href: url,
      textContent: "💾 "
    });
    docLink.appendChild(createElement("i", {
      textContent: `Download ${filetype} (${filesize})`
    }));
    docMeta.appendChild(docLink);
  } else if (status === "SENDING") {
    // Megadoc uploading, display status
    docMeta.className = cl.megadocSending;
    docMeta.appendChild(createText(`☁️ Uploading ${filetype} (${filesize})`));
    docMeta.appendChild(createSpinner());
  } else {
    // Megadoc creating, display status
    docMeta.className = cl.megadocStarted;
    docMeta.appendChild(createText(`📝 Creating ${filetype} (${(progress * 100.0).toFixed(2)}%)`));
    docMeta.appendChild(createSpinner());
  }
  return docMeta;
}
function createDeleteElement() {
  const delLinkMeta = createElement("div", {
    className: cl.delete
  });

  // Create delete link; this will reveal the confirmation prompt
  const delToggleLink = createElement("button", {
    className: cl.deleteToggle,
    textContent: "Delete"
  });
  delLinkMeta.appendChild(delToggleLink);

  // Create prompt --
  const delPrompt = createElement("div", {
    className: cl.deletePrompt,
    textContent: "Are you sure? "
  });
  toggleVisible(delPrompt, false);

  // - OK link
  const okLink = createElement("button", {
    className: cl.deleteOk,
    textContent: "OK"
  });
  delPrompt.appendChild(okLink);
  delPrompt.appendChild(createText(" "));

  // - Cancel link
  const cancelLink = createElement("button", {
    className: cl.deleteCancel,
    textContent: "Cancel"
  });
  delPrompt.appendChild(cancelLink);
  delLinkMeta.appendChild(delPrompt);
  return delLinkMeta;
}
function updateSearchResults(stateManager) {
  const {
    searches = []
  } = stateManager.get();
  if (!Array.isArray(searches) || searches.length === 0) return;
  dom.searchList.innerHTML = "";
  searches.forEach(search => {
    dom.searchList.appendChild(createSearchElement(search, stateManager));
  });
}

/***********
 * Helpers *
 ***********/

const cl = {
  // Generic classes
  spinner: "spinner",
  hidden: "hidden",
  onResult: "on-result",
  onConnect: "on-connect",
  onDisconnect: "on-disconnect",
  // Status classes
  apiVersion: "footer__api-version",
  corpusChecksum: "footer__checksum-value",
  corpusTotal: "header__corpus-total",
  lastPolledAt: "footer__last-polled-timestamp",
  // Forms and controls
  searchForm: "header__search",
  searchInput: "header__search-input",
  searchSubmit: "header__search-submit",
  optionsForm: "footer__options",
  optionsEnablePoll: "footer__options-enable-polling",
  // Dynamic content classes
  searchList: "main__row",
  search: "main__search",
  searchResult: "main__search-result",
  searchStr: "main__search-result-str",
  searchMeta: "main__search-result-meta",
  searchCount: "main__search-result-meta-count",
  searchTimestamp: "main__search-result-meta-timestamp",
  delete: "main__search-result-meta-delete",
  deleteToggle: "main__search-result-meta-delete-link",
  deletePrompt: "main__search-result-meta-delete-prompt",
  deleteOk: "main__search-result-meta-delete-prompt-ok",
  deleteCancel: "main__search-result-meta-delete-prompt-cancel",
  megadocStarted: "main__search-result-meta-file-started",
  megadocSending: "main__search-result-meta-file-sending",
  megadocDownload: "main__search-result-meta-file-download"
};
const dom = {
  // Generic elements
  onResult: document.querySelectorAll(`.${cl.onResult}`),
  onConnect: document.querySelectorAll(`.${cl.onConnect}`),
  onDisconnect: document.querySelectorAll(`.${cl.onDisconnect}`),
  // Status elements
  apiVersion: document.querySelector(`.${cl.apiVersion}`),
  corpusChecksum: document.querySelector(`.${cl.corpusChecksum}`),
  corpusTotal: document.querySelector(`.${cl.corpusTotal}`),
  lastPolledAt: document.querySelector(`.${cl.lastPolledAt}`),
  // Forms and controls
  searchForm: document.querySelector(`.${cl.searchForm}`),
  searchInput: document.querySelector(`.${cl.searchInput}`),
  searchSubmit: document.querySelector(`.${cl.searchSubmit}`),
  optionsForm: document.querySelector(`.${cl.optionsForm}`),
  optionsEnablePoll: document.querySelector(`.${cl.optionsEnablePoll}`),
  // Search result elements
  searchList: document.querySelector(`.${cl.searchList}`)
};
function formatFilesize(bytes) {
  const units = ["", "k", "m", "g", "t"];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024;
    i++;
  }
  return `${bytes.toFixed(1)} ${units[i]}b`;
}
function getSearchStatus(search) {
  const {
    megadocs,
    status
  } = search;
  if (Array.isArray(megadocs) && megadocs.length > 0) {
    for (let i = 0; i < megadocs.length; i++) {
      if (megadocs[i].status === "SENDING" || megadocs[i].status === "STARTED") {
        return megadocs[i].status;
      }
    }
  }
  return status;
}

/***/ }),

/***/ "./www/src/scss/main.scss":
/*!********************************!*\
  !*** ./www/src/scss/main.scss ***!
  \********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
// extracted by mini-css-extract-plugin


/***/ })

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/define property getters */
/******/ 	(() => {
/******/ 		// define getter functions for harmony exports
/******/ 		__webpack_require__.d = (exports, definition) => {
/******/ 			for(var key in definition) {
/******/ 				if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	(() => {
/******/ 		// define __esModule on exports
/******/ 		__webpack_require__.r = (exports) => {
/******/ 			if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 			}
/******/ 			Object.defineProperty(exports, '__esModule', { value: true });
/******/ 		};
/******/ 	})();
/******/ 	
/************************************************************************/
var __webpack_exports__ = {};
/*!****************************!*\
  !*** ./www/src/js/main.js ***!
  \****************************/
__webpack_require__.r(__webpack_exports__);
/* harmony import */ var _scss_main_scss__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../scss/main.scss */ "./www/src/scss/main.scss");
/* harmony import */ var _state_js__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./state.js */ "./www/src/js/state.js");
/* harmony import */ var _api_js__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./api.js */ "./www/src/js/api.js");
/* harmony import */ var _ui_js__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./ui.js */ "./www/src/js/ui.js");






const stateManager = new _state_js__WEBPACK_IMPORTED_MODULE_1__.StateManager({
  isConnected: false,
  isPollingEnabled: true,
  lastPolledAt: null,
  error: null
});
document.addEventListener("DOMContentLoaded", async function () {
  // Set theme based on system preference
  const setTheme = theme => {
    document.documentElement.style.transition =
    // Add a slight transition effect
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
  _ui_js__WEBPACK_IMPORTED_MODULE_3__.initialize(stateManager);
  stateManager.subscribe(_ui_js__WEBPACK_IMPORTED_MODULE_3__.update);
  _api_js__WEBPACK_IMPORTED_MODULE_2__.initialize(stateManager);
});
/******/ })()
;
//# sourceMappingURL=bundle.js.map