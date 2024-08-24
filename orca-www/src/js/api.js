const apiUrl = "https://api.orca.wgws.dev";
const pollInterval = 5000;

export function initialize(stateManager) {
  poll(stateManager);
  setInterval(() => poll(stateManager), pollInterval);
}

export async function poll(stateManager) {
  const { isPollingEnabled } = stateManager.get();
  if (!isPollingEnabled) return;

  try {
    const response = await fetch(apiUrl);
    if (!response.ok) throw new Error(response.statusText);
    const data = await response.json();

    stateManager.update({
      isConnected: true,
      lastPolledAt: new Date(),
      apiVersion: data.apiVersion,
      corpusChecksum: data.corpus.checksum,
      corpusTotal: data.corpus.totalDocuments,
      searches: data.corpus.searches?.reverse() || [],
      error: null,
    });
  } catch (error) {
    console.error(`Error polling API: ${error.message}`);

    stateManager.update({
      isConnected: false,
      error: error.message,
    });
  }
}

export async function createSearch(searchStr, stateManager) {
  console.log(`Searching "${searchStr}"`);

  try {
    const url = `${apiUrl}/search`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ searchStr }),
    });
    if (!response.ok) throw new Error(response.statusText);
    await poll(stateManager);
  } catch (error) {
    console.error(`Error submitting search: ${error.message}`);
  }
}

export async function deleteSearch(searchUID, stateManager) {
  console.log(`Deleting search with ID ${searchUID}`);

  try {
    const url = `${apiUrl}/search/${searchUID}`;
    const response = await fetch(url, { method: "DELETE" });
    if (!response.ok) throw new Error(response.statusText);
    await poll(stateManager);
  } catch (error) {
    console.error(`Error deleting search: ${error.message}`);
  }
}
