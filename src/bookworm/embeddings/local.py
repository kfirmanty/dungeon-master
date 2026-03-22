"""
Local embedding provider using HuggingFace transformers directly.

This module is the heart of the learning experience. Instead of using the
sentence-transformers library (which hides everything behind model.encode()),
we implement the full embedding pipeline manually:

    Raw Text → Tokenization → Transformer Forward Pass → Mean Pooling → L2 Normalization → Embedding Vector

Each step is explained below. Understanding this pipeline is fundamental to
working with any embedding model, whether local or API-based.
"""


class TransformerEmbeddingProvider:
    """Generate sentence embeddings using a transformer model.

    WHAT ARE EMBEDDINGS?

    An embedding is a dense vector (list of floats) that represents the *meaning*
    of a piece of text in high-dimensional space. Key properties:

    - Texts with similar meanings produce vectors that point in similar directions
    - "The cat sat on the mat" and "A feline rested on the rug" → vectors close together
    - "The cat sat on the mat" and "Stock prices rose sharply" → vectors far apart

    This model (all-MiniLM-L6-v2) outputs 384-dimensional vectors. That means each
    piece of text becomes a point in 384-dimensional space — impossible to visualize,
    but the math for measuring distance works the same as in 2D or 3D.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._tokenizer = None
        self._model = None

    def _load_model(self) -> None:
        """Lazy-load the tokenizer and model on first use.

        Why lazy? Loading a model takes a few seconds and ~90MB of RAM. If the user
        is just running `bookworm list` (no embeddings needed), we skip the cost.

        What gets loaded:
        1. Tokenizer — a vocabulary mapping that converts words into integer IDs.
           Each model has its own vocabulary learned during training.
        2. Model — the neural network weights (~22M parameters for MiniLM).
           These were trained on 1 billion sentence pairs to learn that similar
           sentences should produce similar vectors.
        """
        if self._tokenizer is not None:
            return

        from transformers import AutoTokenizer, AutoModel

        print(f"Loading embedding model: {self._model_name} ...")
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
        self._model = AutoModel.from_pretrained(self._model_name)

        # eval() switches from training mode to inference mode.
        # This disables dropout layers (which randomly zero out neurons during
        # training to prevent overfitting). During inference, we want deterministic
        # outputs — the same input should always produce the same embedding.
        self._model.eval()

    def _mean_pooling(self, model_output, attention_mask):
        """Average all token embeddings into a single sentence embedding.

        WHY MEAN POOLING?

        The transformer outputs one vector per TOKEN (subword), not per sentence.
        For "The cat sat", we get 3 token vectors (each 384-dim). We need to
        collapse them into 1 sentence vector.

        Options:
        - [CLS] token: Just use the first token's vector. Fast but throws away
          information from other tokens. The original BERT paper used this, but
          Reimers & Gurevych (2019) showed it's suboptimal for similarity tasks.
        - Mean pooling: Average ALL token vectors. Captures information from the
          entire sentence. Works best for sentence similarity.
        - Max pooling: Take the element-wise maximum. Sometimes useful for
          capturing the most "activated" features.

        THE ATTENTION MASK PROBLEM:

        When we batch multiple sentences, shorter ones get padded with zeros to
        match the longest sentence's length. Example:

            Batch: ["Hello world", "Hi"]
            After tokenization (padded):
              [101, 7592, 2088, 102, 0, 0]   ← "Hello world" + 2 padding tokens
              [101, 7632, 102,   0, 0, 0]     ← "Hi" + 3 padding tokens

            Attention mask:
              [1, 1, 1, 1, 0, 0]  ← 1 = real token, 0 = padding
              [1, 1, 1, 0, 0, 0]

        Without the mask, padding tokens (which have meaningless embeddings) would
        pollute our average. The mask ensures we only average over real tokens.

        Math:  sentence_embedding = sum(token_embeddings * mask) / sum(mask)

        Shapes explained:
            model_output[0]:    (batch_size, sequence_length, 384)
            attention_mask:     (batch_size, sequence_length)
            After unsqueeze(-1): (batch_size, sequence_length, 1)   ← broadcast-ready
            After expand:        (batch_size, sequence_length, 384) ← matches embeddings
            Result:              (batch_size, 384)                  ← one vector per sentence
        """
        import torch

        # model_output[0] is the last hidden state: one 384-dim vector per token
        token_embeddings = model_output[0]

        # Expand mask to match embedding dimensions for element-wise multiplication
        # unsqueeze(-1) adds a dimension: (batch, seq_len) → (batch, seq_len, 1)
        # expand() broadcasts it: (batch, seq_len, 1) → (batch, seq_len, 384)
        input_mask_expanded = (
            attention_mask.unsqueeze(-1)
            .expand(token_embeddings.size())
            .float()
        )

        # Zero out padding token embeddings, then sum across the sequence dimension
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)

        # Count real tokens (clamp to avoid division by zero for empty sequences)
        sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)

        return sum_embeddings / sum_mask

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        The full pipeline:
        1. TOKENIZE: "Hello world" → [101, 7592, 2088, 102]
        2. FORWARD PASS: Token IDs → Contextualized token embeddings
        3. MEAN POOL: Token embeddings → Single sentence embedding
        4. NORMALIZE: Scale to unit length (L2 norm = 1)
        """
        import torch
        import torch.nn.functional as F

        self._load_model()

        # STEP 1: TOKENIZATION
        # Convert text into token IDs that the model understands.
        #
        # - padding=True:     Pad shorter texts to match the longest in this batch
        # - truncation=True:  Cut texts longer than the model's max (256 tokens for MiniLM).
        #                     Truncated text loses its tail — the embedding won't capture
        #                     information from the end. This is why we chunk text BEFORE
        #                     embedding: smaller chunks → less truncation risk.
        # - return_tensors="pt":  Return PyTorch tensors (vs. numpy or plain lists)
        encoded = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )

        # STEP 2: FORWARD PASS
        # Feed token IDs through the transformer to get contextualized embeddings.
        #
        # torch.no_grad() disables gradient computation. Gradients are only needed
        # during training (for backpropagation). Disabling them:
        # - Reduces memory usage (no need to store intermediate values)
        # - Speeds up computation slightly
        with torch.no_grad():
            model_output = self._model(**encoded)

        # STEP 3: MEAN POOLING
        # Collapse per-token vectors into per-sentence vectors
        sentence_embeddings = self._mean_pooling(model_output, encoded["attention_mask"])

        # STEP 4: L2 NORMALIZATION
        # Scale each vector to unit length (L2 norm = 1.0).
        #
        # Why? After normalization, cosine similarity simplifies to the dot product:
        #   cosine_sim(a, b) = dot(a, b) / (||a|| * ||b||)
        #   If ||a|| = ||b|| = 1:  cosine_sim(a, b) = dot(a, b)
        #
        # This is why pgvector's cosine distance operator (<=>)  works efficiently
        # with normalized vectors — it can use dot products internally.
        sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)

        return sentence_embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query.

        Identical to embed_texts() with one item — separated for readability
        at call sites. In a production system, the query embedding and document
        embedding might use DIFFERENT models or prompts (asymmetric search).
        For MiniLM, they're the same.
        """
        return self.embed_texts([query])[0]
