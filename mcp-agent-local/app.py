try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import MistralClient as Mistral