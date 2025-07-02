# Orca Chat

Personal playground for orchestrating chat models with LangChain and Ollama.
The project requires Python 3.12 or newer and is not yet packaged for general use.

## Quickstart

Set environment variables to point at your models (or rely on the defaults):

```
LLM=<name>
LLM_URL=<http(s)://host:port>
EDITOR_LLM=<alias>
EDITOR_LLM_URL=<http(s)://host:port>
```

Run the built-in demo:

```bash
python -m orca_chat
```

It will stream a response for a sample prompt and log stage transitions and
précis to the console.
