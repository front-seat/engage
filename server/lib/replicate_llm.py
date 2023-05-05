from time import sleep

import replicate
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM

DEFAULT_MODEL_USER = "replicate"
DEFAULT_MODEL_NAME = "vicuna-13b"
DEFAULT_MODEL_HASH = "a68b84083b703ab3d5fbf31b6e25f16be2988e4c3e21fe79c2ff1c18b99e61c1"
# DEFAULT_MODEL_VERSION = f"{DEFAULT_MODEL_USER}/{DEFAULT_MODEL_NAME}:{DEFAULT_MODEL_HASH}"


class ReplicateLLM(LLM):
    """
    ReplicateLLM is a Langchain LLM that invokes a model deployed to the
    Replicate model hosting service.
    """

    model_user: str = DEFAULT_MODEL_USER
    model_name: str = DEFAULT_MODEL_NAME
    model_hash: str = DEFAULT_MODEL_HASH
    max_length: int = 2048
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
        model = replicate.models.get(f"{self.model_user}/{self.model_name}")
        version = model.versions.get(self.model_hash)
        pred = replicate.predictions.create(
            version=version,
            input={
                "prompt": prompt,
                "max_length": self.max_length,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "repetition_penalty": self.repetition_penalty,
            }
        )

        if pred is None:
            raise RuntimeError("Prediction failed.")
        
        # Keep reploading the prediction until it's done.
        while pred.status not in {"succeeded", "failed"}:
            pred.reload()
            sleep(0.25)

        if pred.status == "failed":
            raise RuntimeError("Prediction failed.")
        
        output = pred.output
        assert isinstance(output, list)
        
        # For each item, if it ends with a letter and has no whitespace at the
        # end, add a space to the end of it.
        items = [
            item + " " if item and item.strip() == item and item[-1].isalpha() else item
            for item in output
        ]

        # Join each item in the `iterable` with an empty string, *UNLESS*
        # the item has no whitespace at the end and it ends with a letter.
        # In that case, join it with a space.
        return "".join(items)

    def get_num_tokens(self, text: str) -> int:
        """Get the number of tokens in the given text."""
        return len(text) // 3



