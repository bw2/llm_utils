from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # take environment variables from .env.


import anthropic
import openai
import os
import sqlite3

anthropic_client = anthropic.Anthropic()
openai_client = openai.OpenAI()

def get_openai_models_list():
	return [
		(model.id, datetime.fromtimestamp(model.created).isoformat())
		for model in sorted(openai_client.models.list(), key=lambda x: x.created)
	]

ANTHROPIC_MODELS = {
	"3.5": "claude-3-5-sonnet-20240620",
	"3": "claude-3-opus-20240229",
}

OPENAI_MODELS = {
	"4o": "gpt-4o-2024-05-13",
	"4": "gpt-4-turbo-2024-04-09",
	"3.5": "gpt-3.5-turbo-16k"
}

RESPONSE_CACHE_DB = None
def _connect_to_response_cache():
    global RESPONSE_CACHE_DB

    if RESPONSE_CACHE_DB is not None:
        return

    response_cache_db_path = "~/code/llm_utils/.cache/response_cache.db"
    RESPONSE_CACHE_DB = sqlite3.connect(
        os.path.expanduser(response_cache_db_path),
        isolation_level=None,
        cached_statements=0)
    print("Connected to cache_db: ", response_cache_db_path)
    try:
        RESPONSE_CACHE_DB.execute("CREATE TABLE cache (question NOT NULL, model NOT NULL, temperature REAL, max_tokens INTEGER, system_prompt, response)").close()
        RESPONSE_CACHE_DB.execute("CREATE UNIQUE INDEX cache_index ON cache (question, model, temperature, max_tokens, system_prompt)").close()

    except sqlite3.OperationalError as e:
        if "already exists" not in str(e):
            print("ERROR:", e)

def _get_response_from_cache(question, model, temperature, max_tokens=None, system_prompt=""):
	_connect_to_response_cache()
	cursor = RESPONSE_CACHE_DB.execute(
		"SELECT response FROM cache WHERE question=? AND model=? AND temperature=? AND max_tokens=? AND system_prompt=?", (
		(question, model, temperature, max_tokens, system_prompt)))

	try:
		(response,) = next(cursor)
		return response
	except StopIteration:
		pass
	finally:
		cursor.close()

	return None

def _update_response_cache(question, model, temperature, max_tokens, system_prompt, response):
	_connect_to_response_cache()
	try:
		RESPONSE_CACHE_DB.execute(
			"INSERT INTO cache (question, model, temperature, max_tokens, system_prompt, response) VALUES (?, ?, ?, ?, ?, ?)", (
			question, model, temperature, max_tokens, system_prompt, response))
	except sqlite3.IntegrityError as e:
		print("CACHE ERROR:", e)


MAX_RETRIES = 5
def ask_anthropic(question, model="3.5", temperature=0, max_tokens=1000, system_prompt=""):
	cached_response = _get_response_from_cache(question, f"anthropic {model}", temperature, max_tokens, system_prompt)
	if cached_response is not None:
		return cached_response

	if model not in ANTHROPIC_MODELS:
		raise ValueError(f"Model {model} not in {ANTHROPIC_MODELS.keys()}")
	if temperature < 0 or temperature > 1:
		raise ValueError(f"Temperature {temperature} not in [0, 1]")

	for retry_attempt in range(0, MAX_RETRIES):
		try:
			message = anthropic_client.messages.create(
				model=ANTHROPIC_MODELS[model],
				max_tokens=max_tokens,
				temperature=temperature,
				system=system_prompt,
				messages=[{"role": "user", "content": f"{question}"}],
			)
			break
		except Exception as e:
			print(f"WARNING: Anthropic error: {e}. Retry attempt #{retry_attempt + 1} failed.")
	else:
		print(f"ERROR: Anthropic failed after {MAX_RETRIES} attempts.")
		return None

	if len(message.content) != 1:
		print(f"WARNING: Expected 1 response from Anthropic, but got {len(message.content)}")
		return None

	response_text = message.content[0].text
	_update_response_cache(question, f"anthropic {model}", temperature, max_tokens, system_prompt, response_text)

	return response_text


def ask_openai(question, model="4o", temperature=0, system_prompt=""):
	cached_response = _get_response_from_cache(question, f"openai {model}", temperature, None, system_prompt)
	if cached_response is not None:
		return cached_response

	if model not in OPENAI_MODELS:
		raise ValueError(f"Model {model} not in {OPENAI_MODELS.keys()}")
	if temperature < 0 or temperature > 1:
		raise ValueError(f"Temperature {temperature} not in [0, 1]")

	for retry_attempt in range(0, MAX_RETRIES):
		try:
			response = openai_client.chat.completions.create(
				model=OPENAI_MODELS[model],
				messages=[
					{ "role": "system", "content": system_prompt },
					{ "role": "user", "content": question },
				],
				temperature=temperature,
			)
			break
		except Exception as e:
			print(f"WARNING: OpenAI error: {e}. Retry attempt #{retry_attempt + 1} failed.")
	else:
		print(f"ERROR: OpenAI failed after {MAX_RETRIES} attempts.")
		return None

	if len(response.choices) != 1:
		print(f"WARNING: Expected 1 response from OpenAI, but got {len(response.choices)}")
		return None

	if response.choices[0].finish_reason != "stop":
		print(f"WARNING: OpenAI did not stop generating text. finish_reason was: '{response.choices[0].finish_reason}'")
		return None

	response_text = response.choices[0].message.content
	_update_response_cache(question, f"openai {model}", temperature, None, system_prompt, response_text)

	return response_text
