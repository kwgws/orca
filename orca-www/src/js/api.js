import { apiUrl } from "./config.js";
import { err } from "./helpers.js";
import { togglePoll } from "./state.js";

/* */
export async function pollAPI(stateManager) {
  console.log(`Polling API at ${apiUrl}`);

  try {
    const response = await fetch(apiUrl);
    if (!response.ok) {
      throw new Error(response.statusText);
    }
    const data = await response.json();

    stateManager.update({
      isConnected: true,
      lastPoll: new Date(),
      apiVersion: data.apiVersion,
      corpusHash: data.hash_value,
      corpusTotal: data.total,
      searches: data.searches,
      error: null,
    });
  } catch (error) {
    err(`Error polling API: ${error.message}`);

    stateManager.update({
      isConnected: false,
      lastChecked: new Date(),
      error: error.message,
    });
  }
}

/* */
export function startPollAPI(stateManager, pollingInterval) {
  const pollWithInterval = () => {
    if (togglePoll()) {
      pollAPI(stateManager);
    }
  };
  pollWithInterval();
  setInterval(pollWithInterval, pollingInterval);
}

/* */
export async function deleteSearch(search) {
  const { uuid: searchUID, searchStr } = search;
  console.log(`Deleting "${searchStr}" (${searchUID})`);

  try {
    const url = `${apiUrl}/search/${searchUID}`;
    const response = await fetch(url, { method: "DELETE" });
    if (!response.ok) {
      throw new Error(response.statusText);
    }
  } catch (error) {
    err(`Error deleting "${searchStr}" (${searchUID}): ${error.message}`);
  }
}

/* */
export async function createSearch(searchStr) {
  console.log(`Searching "${searchStr}"`);

  try {
    const url = `${apiUrl}/search`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ search_str: searchStr }),
    });
    if (!response.ok) {
      throw new Error(response.statusText);
    }
  } catch (error) {
    err(`Error searching "${searchStr}: ${error.message}`);
  }
}
