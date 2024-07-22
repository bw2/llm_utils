from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # take environment variables from .env.

import anthropic
import google.generativeai as genai
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import openai
import os
import sqlite3

from llm_utils.constants import ANTHROPIC_MODELS, GEMINI_MODELS, MISTRAL_MODELS, OPENAI_MODELS

MAX_RETRIES = 5

RESPONSE_CACHE_DB_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".cache/llm_response_cache.db")
RESPONSE_CACHE_DB = None

ANTHROPIC_CLIENT = None
OPENAI_CLIENT = None
MISTRAL_CLIENT = None


if "GEMINI_API_KEY" in os.environ:
	genai.configure(api_key=os.environ["GEMINI_API_KEY"])


def get_openai_models_list():
	return [
		(model.id, datetime.fromtimestamp(model.created).isoformat())
		for model in sorted(openai_client.models.list(), key=lambda x: x.created)
	]

def _connect_to_response_cache():
	global RESPONSE_CACHE_DB

	if RESPONSE_CACHE_DB is not None:
		return

	cache_dir = os.path.dirname(RESPONSE_CACHE_DB_PATH)
	if not os.path.isdir(cache_dir):
		print("Creating response cache directory:", cache_dir)
		os.makedirs(cache_dir)

	RESPONSE_CACHE_DB = sqlite3.connect(
		os.path.expanduser(RESPONSE_CACHE_DB_PATH),
		isolation_level=None,
		cached_statements=0)
	print("Connected to response cache:", RESPONSE_CACHE_DB_PATH)
	try:
		RESPONSE_CACHE_DB.execute("CREATE TABLE cache (question NOT NULL, model NOT NULL, temperature REAL, max_tokens INTEGER, system_prompt, response, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)").close()
		RESPONSE_CACHE_DB.execute("CREATE UNIQUE INDEX cache_index ON cache (question, model, temperature, max_tokens, system_prompt)").close()

	except sqlite3.OperationalError as e:
		if "already exists" not in str(e):
			print("ERROR:", e)

def _get_response_from_cache(question, model, temperature, max_tokens=0, system_prompt=""):
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
		# upsert into RESPONSE_CACHE_DB
		RESPONSE_CACHE_DB.execute(
			"INSERT INTO cache (question, model, temperature, max_tokens, system_prompt, response) VALUES (?, ?, ?, ?, ?, ?)"
			"ON CONFLICT(question, model, temperature, max_tokens, system_prompt) DO UPDATE SET response=?", (
			question, model, temperature, max_tokens, system_prompt, response, response))

	except sqlite3.IntegrityError as e:
		print("CACHE ERROR:", e)


def _ask_model_with_cache_and_retry(
	run_query,
	question,
	model_label,
	temperature,
	max_tokens,
	system_prompt,
	check_cache=True,
	update_cache=True,
	verbose=False):

	if check_cache:
		cached_response = _get_response_from_cache(question, model_label, temperature, max_tokens, system_prompt)
		if cached_response is not None:
			if verbose:
				print(f"cache hit for q{len(question)}, {model_label}, temp={temperature}, tokens={max_tokens}, s{len(system_prompt)}")
			return cached_response
	if verbose:
		print(f"calling api for q{len(question)}, {model_label}, temp={temperature}, tokens={max_tokens}, s{len(system_prompt)}")
	if temperature < 0 or temperature > 1:
		raise ValueError(f"Temperature {temperature} not in [0, 1]")

	for retry_attempt in range(0, MAX_RETRIES):
		try:
			response_text = run_query()
			break
		except Exception as e:
			print(f"WARNING: {type(e).__name__}: {e}. Retry attempt #{retry_attempt + 1} failed.")
	else:
		print(f"ERROR: Failed after {MAX_RETRIES} attempts.")
		return None

	if update_cache:
		_update_response_cache(question, model_label, temperature, max_tokens, system_prompt, response_text)

	return response_text


def ask_anthropic(question, model="3.5", temperature=0, max_tokens=1000, system_prompt="", check_cache=True, update_cache=True, verbose=False):
	global ANTHROPIC_CLIENT

	if model not in ANTHROPIC_MODELS:
		raise ValueError(f"Invalid anthropic model version: {model}. It must be one of {ANTHROPIC_MODELS.keys()}")

	if ANTHROPIC_CLIENT is None:
		ANTHROPIC_CLIENT = anthropic.Anthropic()

	def run_query():
		message = ANTHROPIC_CLIENT.messages.create(
			model=ANTHROPIC_MODELS[model],
			max_tokens=max_tokens,
			temperature=temperature,
			system=system_prompt,
			messages=[{"role": "user", "content": f"{question}"}],
		)
		if len(message.content) == 1:
			response_text = message.content[0].text
		else:
			print(f"WARNING: Expected 1 response from Anthropic, but got {len(message.content)}")
			response_text = None
		return response_text

	return _ask_model_with_cache_and_retry(
		run_query,
		question,
		f"anthropic {model}",
		temperature=temperature,
		max_tokens=max_tokens,
		system_prompt=system_prompt,
		check_cache=check_cache,
		update_cache=update_cache,
		verbose=verbose)


def ask_openai(question, model="4o", temperature=0, max_tokens=1000, system_prompt="", check_cache=True, update_cache=True, verbose=False):
	global OPENAI_CLIENT

	if model not in OPENAI_MODELS:
		raise ValueError(f"Invalid openai model version: {model}. It must be one of {OPENAI_MODELS.keys()}")

	if OPENAI_CLIENT is None:
		OPENAI_CLIENT = openai.OpenAI()

	def run_query():
		response = OPENAI_CLIENT.chat.completions.create(
			model=OPENAI_MODELS[model],
			messages=[
				{ "role": "system", "content": system_prompt },
				{ "role": "user", "content": question },
			],
			temperature=temperature,
		)
		if response.choices[0].finish_reason != "stop":
				print(f"WARNING: OpenAI did not stop generating text. finish_reason was: '{response.choices[0].finish_reason}'")
				return None

		if len(response.choices) == 1:
			response_text = response.choices[0].message.content
		else:
			print(f"WARNING: Expected 1 response from OpenAI, but got {len(response.choices)}")
			response_text = None
		return response_text

	return _ask_model_with_cache_and_retry(
		run_query,
		question,
		f"openai {model}",
		temperature=temperature,
		max_tokens=0,
		system_prompt=system_prompt,
		check_cache=check_cache,
		update_cache=update_cache,
		verbose=verbose)

def ask_gemini(question, model="1.5-pro", temperature=0, max_tokens=1000, system_prompt="", check_cache=True, update_cache=True, verbose=False):
	def run_query():
		gemini_client = genai.GenerativeModel(
			model_name=GEMINI_MODELS[model],
			system_instruction=system_prompt or None)

		response = gemini_client.generate_content(
			contents=question,
			generation_config = genai.GenerationConfig(
        		max_output_tokens=max_tokens,
        		temperature=temperature,
    		)
		)

		return response.text

	return _ask_model_with_cache_and_retry(
		run_query,
		question,
		f"gemini {model}",
		temperature=temperature,
		max_tokens=max_tokens,
		system_prompt=system_prompt,
		check_cache=check_cache,
		update_cache=update_cache,
		verbose=verbose)


def ask_mistral(question, model="mistral-large-latest", temperature=0, max_tokens=1000, system_prompt="", check_cache=True, update_cache=True, verbose=False):
	global MISTRAL_CLIENT

	if model not in MISTRAL_MODELS:
		raise ValueError(f"Invalid mistral model version: {model}. It must be one of {MISTRAL_MODELS.keys()}")

	if MISTRAL_CLIENT is None:
		MISTRAL_CLIENT = MistralClient()  # api_key=os.environ["MISTRAL_API_KEY"])

	def run_query():
		response = MISTRAL_CLIENT.chat(
			model=MISTRAL_MODELS[model],
			messages=[ChatMessage(role="system", content=system_prompt), ChatMessage(role="user", content=question)],
			temperature=temperature,
			max_tokens=max_tokens,
		)
		if len(response.choices) == 1:
			response_text = response.choices[0].message.content
		else:
			print(f"WARNING: Expected 1 response from Mistral, but got {len(response.choices)}")
			response_text = None
		return response_text

	return _ask_model_with_cache_and_retry(
		run_query,
		question,
		f"mistral {model}",
		temperature=temperature,
		max_tokens=max_tokens,
		system_prompt=system_prompt,
		check_cache=check_cache,
		update_cache=update_cache,
		verbose=verbose)