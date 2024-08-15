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
            isConnected: true,
            lastPoll: new Date(),
            apiVersion: data.apiVersion,
            corpusHash: data.hash,
            corpusTotal: data.total,
            searches: data.searches,
            error: null,
        });
    } catch (error) {
        console.log(`Error polling API: ${error.message}`);
    
        stateManager.update({
            isConnected: false,
            lastChecked: new Date(),
            error: error.message,
        });
    }
}

export function startPollAPI(stateManager, pollingInterval) {
    function pollWithInterval() {
        const { isPollEnabled } = stateManager.get();
        if (isPollEnabled) {
            pollAPI(stateManager);
        }
    }

    pollWithInterval();
    setInterval(pollWithInterval, pollingInterval);
}
