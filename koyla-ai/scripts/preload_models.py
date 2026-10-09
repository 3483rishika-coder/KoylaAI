"""Download the OCR + embedding models at Docker *build* time, so the first upload after deploy does not
have to fetch ~150 MB from the internet (slow, memory-hungry, and impossible on an air-gapped host).

FASTEMBED_CACHE_PATH must be the same value at build time and run time (the Dockerfile sets it once as ENV).
"""
import numpy as np

try:
    from rapidocr import RapidOCR                      # rapidocr >= 2.0
except ImportError:                                     # legacy package
    from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
engine(np.full((64, 256, 3), 255, dtype=np.uint8))     # warm-up call forces any lazy model download
print("rapidocr models ready")

from fastembed import TextEmbedding

emb = TextEmbedding("BAAI/bge-small-en-v1.5")
list(emb.embed(["warm up"]))
print("fastembed model ready")
