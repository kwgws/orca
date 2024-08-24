const apiUrl = "https://api.orca.wgws.dev";
const minInterval = 1000; // 1 sec
const maxInterval = 60000; // 1 min
let pollTimer = null;

export function initialize(stateManager) {
  poll(stateManager, minInterval);
}

export async function poll(stateManager, currentInterval) {
  const { isPollingEnabled, dataChecksum } = stateManager.get();
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
      error: null,
    });

    // Reset interval on successful poll with changes
    const nextInterval =
      dataChecksum !== data.checksum
        ? minInterval
        : Math.min(currentInterval * 2, maxInterval);

    pollTimer = setTimeout(
      () => poll(stateManager, nextInterval),
      nextInterval
    );
  } catch (error) {
    console.error(`Error polling API: ${error.message}`);

    stateManager.update({
      isConnected: false,
      error: error.message,
    });

    // Exponential backoff on error
    const nextInterval = Math.min(currentInterval * 2, maxInterval);
    pollTimer = setTimeout(
      () => poll(stateManager, nextInterval),
      nextInterval
    );
  }
}

export async function createSearch(searchStr, stateManager) {
  console.log(`Searching "${searchStr}" 🔦`);

  try {
    const url = `${apiUrl}/search`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ searchStr }),
    });
    if (!response.ok) throw new Error(response.statusText);

    clearTimeout(pollTimer);
    await poll(stateManager, minInterval);
  } catch (error) {
    console.error(`Error submitting search: ${error.message}`);
  }
}

export async function deleteSearch(searchUID, stateManager) {
  console.log(`Deleting search with ID ${searchUID} 🗑️`);

  try {
    const url = `${apiUrl}/search/${searchUID}`;
    const response = await fetch(url, { method: "DELETE" });
    if (!response.ok) throw new Error(response.statusText);

    clearTimeout(pollTimer);
    await poll(stateManager, minInterval);
  } catch (error) {
    console.error(`Error deleting search: ${error.message}`);
  }
}
