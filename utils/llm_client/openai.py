import logging
from typing import Optional, Dict, Any
from .base import BaseClient

try:
    from openai import OpenAI
except ImportError:
    OpenAI = 'openai'


logger = logging.getLogger(__name__)

class OpenAIClient(BaseClient):

    ClientClass = OpenAI

    def __init__(
        self,
        model: str,
        temperature: float = 1.0,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_dimensions: Optional[int] = None,
        dimensions: Optional[int] = None,  # 别名，兼容配置文件中的 dimensions 参数
    ) -> None:
        super().__init__(model, temperature)
        
        if isinstance(self.ClientClass, str):
            logger.fatal(f"Package `{self.ClientClass}` is required")
            exit(-1)
        
        self.client = self.ClientClass(api_key=api_key, base_url=base_url)
        self.embedding_model = embedding_model or "text-embedding-3-small"
        # 优先使用 embedding_dimensions，然后是 dimensions
        self.embedding_dimensions = embedding_dimensions if embedding_dimensions is not None else dimensions
    
    def _chat_completion_api(self, messages: list[dict], temperature: float, n: int = 1):
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature, n=n, stream=False,
        )
        return response.choices
    
    def embeddings(self, input: str, dimensions: Optional[int] = None, encoding_format: Optional[str] = None) -> list[float]:
        """
        Get embeddings for input text.
        
        Args:
            input: Text to embed
            dimensions: Optional dimension size (supported by text-embedding-v3 and text-embedding-v4)
            encoding_format: Optional encoding format (e.g., "float", "base64")
        
        Returns:
            List of embedding floats
        """
        # Prepare parameters
        params: Dict[str, Any] = {
            "model": self.embedding_model,
            "input": input
        }
        
        # 优先使用实例的 embedding_dimensions，然后使用传入的 dimensions 参数
        actual_dimensions = self.embedding_dimensions if dimensions is None else dimensions
        if actual_dimensions is not None:
            params["dimensions"] = actual_dimensions
            
        if encoding_format is not None:
            params["encoding_format"] = encoding_format
        
        response = self.client.embeddings.create(**params)
        return response.data[0].embedding
