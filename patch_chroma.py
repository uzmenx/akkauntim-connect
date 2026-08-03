import re

with open('bot/learning/ai_strategist.py', 'r') as f:
    code = f.read()

replacement = '''        cache_key = f"{current_situation_desc}_{market_condition}_{limit}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        import time
        start_time = time.time()
        try:
            results = self.collection.query(
                query_texts=[current_situation_desc],
                n_results=limit,
                where={"$or": [{"market_condition": market_condition}, {"market_condition": "all"}]}
            )
            count = self.collection.count()
            elapsed = time.time() - start_time
            import logging
            if elapsed > 0.5:
                logging.getLogger(__name__).warning(f"ChromaDB search took {elapsed:.3f}s for {count} rules. Consider re-indexing or HNSW tuning.")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"ChromaDB search error: {e}")
            return ""'''

code = code.replace('''        cache_key = f"{current_situation_desc}_{market_condition}_{limit}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        try:
            results = self.collection.query(
                query_texts=[current_situation_desc],
                n_results=limit,
                where={"$or": [{"market_condition": market_condition}, {"market_condition": "all"}]}
            )
        except Exception:
            return ""''', replacement)

with open('bot/learning/ai_strategist.py', 'w') as f:
    f.write(code)
