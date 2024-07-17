from dotenv import load_dotenv
load_dotenv()  # take environment variables from .env.

import anthropic
import openai

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

MAX_RETRIES = 5
def ask_anthropic(question, model="3.5", temperature=0, max_tokens=1000, system_prompt=None):
	if model not in ANTHROPIC_MODELS:
		raise ValueError(f"Model {model} not in {ANTHROPIC_MODELS.keys()}")
	if temperature < 0 or temperature > 1:
		raise ValueError(f"Temperature {temperature} not in [0, 1]")

	for retry_attempt in range(0, MAX_RETRIES):
		try:
			message = anthropic_client.messages.create(
				model=ANTHROPIC_MODELS[model],
				max_tokens=max_tokens,
				temperature=teperature,
				system=system_prompt,
				messages=[{ "role": "user", "content": f"{question}"}]
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

	return message.content[0].text


def ask_openai(question, model="4o", temperature=0, system_prompt=None):
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

	return response.choices[0].message.content
