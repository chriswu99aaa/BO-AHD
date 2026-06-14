import openai
class InterfaceAPI:
    def __init__(self, api_endpoint, api_key, model_LLM, debug_mode):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.client = model_LLM
        self.debug_mode = debug_mode
        self.n_trial = 5
        self.openai = openai

    def get_response(self, prompt_content, temp=1.):

        response = self.client.chat_completion(1, [{"role": "user", "content": prompt_content}], temperature=temp)
        ret = response[0].message.content
        return ret
    
    def get_embedding(self, prompt_content: str, dimensions: int = None, encoding_format: str = "float"):
        """
        Get embedding for prompt content.
        
        Args:
            prompt_content: Text to embed
            dimensions: Optional dimension size (supported by text-embedding-v3 and text-embedding-v4).
                       Default is None, which uses the model's default dimension.
                       For Qwen3 text-embedding-v4, typical values are 1024, 1536, etc.
            encoding_format: Encoding format for the embedding. Default is "float".
                            Other options may include "base64" (if supported by the model).
        
        Returns:
            Embedding vector as list of floats
        """
        response = self.client.embeddings(
            input=prompt_content,
            dimensions=dimensions,
            encoding_format=encoding_format
        )
        return response
