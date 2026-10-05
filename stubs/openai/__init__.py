# Stub so XVada modules import under PyPy (the real openai wheel will not build there).
# Any actual LLM call raises, so a run that silently needed the LLM cannot pass unnoticed.
class OpenAI:
    def __init__(self, *a, **k):
        pass

    def __getattr__(self, name):
        raise RuntimeError("openai stub: LLM call attempted")
