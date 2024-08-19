import { deleteSearch, createSearch } from "./api.js";
import { apiUrl } from "./config.js";
import { err, fmtDate, fmtSize, make, spinner, text } from "./helpers.js";
import { togglePoll, toggleSearch } from "./state.js";

export function initUI() {
  const searchForm = document.getElementById("searchForm");
  const searchStrInput = document.getElementById("searchStrInput");
  searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await createSearch(searchStrInput.value.trim());
  });
}

export function updateUI(stateManager) {
  const prevState = stateManager.getPrev();
  const { apiVersion, checksum, totalDocuments, isConnected, lastPoll } =
    stateManager.get();

  // Update connection status on change
  if (isConnected !== prevState?.isConnected) {
    if (isConnected) {
      console.log(`Connected to ORCA Document Query API at ${apiUrl}`);
    } else {
      err(`Error connecting to API at ${apiUrl}`);
    }

    // Swap heading and loading message
    const loadSubhead = document.getElementById("connectingSubhead");
    loadSubhead.hidden = isConnected;
    const subhead = document.getElementById("subhead");
    subhead.hidden = !isConnected;

    // Connection status
    const connStatus = document.getElementById("connection");
    connStatus.textContent = isConnected ? "Connected" : "Disconnected";
    connStatus.className = isConnected ? "connected" : "error";

    // Server-side API version
    const verStatus = document.getElementById("apiVersion");
    verStatus.textContent = apiVersion;

    // Show connection details if there's a connection, otherwise hide
    const connDetails = document.getElementById("connectionDetails");
    connDetails.hidden = !isConnected;

    // Toggle search form
    toggleSearch(isConnected);
  }

  // Client-side timestamp of last fetch
  const lastPollStatus = document.getElementById("lastPoll");
  lastPollStatus.textContent = fmtDate(lastPoll, true);
  lastPollStatus.setAttribute("datetime", lastPoll.toISOString());

  // Update search results
  updateSearchResults(stateManager);

  // Update corpus details if the checksum changes
  if (checksum !== prevState?.checksum) {
    console.log(`New checksum found, updating metadata (${checksum})`);
    const docTotal = document.getElementById("totalDocuments");
    docTotal.textContent = totalDocuments.toLocaleString();
  }
}

function updateSearchResults(stateManager) {
  const searchResults = document.getElementById("results");
  searchResults.innerHTML = "";

  const { searches } = stateManager.get();
  if (Array.isArray(searches) && searches.length > 0) {
    searches.forEach((search) => {
      searchResults.appendChild(makeSearchResult(search));
    });
  }
}

function makeSearchResult(search) {
  const {
    uid: searchUID,
    checksum,
    search_str,
    results,
    status,
    updated,
    created_at,
    megadocs,
  } = search;
  const isDone = status === "SUCCESS";

  // Create <article> container for search result
  const searchResult = make("article", { className: "result" });
  searchResult.dataset.id = searchUID;
  searchResult.dataset.checksum = checksum;

  // Add search query as heading
  const searchStr = make("h2", {
    className: "searchStr",
    textContent: search_str,
  });
  searchResult.appendChild(searchStr);

  // Add search metadata, starting with number of results. Include status.
  const searchMeta = make("ul");
  const count = make("li", { textContent: `${results} results` });
  if (!isDone) {
    count.appendChild(text(` (${status.toLowerCase()})`));
    count.appendChild(spinner());
  }
  searchMeta.appendChild(count);

  // Add timestamp
  const timestampOuter = make("li", {
    textContent: isDone ? "Finished" : "Started",
  });
  const ts = isDone ? updated_at : created_at;
  const timestamp = make("time", {
    textContent: fmtDate(ts),
    dateTime: ts,
  });
  timestampOuter.appendChild(timestamp);
  searchMeta.appendChild(timestampOuter);

  // Add megadocs
  if (Array.isArray(megadocs) && megadocs.length > 0) {
    megadocs.forEach((megadoc) => {
      searchMeta.appendChild(makeMegadoc(megadoc));
    });
  }

  // Add delete link
  if (isDone) {
    searchMeta.appendChild(makeDeleteLink(search));
  }

  searchResult.appendChild(searchMeta);
  return searchResult;
}

function makeMegadoc(megadoc) {
  const { uid: docUID, status, url } = megadoc;
  const filetype = megadoc.filetype.toLowerCase();
  const filesize = fmtSize(megadoc.filesize);

  const docMeta = make("li");

  if (status === "SUCCESS") {
    const docText = `Download ${filetype} (${filesize})`;
    const docLink = make("a", {
      className: "file",
      href: url,
      textContent: docText,
    });
    docLink.dataset.uid = docUID;
    docMeta.appendChild(docLink);
  } else {
    docMeta.className = "file";
    docMeta.dataset.uid = docUID;
    const progress = (megadoc.progress * 100.0).toFixed(2);
    const docText =
      status === "SENDING"
        ? `Finalizing ${filetype}`
        : `Creating ${filetype} (${progress}%)`;
    docMeta.appendChild(text(docText));
    docMeta.appendChild(spinner());
  }

  return docMeta;
}

function makeDeleteLink(search) {
  let wasPollEnabled = togglePoll();
  const linkMeta = make("li");

  // Create delete link-- clicking this will reveal the y/n prompt
  const delLink = make("a", {
    className: "delete",
    href: "#",
    textContent: "Delete",
  });
  delLink.addEventListener("click", async function (event) {
    event.preventDefault();

    // Track previous polling status so we can go back to it after prompt
    wasPollEnabled = togglePoll(); // Returns state w null arg
    togglePoll(false);
    delLink.hidden = true;
    delPrompt.hidden = false;
  });
  linkMeta.appendChild(delLink);

  // Create prompt--
  const delPrompt = make("b", {
    className: "prompt",
    textContent: "Delete?",
    hidden: true,
  });

  // Clicking OK will send a delete request through the API
  const okLink = make("a", {
    className: "promptOk",
    href: "#",
    textContent: "OK",
  });
  okLink.addEventListener("click", async function (event) {
    event.preventDefault();
    deleteSearch(search);
    togglePoll(wasPollEnabled);
    delLink.hidden = false;
    delPrompt.hidden = true;
  });
  delPrompt.appendChild(okLink);

  // Clicking cancel will hide the prompt again
  const cancelLink = make("a", {
    className: "promptCancel",
    href: "#",
    textContent: "Cancel",
  });
  cancelLink.addEventListener("click", async function (event) {
    event.preventDefault();
    togglePoll(wasPollEnabled);
    delLink.hidden = false;
    delPrompt.hidden = true;
  });
  delPrompt.appendChild(cancelLink);

  linkMeta.appendChild(delPrompt);
  return linkMeta;
}
