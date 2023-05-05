import replicate
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM

DEFAULT_MODEL_USER = "replicate"
DEFAULT_MODEL_NAME = "vicuna-13b"
DEFAULT_MODEL_HASH = "a68b84083b703ab3d5fbf31b6e25f16be2988e4c3e21fe79c2ff1c18b99e61c1"
DEFAULT_MODEL_VERSION = f"{DEFAULT_MODEL_USER}/{DEFAULT_MODEL_NAME}:{DEFAULT_MODEL_HASH}"


class ReplicateLLM(LLM):
    """
    ReplicateLLM is a Langchain LLM that invokes a model deployed to the
    Replicate model hosting service.
    """

    model_version: str = DEFAULT_MODEL_VERSION
    max_length: int = 500
    temperature: float = 0.75
    top_p: float = 1.0
    repetition_penalty: float = 1.1

    @property
    def _llm_type(self) -> str:
        return "replicate-custom-llm"

    def _call(
        self, 
        prompt: str, 
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
    ) -> str:
        """Call the LLM with the given prompt and return the result."""
        iterable = replicate.run(
            model_version=self.model_version,
            input={
                "prompt": prompt,
                "max_length": self.max_length,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "repetition_penalty": self.repetition_penalty,
            }
        )
        return "".join(iterable)
