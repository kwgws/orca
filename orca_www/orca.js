/////////////
// orca.js //
/////////////

const apiUrl = "https://api.orca.wgws.dev";
const pollingDelay = 5000; /* 1000 = 1 second. */

// ---- INITIALIZATION ----
document.addEventListener("DOMContentLoaded", async () => {
  console.log("Starting ORCA Client...");

  enableForm(false);
  await pollApi();
  setInterval(async () => {
    if (enablePolling() == true) await pollApi();
  }, pollingDelay);

  const searchForm = document.getElementById("searchForm");
  searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await submitSearch();
  });

  console.log("Ok");
});

// ---- API POLLING; LIST UPDATES ----
async function pollApi() {
  displayError(false); /* Clear out error message if any. */

  try {
    const response = await fetch(apiUrl);
    if (!response.ok) throw new Error("Reconnecting...");

    const data = await response.json();
    updateStatus(data);
    updateSearchList(data.searches);

  } catch (error) {
    displayError(error.message);
  }
}

function updateStatus(data) {
  const docTotal = document.getElementById("docTotal");
  const newDocTotal = data.total.toLocaleString();
  if (docTotal.textContent !== newDocTotal) docTotal.textContent = newDocTotal;

  const apiConnectionStatus = document.getElementById("apiConnectionStatus");
  apiConnectionStatus.textContent = "🛰️";

  const apiVersion = document.getElementById("apiVersion");
  if (apiVersion.textContent !== data.version) apiVersion.textContent = data.version;
}

function updateSearchList(searches) {
  const searchList = document.getElementById("searchList");
  searchList.innerHTML = "";

  const fragment = document.createDocumentFragment();
  for (let i = searches.length - 1; i >= 0; i--) {
    searchElement = createSearchElement(searches[i])
    if (i < searches.length - 1) searchElement.style.marginTop = "1rem";
    fragment.appendChild(searchElement);
  };
  searchList.appendChild(fragment)

  enableForm(true);
}

function createSearchElement(search) {
  const searchElement = createElement("dt", { "data-id": search.id });
  searchElement.appendChild(createElement("span", { className: "searchStr", textContent: search.search_str }));
  searchElement.appendChild(createText(" "));
  searchElement.appendChild(createElement("span", { className: "searchResults", textContent: `${search.results.toLocaleString()} results` }));
  searchElement.appendChild(createText(" "));
  if (search.status !== "SUCCESS") {
    searchElement.appendChild(createSpinner());

    // Add delete link.
  } else if ((() => {
    let isDeleteOk = search.status !== "STARTED";
    if (isDeleteOk && Array.isArray(search.megadocs)) {
      if (search.megadocs.length == 0) {
        isDeleteOk = false;
      } else {
        for (let i = 0; i < search.megadocs.length; i++) {
          if (search.megadocs[i].status !== "SUCCESS") {
            isDeleteOk = false;
            break;
          }
        }
      }
    }
    return isDeleteOk;
  })()) {
    const deleteElement = createElement("span", { className: "searchDeleteLink" });
    const deleteLink = createElement("a", { href: "#", textContent: "delete" });
    deleteLink.addEventListener("click", (event) => {
      event.preventDefault();
      deleteSearch(search.id);
    });
    deleteElement.appendChild(deleteLink);
    searchElement.appendChild(deleteElement);
  }

  // Add timestamp.
  const statusElement = createElement("dd");
  if (search.status !== "SUCCESS") {
    statusElement.appendChild(createText("Started "));
    statusElement.appendChild(createElement("time", { className: "searchTimestamp", textContent: formatDate(search.created) }));
  } else {
    statusElement.appendChild(createText("Finished "));
    statusElement.appendChild(createElement("time", { className: "searchTimestamp", textContent: formatDate(search.updated) }));
  }
  searchElement.appendChild(statusElement);

  // Add list of megadocs.
  if (Array.isArray(search.megadocs)) {
    if (search.megadocs.length === 0 && search.status === "SUCCESS") {
      const megadocElement = createElement("dd", { className: "downloadLink" });
      megadocElement.textContent = "Starting... "
      megadocElement.appendChild(createSpinner());
      searchElement.appendChild(megadocElement);
    } else {
      search.megadocs.forEach(megadoc => {
        const megadocElement = createElement("dd", { className: "downloadLink" });
        if (megadoc.status === "SENDING") {
          megadocElement.textContent = `${megadoc.filetype.toUpperCase()} Uploading... `;
          megadocElement.appendChild(createSpinner());
        } else if (megadoc.status !== "SUCCESS") {
          const progress = (megadoc.progress / search.results * 100.0).toFixed(1);
          megadocElement.textContent = `${megadoc.filetype.toUpperCase()} `;
          megadocElement.appendChild(createSpinner());
          megadocElement.appendChild(createText(`  ${progress}%`));
        } else {
          megadocElement.appendChild(createElement("a", { href: megadoc.url, textContent: `${megadoc.filetype.toUpperCase()} download` }));
          megadocElement.appendChild(createText(` (${formatSize(megadoc.filesize)})`));
        }
        searchElement.appendChild(megadocElement);
      });
    }
  }

  return searchElement;
}

// ---- SUBMIT NEW QUERY ----
async function submitSearch() {
  const searchInput = document.getElementById("searchInput");
  const search_str = searchInput.value.trim();
  searchInput.value = "";
  enableForm(false);

  try {
    console.log(`Submitting: ${JSON.stringify({ search_str })} ...`);

    const response = await fetch(`${apiUrl}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ search_str })
    });
    if (!response.ok) {
      throw new Error("Could not submit search");
    }

    await pollApi();
    enableForm(true);

  } catch (error) {
    displayError(error.message);
  }
}

// --- DELETE QUERY ---
function deleteSearch(searchId) {
  const deleteSpan = document.querySelector(`[data-id="${searchId}"] .searchDeleteLink`);
  const deleteLink = deleteSpan.querySelector("a");
  deleteLink.remove();

  const prevEnablePolling = enablePolling();
  enablePolling(false);

  // Create confirmation prompt.
  const deletePrompt = createElement("span", { className: "searchDeletePrompt", textContent: "delete? " });
  deletePrompt.appendChild(createElement("a", { className: "confirmLink", href: "#", textContent: "OK" }));
  deletePrompt.appendChild(createText(" "));
  deletePrompt.appendChild(createElement("a", { className: "cancelLink", href: "#", textContent: "Cancel" }));
  deleteSpan.appendChild(deletePrompt);

  // Ok to delete; pass request to API.
  deletePrompt.querySelector(".confirmLink").addEventListener("click", async function (event) {
    event.preventDefault();
    console.log(`Deleting ...`);
    try {
      const response = await fetch(`${apiUrl}/search/${searchId}`, {
        method: "DELETE"
      });
      if (!response.ok) {
        throw new Error("Could not delete search");
      }
      await pollApi();
    } catch (error) {
      displayError(error.message);
    }
    deletePrompt.remove();
    deleteSpan.appendChild(deleteLink);
    enablePolling(prevEnablePolling);
  });

  // Cancel, restore link.
  deletePrompt.querySelector(".cancelLink").addEventListener("click", function (event) {
    event.preventDefault();
    deletePrompt.remove();
    deleteSpan.appendChild(deleteLink);
    enablePolling(prevEnablePolling);
  });
}

// ---- DOM HELPER FUNCTIONS ----
function createElement(tag, attributes = {}) {
  const element = document.createElement(tag);
  Object.keys(attributes).forEach(key => {
    if (key === "className") element.className = attributes[key];
    else if (key in element) element[key] = attributes[key];
    else element.setAttribute(key, attributes[key]);
  });
  return element;
}

function createText(textContent) {
  return document.createTextNode(textContent);
}

function createSpinner() {
  return createElement("span", { className: "spinner" })
}

function displayError(message) {
  const errorMessage = document.getElementById("errorMessage");

  // If message passed is false, clear the display and return.
  if (message === false) {
    errorMessage.textContent = "";
    errorMessage.className = "";

    // Otherwise print an error.
  } else {
    console.error(message);
    errorMessage.textContent = message;
    errorMessage.className = "error";

    enableForm(false);
    //enablePolling(false);
  }
}

// ---- STATE HELPER FUNCTIONS ----
function enablePolling(status) {
  const pollCheckbox = document.getElementById("pollCheckbox");
  if (typeof status === "undefined") return pollCheckbox.checked;
  pollCheckbox.checked = status;
}

function enableForm(status) {
  const searchForm = document.getElementById("searchForm");
  searchForm.querySelectorAll("*").forEach(e => e.disabled = !status);

  const submitButton = document.getElementById("submitButton");
  if (!status) {
    // Replace submit button with spinner
    if (!submitButton.classList.contains("hidden")) {
      submitButton.classList.add("hidden");
      const spinner = createSpinner();
      spinner.id = "submitSpinner";
      submitButton.parentElement.appendChild(spinner);
    }
  } else {
    // Restore submit button and remove spinner
    submitButton.classList.remove("hidden");
    const spinner = document.getElementById("submitSpinner");
    if (spinner) spinner.remove();
  }
}

// ---- MISCELLANIOUS HELPER FUNCTIONS ----
async function checkUrl(url) {
  const response = await fetch(url, { method: "HEAD" });
  if (response.ok) { return true; }
  return false;
}

function formatSize(bytes) {
  const units = ["", "k", "m", "g", "t"];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024;
    i++;
  }
  return `${bytes.toFixed(1)} ${units[i]}b`;
}

function formatDate(isoDate) {
  return new Date(isoDate).toLocaleString('en-US', {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true
  });
}
