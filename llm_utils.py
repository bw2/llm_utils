from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # take environment variables from .env.

import anthropic
import google.generativeai as genai
import openai
import os
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import sqlite3

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

ANTHROPIC_MODELS = {
	"3.5": "claude-3-5-sonnet-20240620",
	"3": "claude-3-opus-20240229",
}

GEMINI_MODELS = {
	"1.5-pro": "gemini-1.5-pro",
	"1.5-flash": "gemini-1.5-flash",
}

OPENAI_MODELS = {
	"4o": "gpt-4o-2024-05-13",
	"4": "gpt-4-turbo-2024-04-09",
	"3.5": "gpt-3.5-turbo-16k"
}

MISTRAL_MODELS = {  # from https://docs.mistral.ai/getting-started/models/
	"open-mistral-7b": "open-mistral-7b", #  The first dense model released by Mistral AI, perfect for experimentation, customization, and quick iteration. At the time of the release, it matched the capabilities of models up to 30B parameters. Learn more on our blog post	32k
	"open-mixtral-8x7b": "open-mixtral-8x7b", # A sparse mixture of experts model. As such, it leverages up to 45B parameters but only uses about 12B during inference, leading to better inference throughput at the cost of more vRAM. Learn more on the dedicated blog post	32k
	"open-mixtral-8x22b": "open-mixtral-8x22b", # A bigger sparse mixture of experts model. As such, it leverages up to 141B parameters but only uses about 39B during inference, leading to better inference throughput at the cost of more vRAM. Learn more on the dedicated blog post	64k
	#"mistral-small-latest": "mistral-small-latest", # Suitable for simple tasks that one can do in bulk (Classification, Customer Support, or Text Generation)	32k
	#"mistral-medium-latest": "mistral-medium-latest", # Ideal for intermediate tasks that require moderate reasoning (Data extraction, Summarizing a Document, Writing emails, Writing a Job Description, or Writing Product Descriptions)	32k
	"mistral-large-latest": "mistral-large-latest", # Our flagship model that's ideal for complex tasks that require large reasoning capabilities or are highly specialized (Synthetic Text Generation, Code Generation, RAG, or Agents). Learn more on our blog post	32k
	#"mistral-embed": "mistral-embed", # A model that converts text into numerical vectors of embeddings in 1024 dimensions. Embedding models enable retrieval and retrieval-augmented generation applications. It achieves a retrieval score of 55.26 on MTEB	8k
	#"codestral-latest": "codestral-latest", # A cutting-edge generative model that has been specifically designed and optimized for code generation tasks, including fill-in-the-middle and code completion	32k
	#"open-codestral-mamba": "open-codestral-mamba", # A Mamba 2 language model specialized in code generation. Learn more on our blog post	256k
	#"mistral-nemo": "mistral-nemo", # A 12B model built with the partnership with Nvidia. It is easy to use and a drop-in replacement in any system using Mistral 7B that it supersedes. Learn more on our blog post	128k
}



MAX_RETRIES = 5

RESPONSE_CACHE_DB_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".cache/llm_response_cache.db")
RESPONSE_CACHE_DB = None

ANTHROPIC_CLIENT = None
OPENAI_CLIENT = None
MISTRAL_CLIENT = None


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


def ask_openai(question, model="4o", temperature=0, system_prompt="", check_cache=True, update_cache=True, verbose=False):
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