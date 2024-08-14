let wasStillLoading = true;
let wasConnected = false;
let oldHash = null;

export function initializeUI(state) {
    const pollingCheckbox = document.getElementById("poll");
    pollingCheckbox.addEventListener("change", () => {
        state.update({ isPollingEnabled: pollingCheckbox.checked });
    });
}

export function updateUI(state) {
    const { isPollingEnabled, isStillLoading, isConnected, lastChecked, total, version, hash } = state;

    const pollingCheckbox = document.getElementById("poll");
    pollingCheckbox.checked = isPollingEnabled;

    if(!isStillLoading) {
        if (wasStillLoading) {
            enableSubheading(true);
            wasStillLoading = false;
        }
        if (isConnected) {
            if (!wasConnected) {
                enableSearchForm(true);
                setConnectionStatus(true);
                wasConnected = true;
            }
            
            if (oldHash != hash) {
                setConnectionDetails(total, version, lastChecked, hash);
                oldHash = hash;
            }
        }
    }
}

function enableSubheading(isEnabled) {
    const loadingSubhead = document.getElementById("loadingSubhead");
    loadingSubhead.hidden = isEnabled;
    const subhead = document.getElementById("subhead");
    subhead.hidden = !isEnabled;
}

function enableSearchForm(isEnabled) {
    const searchForm = document.getElementById("searchForm");
    searchForm.querySelectorAll("*").forEach(e => e.disabled = !isEnabled);
}

function setConnectionStatus(isConnected) {
    const connectionStatus = document.getElementById("connection");
    connectionStatus.textContent = isConnected ? "Connected" : "Disconnected";
    connectionStatus.className = isConnected ? "connected" : "error";

    const connectionDetails = document.getElementById("connectionDetails");
    connectionDetails.hidden = !isConnected;
}

function setConnectionDetails(total, apiVersion, lastChecked, hashValue) {
    const docTotal = document.getElementById("docTotal");
    docTotal.textContent = total.toLocaleString();

    const version = document.getElementById("version");
    version.textContent = apiVersion;

    const lastUpdated = document.getElementById("lastUpdated");
    lastUpdated.setAttribute("datetime", lastChecked.toISOString());
    lastUpdated.textContent = lastChecked.toLocaleString();

    const hash = document.getElementById("hash");
    hash.textContent = hashValue;
}
