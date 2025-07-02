# Orca Chat

Personal playground for orchestrating chat models with LangChain and Ollama.
The project requires Python 3.12 or newer and is not yet packaged for general use.

## Quickstart

Set environment variables to point at your models (or rely on the defaults):

```
CHAT_MODEL_NAME=<name>
CHAT_MODEL_URL=<http://host:port>
SUMMARIZER_MODEL_NAME=<name>
SUMMARIZER_MODEL_URL=<http://host:port>
```

Run the built-in demo:

```bash
python -m orca_chat
```

It will stream a response for a sample prompt and log stage transitions and
summaries to the console.
