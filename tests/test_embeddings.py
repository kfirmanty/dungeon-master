"""Tests for the embedding provider.

These tests verify that the manual transformer pipeline (tokenize → forward
pass → mean pooling → normalize) produces correct, meaningful embeddings.
"""

import pytest

from bookworm.embeddings.local import TransformerEmbeddingProvider
from bookworm.utils import cosine_similarity


@pytest.fixture(scope="module")
def provider():
    """Shared provider instance — model loads once for all tests in this module."""
    return TransformerEmbeddingProvider()


class TestEmbeddingDimensions:
    def test_single_text_returns_384_dims(self, provider):
        vectors = provider.embed_texts(["Hello world"])
        assert len(vectors) == 1
        assert len(vectors[0]) == 384

    def test_batch_returns_correct_count(self, provider):
        texts = ["First text", "Second text", "Third text"]
        vectors = provider.embed_texts(texts)
        assert len(vectors) == 3
        assert all(len(v) == 384 for v in vectors)


class TestEmbeddingQuality:
    """Verify that embeddings capture semantic meaning, not just surface form."""

    def test_similar_texts_have_high_similarity(self, provider):
        # These mean roughly the same thing, expressed differently
        v1 = provider.embed_query("The cat sat on the mat")
        v2 = provider.embed_query("A feline rested on the rug")
        sim = cosine_similarity(v1, v2)
        assert sim > 0.5, f"Similar sentences should have similarity > 0.5, got {sim:.3f}"

    def test_unrelated_texts_have_low_similarity(self, provider):
        v1 = provider.embed_query("The cat sat on the mat")
        v2 = provider.embed_query("Stock prices rose sharply in Q3")
        sim = cosine_similarity(v1, v2)
        assert sim < 0.4, f"Unrelated sentences should have similarity < 0.4, got {sim:.3f}"

    def test_identical_texts_have_perfect_similarity(self, provider):
        text = "The quick brown fox jumps over the lazy dog"
        v1 = provider.embed_query(text)
        v2 = provider.embed_query(text)
        sim = cosine_similarity(v1, v2)
        assert sim > 0.99, f"Identical texts should have similarity ~1.0, got {sim:.3f}"


class TestEmbedQueryConsistency:
    def test_embed_query_matches_embed_texts(self, provider):
        """embed_query should produce the same result as embed_texts with one item."""
        text = "Test consistency between methods"
        query_vec = provider.embed_query(text)
        batch_vec = provider.embed_texts([text])[0]

        sim = cosine_similarity(query_vec, batch_vec)
        assert sim > 0.99, f"embed_query and embed_texts should match, got similarity {sim:.3f}"


class TestNormalization:
    def test_vectors_are_unit_length(self, provider):
        """After L2 normalization, each vector should have norm ≈ 1.0."""
        import numpy as np

        vectors = provider.embed_texts(["Test normalization"])
        norm = np.linalg.norm(vectors[0])
        assert abs(norm - 1.0) < 0.01, f"L2 norm should be ~1.0, got {norm:.4f}"
