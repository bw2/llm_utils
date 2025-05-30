
ANTHROPIC_MODELS = {
	"3.5": "claude-3-5-sonnet-20240620",
	"3": "claude-3-opus-20240229",
}

GEMINI_MODELS = {
	"2.5-flash": "gemini-2.5-flash-preview-05-20",
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
