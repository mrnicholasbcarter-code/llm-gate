# OpenHands (formerly OpenDevin) Integration

[OpenHands](https://github.com/All-Hands-AI/OpenHands) executes autonomous engineering tasks. 

To use `llm-gate` with OpenHands, run the `llm-gate` FastAPI server (`llm-gate serve --port 8000`) and point the OpenHands `LLM_BASE_URL` to it. The gateway will ensure OpenHands uses tier-3 models for scanning files and only swaps to `opus-4.8` when manipulating core application logic.
