export function initializeUI(stateManager) {
    console.log("Initialzing UI");

    // Attach automatic polling state to checkbox. When we check/uncheck
    // the box, store that as a global flag in the state manager
    const isPollEnabledElement = document.getElementById("isPollEnabled");
    isPollEnabledElement.addEventListener("change", function () {
        const enablePolling = isPollEnabledElement.checked;
        stateManager.update({ isPollEnabled: enablePolling });
        console.log(`Automatic polling has been ${enablePolling ? "enabled" : "disabled"}`);
    });
}

export function updateUI(stateManager) {
    console.log("Updating UI");
    const oldState = stateManager.getOld();
    const { isConnected, lastPoll, corpusHash, corpusTotal, apiVersion } = stateManager.get();


    // Update connection status on change
    if (isConnected !== oldState?.isConnected) {
        console.log(`${isConnected ? "Connected to" : "disconnected from"} API`);
        
        // Client-side timestamp of last fetch
        const lastPollElement = document.getElementById("lastPoll");
        lastPollElement.setAttribute("datetime", lastPoll.toISOString());
        lastPollElement.textContent = lastPoll.toLocaleString();

        // Swap heading and loading message
        const connectingSubheadElement = document.getElementById("connectingSubhead");
        connectingSubheadElement.hidden = isConnected;
        const subheadElement = document.getElementById("subhead");
        subheadElement.hidden = !isConnected;

        // Connection status
        const connectionStatusElement = document.getElementById("connection");
        connectionStatusElement.textContent = isConnected ? "Connected" : "Disconnected";
        connectionStatusElement.className = isConnected ? "connected" : "error";

        // Server-side API version
        const apiVersionElement = document.getElementById("apiVersion");
        apiVersionElement.textContent = apiVersion;

        // Show connection details if there's a connection, otherwise hide
        const connectionDetailsElement = document.getElementById("connectionDetails");
        connectionDetailsElement.hidden = !isConnected;

        // Toggle search form
        enableSearchForm(isConnected);
    }

    // Update corpus details if the hash changes
    if (corpusHash !== oldState?.corpusHash) {
        console.log(`New hash value found: ${corpusHash}`);
        const corpusTotalElement = document.getElementById("corpusTotal");
        corpusTotalElement.textContent = corpusTotal.toLocaleString();
    }
}

function enableSearchForm(status) {
    // Toggle the search form by selecting its elements and enabling/disabling them
    const searchFormElement = document.getElementById("searchForm");
    searchFormElement.querySelectorAll("*").forEach(e => e.disabled = !status);
    console.log(`Search form has been ${status ? "enabled" : "disabled"}`);
}
