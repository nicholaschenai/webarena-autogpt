# Attribution
The original authors of WebArena can be found here:
[[Code](https://github.com/web-arena-x/webarena)]
[[Site](https://webarena.dev/)]
[[Paper](https://arxiv.org/2307.13854)]

This uses the AutoGPT LangChain implementation in "Auto-GPT for Online Decision Making: Benchmarks and Additional Opinions"
[[Code](https://github.com/younghuman/LLMAgent)]
[[Paper](https://arxiv.org/abs/2306.02224)]

# Intro
This repo is a modification of WebArena, forked from version e32b71e3f5b2463bb102457591bc06c0f2c93acf Oct 21, 2023

# Modification: AutoGPT
Key components include tool use, chat memory, memory retrieval and reflection. As this uses LangChain, it inherits the validation benefits

Usage for 4k context:

```bash
python lc_run.py --instruction_path agent/prompts/jsons/langchain_prompt.json --agent_type lc_agent --test_start_idx 0 --test_end_idx 812 --model gpt-3.5-turbo --lc_type autogpt --max_tokens 250 --max_obs_length 950 --result_dir outputs/autogpt
```

Usage for 16k context:

```bash
python lc_run.py --instruction_path agent/prompts/jsons/langchain_prompt.json --agent_type lc_agent --test_start_idx 0 --test_end_idx 812 --model gpt-3.5-turbo-16k --lc_type autogpt --max_tokens 250  --max_obs_length 3000 --send_token_limit 16385 --base_plus_mem_tokens 8400 --result_dir outputs/autogpt-16k
```

**Warning** This does not use early stopping from WebArena so it can potentially repeat actions for the whole 30 steps

**Warning** For 16k model, longer context + increased price per token makes this expensive (~$120+)

# Modification: LangChain Structured Tool Chat (STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION)

This also supports the LangChain Structured Tool Chat experiment

Usage:

```bash
python lc_run.py --instruction_path agent/prompts/jsons/langchain_prompt.json --agent_type lc_agent --test_start_idx 0 --test_end_idx 812 --model gpt-3.5-turbo --result_dir outputs/langchain-agent
```
