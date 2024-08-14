export function initializeUI(stateManager) {
    console.log("Initialzing UI");

    // Attach automatic polling state to checkbox. When we check/uncheck
    // the box, store that as a global flag in the state manager
    const pollingCheckbox = document.getElementById("poll");
    pollingCheckbox.addEventListener("change", function () {
        const status = pollingCheckbox.checked;
        stateManager.update({ isPollingEnabled: status });
        console.log(`Automatic polling has been ${status ? "enabled" : "disabled"}`);
    });
}

export function updateUI(stateManager) {
    console.log("Updating UI");
    const oldState = stateManager.getOld();
    const { isStillLoading, isConnected, lastChecked, hash, total, version } = stateManager.get();

    // Once we get our first request we can get rid of the loading message
    if (isStillLoading !== oldState?.isStillLoading) {
        console.log("Done loading");
        const loadingSubhead = document.getElementById("loadingSubhead");
        loadingSubhead.hidden = true;
        const subhead = document.getElementById("subhead");
        subhead.hidden = false;
    }

    // Update connection status on change
    if (isConnected !== oldState?.isConnected) {
        console.log(`${isConnected ? "Connected to" : "disconnected from"} API`);

        // Client-side timestamp of last fetch
        const lastUpdated = document.getElementById("lastUpdated");
        lastUpdated.setAttribute("datetime", lastChecked.toISOString());
        lastUpdated.textContent = lastChecked.toLocaleString();

        // Connection status
        const connectionStatus = document.getElementById("connection");
        connectionStatus.textContent = isConnected ? "Connected" : "Disconnected";
        connectionStatus.className = isConnected ? "connected" : "error";

        // Server-side API version
        const apiVersion = document.getElementById("version");
        apiVersion.textContent = version;

        // Show connection details if there's a connection, otherwise hide
        const connectionDetails = document.getElementById("connectionDetails");
        connectionDetails.hidden = !isConnected;

        // Toggle search form
        enableSearchForm(isConnected);
    }

    // Update corpus details if the hash change
    if (hash !== oldState?.hash) {
        console.log(`New hash value found: ${hash}`);
        const docTotal = document.getElementById("docTotal");
        docTotal.textContent = total.toLocaleString();
    }
}

function enableSearchForm(status) {
    // Toggle the search form by selecting its elements and enabling/disabling them
    const searchForm = document.getElementById("searchForm");
    searchForm.querySelectorAll("*").forEach(e => e.disabled = !status);
    console.log(`Search form has been ${status ? "enabled" : "disabled"}`);
}
