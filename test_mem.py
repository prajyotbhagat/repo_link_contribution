import tracemalloc
tracemalloc.start()
from fastembed import TextEmbedding
model = TextEmbedding("BAAI/bge-small-en-v1.5")
current, peak = tracemalloc.get_traced_memory()
print(f"Peak memory: {peak / 10**6} MB")
