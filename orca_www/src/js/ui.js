import { fmtDate, fmtSize, make, spinner, text } from "./helpers.js";


export function initializeUI(stateManager) {
    console.log("Initialzing UI");

    // Attach automatic polling state to checkbox. When we check/uncheck
    // the box, store that as a global flag in the state manager
    const pollCheckbox = document.getElementById("isPollEnabled");
    pollCheckbox.addEventListener("change", function () {
        const poll = pollCheckbox.checked;
        stateManager.update({ isPollEnabled: poll });
        console.log(`Polling has been ${poll ? "enabled" : "disabled"}`);
    });
}


export function updateUI(stateManager) {
    console.log("Updating UI");
    const prevState = stateManager.getPrev();
    const {
        apiVersion, corpusHash, corpusTotal, isConnected, lastPoll
    } = stateManager.get();

    // Update connection status on change
    if (isConnected !== prevState?.isConnected) {
        console.log(`${isConnected ? "Connected to" : "disconnected from"} API`);

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
        enableSearchForm(isConnected);
    }

    // Client-side timestamp of last fetch
    const lastPollStatus = document.getElementById("lastPoll");
    lastPollStatus.textContent = fmtDate(lastPoll, true);
    lastPollStatus.setAttribute("datetime", lastPoll.toISOString());

    // Update search results
    updateSearchResults(stateManager);

    // Update corpus details if the hash changes
    if (corpusHash !== prevState?.corpusHash) {
        console.log(`New hash value found: ${corpusHash}`);
        const docTotal = document.getElementById("corpusTotal");
        docTotal.textContent = corpusTotal.toLocaleString();
    }
}


function enableSearchForm(status) {
    // Toggle the form by selecting its elements and enabling/disabling them
    const searchForm = document.getElementById("searchForm");
    searchForm.querySelectorAll("*").forEach((e) => e.disabled = !status);
    console.log(`Search form has been ${status ? "enabled" : "disabled"}`);
}


function updateSearchResults(stateManager) {
    const searchResults = document.getElementById("results");
    searchResults.innerHTML = "";

    const { searches } = stateManager.get();
    searches.forEach((search) => {
        searchResults.appendChild(makeSearchResult(search));
    });
}


function makeSearchResult(search) {
    const {
        id: searchId, hash, search_str, results, status, updated, created, megadocs
    } = search;
    const isDone = status === "SUCCESS";

    // Create <article> container for search result
    const searchResult = make("article", { className: "result" });
    searchResult.dataset.id = searchId;
    searchResult.dataset.hash = hash;

    // Add search query as heading
    const searchStr = make("h2", {
        className: "searchStr", textContent: search_str
    });
    searchResult.appendChild(searchStr);

    // Add search metadata, starting with number of results. Include status.
    const searchMeta = make("ul");
    const count = make("li", { textContent: `${results} results` });
    if (!isDone) {
        count.appendChild(text(` (${status.toLowerCase()}`));
        count.appendChild(spinner());
    }
    searchMeta.appendChild(count);

    // Add timestamp
    const timestampOuter = make("li", {
        textContent: isDone ? "Finished" : "Started"
    });
    const ts = isDone ? updated : created;
    const timestamp = make("time", {
        textContent: fmtDate(ts), dateTime: ts,
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
    if (isDone) { searchMeta.appendChild(makeDeleteLink(searchId)); }

    searchResult.appendChild(searchMeta);
    return searchResult;
}


function makeMegadoc(megadoc) {
    const { id: docId, status, url } = megadoc;
    const filetype = megadoc.filetype.toLowerCase();
    const filesize = fmtSize(megadoc.filesize);
    const docMeta = make("li");

    if (status === "SUCCESS") {
        const docText = `Download ${filetype} (${filesize})`
        const docLink = make("a", { className: "file", href: url, textContent: docText });
        docLink.dataset.id = docId;
        docMeta.appendChild(docLink);

    } else {
        docMeta.className = "file";
        docMeta.dataset.id = docId;
        const docText = status === (
            "SENDING" ? `Finalizing ${filetype}` : `Creating ${filetype} (${progress})`
        );
        docMeta.appendChild(text(docText));
        docMeta.appendChild(spinner());
    }

    return docMeta;
}


function makeDeleteLink(searchId) {
    const linkMeta = make("li");

    // Delete link--this is the first layer. Clicking this reveals the prompt.
    const delLink = make("a", { className: "delete", href: "#", textContent: "Delete" });
    linkMeta.appendChild(delLink);

    // Delete prompt--this is the second layer. Clicking OK deletes the search.
    const delPrompt = make("b", { className: "prompt", textContent: "Delete?", hidden: true });

    const okLink = make("a", { className: "promptOk", href: "#", textContent: "Ok" });
    okLink.dataset.id = searchId;
    delPrompt.appendChild(okLink);

    const cancelLink = make("a", { className: "promptCancel", href: "#", textContent: "Cancel" });
    delPrompt.appendChild(cancelLink);

    linkMeta.appendChild(delPrompt);
    return linkMeta;
}
