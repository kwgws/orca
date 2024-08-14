const apiUrl = "https://api.orca.wgws.dev/";

export async function pollAPI(stateManager) {
    try {
        console.log(`Polling API at ${apiUrl}`);

        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }
        const data = await response.json();

        stateManager.update({
            isStillLoading: false,
            isConnected: true,
            lastChecked: new Date(),
            version: data.version,
            hash: data.hash,
            total: data.total,
            searches: data.searches,
            error: null,
        });
    } catch (error) {
        console.log(`Error polling API: ${error.message}`);
    
        stateManager.update({
            isStillLoading: false,
            isConnected: false,
            lastChecked: new Date(),
            error: error.message,
        });
    }
}

export function startPolling(stateManager, pollingInterval) {
    function pollWithInterval() {
        const { isPollingEnabled } = stateManager.get();
        if (isPollingEnabled) {
            pollAPI(stateManager);
        }
    }

    pollWithInterval();
    setInterval(pollWithInterval, pollingInterval);
}
