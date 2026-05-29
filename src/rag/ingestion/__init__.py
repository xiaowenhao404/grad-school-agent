"""RAG 数据摄取层。

详见 DEV_SPEC.md 3.2.2 节。

流程：Document Loader -> Splitter -> Embedding (Dense + Sparse) -> Chroma + BM25
"""
