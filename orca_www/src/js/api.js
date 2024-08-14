const apiUrl = "https://api.orca.wgws.dev/";

export async function pollAPI(state) {
    const { isPollingEnabled } = state.get();
    if (!isPollingEnabled) return;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }

        const data = await response.json();

        state.update({
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
        state.update({
            isStillLoading: false,
            isConnected: false,
            lastChecked: new Date(),
            error: error.message,
        });
    }
}

export function startPolling(state, pollingInterval) {
    function pollWithInterval() {
        if (state.get().isPollingEnabled) {
            pollAPI(state);
        }
    }

    pollWithInterval();
    setInterval(pollWithInterval, pollingInterval);
}
