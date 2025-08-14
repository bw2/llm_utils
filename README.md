
### Features

- provides a single simplified python API for querying different LLMs via the OpenAI, Gemini, Anthropic, and Mistral web APIs
- by default, responses are cached in a local sqlite database. Subsequent identical API calls will return the cached response without querying the model.   


### Installation

To install llm_utils, run:
```
python3 -m pip install git+https://github.com/bw2/llm_utils
```


### Quick Start

Create a ~/.env text file and add one or more of the following lines:
```
ANTHROPIC_API_KEY=<your Anthropic API key from https://docs.anthropic.com/en/api/getting-started>
OPENAI_API_KEY=<your OpenAI API key from https://platform.openai.com/api-keys>
GEMINI_API_KEY=<your Gemini API key from https://ai.google.dev/gemini-api/docs/api-key>
MISTRAL_API_KEY=<your Mistral API key from https://console.mistral.ai/api-keys/>
```
The contents of ~/.env will be loaded as environment variables when you import llm_utils.

The `llm_utils.text_completion` module contains functions for querying different version of LLMs from these providers.

Basic usage example:

```
from llm_utils.text_completion import ask_anthropic, ask_gemini, ask_mistral, ask_openai

my_question = "What's an interesting and useful fact that few people know?"
for model_name, ask_function in [
    ("Anthropic", ask_anthropic),
    ("Gemini", ask_gemini),
    ("Mistral", ask_mistral),
    ("OpenAI", ask_openai),
]:
    response_text = ask_function(my_question)
    print("=" * 80)
    print(f"{model_name}:\n", response_text)
```

Full usage example:
```
from llm_utils.text_completion import ask_anthropic, ask_gemini, ask_mistral, ask_openai
from llm_utils.constants import OPENAI_MODELS, GEMINI_MODELS, ANTHROPIC_MODELS, MISTRAL_MODELS

# define question and model instructions
my_question = "What's an interesting and useful fact that few people know?"
system_prompt = "You are a wise and pithy LLM that understands all human knowledge. You answers are cogent and concise."  # specifies desire model behavior, role, etc. for this query 

# ask all versions of all models
models_to_query = [
    ("Anthropic", ask_anthropic, "3"),
    ("Anthropic", ask_anthropic, "3.5"),
]
for model_version in GEMINI_MODELS:
    models_to_query.append(("Gemini", ask_gemini, model_version))
for model_version in MISTRAL_MODELS:
    models_to_query.append(("Mistral", ask_mistral, model_version))
for model_version in OPENAI_MODELS:
    models_to_query.append(("OpenAI", ask_openai, model_version))

for model_name, ask_function, model_version in models_to_query:
    response_text = ask_function(
        my_question, 
        model=model_version,  # the version of the model to use
        temperature=1,        # a number between 0 and 1 that controls the randomness of the response
        max_tokens=100,       # the maximum number of tokens to generate
        system_prompt=system_prompt,
        check_cache=True,     # whether to check the internal SQLite cache for an existing response before querying the model
        update_cache=True,    # whether to record the model's response in the internal SQLite cache
        verbose=True,
    )
        
    print("=" * 80)
    print(f"{model_name} {model_version}:\n", response_text)
```

