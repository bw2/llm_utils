from llm_utils import ask_anthropic, ask_openai, ask_gemini, ask_mistral, ANTHROPIC_MODELS, OPENAI_MODELS, MISTRAL_MODELS, GEMINI_MODELS

def _normalize_answer(answer):
	answer = answer.strip().strip("'").lower()
	if "unlikely" in answer:
		answer = "unlikely"
	elif "probably" in answer:
		answer = "probably"
	elif "unclear" in answer:
		answer = "unclear"
	elif answer.startswith("yes"):
		answer = "yes"
	elif answer.startswith("no"):
		answer = "no"
	else:
		print(f"WARNING: response could not be parsed. Setting it to 'unlikely'. The response was: {answer}")
		answer = "unlikely"

	score_map = {
		"yes": 3,
		"probably": 1,
		"unclear": 0,
		"unlikely": -1,
		"no": -2,
	}
	return score_map[answer]


def does_diagnosis_match_phenotype(candidate_diagnosis, phenotype_description, verbose=False):
	system_prompt = ("You are an expert in rare disease genetics, OMIM, phenotypes, and physiology."
	"Please provide concise, highly accurate responses. For each question, answer only "
	"'yes', 'probably', 'unclear', 'unlikely', or 'no'.")
	question = (f"is '{candidate_diagnosis}' a reasonable diagnosis for someone whose medical record says '{phenotype_description}'? " 
	"Note, the entire response should just be one of these words which indicate a probability: 'yes', 'probably', 'unlikely', or 'no")

	responses = []
	for model_version in "3.5", "3":
		answer = ask_anthropic(
			question, 
			model=model_version,
			temperature=0, 
			max_tokens=10, 
			system_prompt=system_prompt, 
			check_cache=True, 
			update_cache=True, 
			verbose=verbose)
		
		if answer is None:
			raise ValueError(f"anthropic {model_version} did not return a response")
		
		responses.append((f"anthropic {model_version}", _normalize_answer(answer)))

	for model_version in "4o", "4", "3.5":
		answer = ask_openai(
			question,
			model=model_version,
			temperature=0,
			system_prompt=system_prompt,
			check_cache=True,
			update_cache=True,
			verbose=verbose)

		if answer is None:
			raise ValueError(f"openai {model_version} did not return a response")

		responses.append((f"openai {model_version}", _normalize_answer(answer)))

	for model_version in MISTRAL_MODELS:
		answer = ask_mistral(
			question,
			model=model_version,
			temperature=0,
			system_prompt=system_prompt,
			check_cache=True,
			update_cache=True,
			verbose=verbose)

		if answer is None:
			raise ValueError(f"mistral {model_version} did not return a response")

		responses.append((f"mistral {model_version}", _normalize_answer(answer)))

	for model_version in GEMINI_MODELS:
		answer = ask_gemini(
			question,
			model=model_version,
			temperature=0,
			system_prompt=system_prompt,
			check_cache=True,
			update_cache=True,
			verbose=verbose)

		if answer is None:
			raise ValueError(f"gemini {model_version} did not return a response")

		responses.append((f"gemini {model_version}", _normalize_answer(answer)))

	return dict(responses)