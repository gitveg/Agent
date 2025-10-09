

import os
import sys
from typing import List

from src.configs.configs import DEFAULT_PARENT_CHUNK_SIZE
from src.utils.general_utils import get_time_async
current_script_path = os.path.abspath(__file__)
# 将项目根目录添加到sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_script_path)))
root_dir = os.path.dirname(root_dir)
sys.path.append(root_dir)
import time
from src.utils.log_handler import debug_logger
from src.client.database.milvus.milvus_client import MilvusClient
from src.client.database.elasticsearch.es_client import ESClient
from src.client.database.mysql.mysql_client import MysqlClient
from src.utils.log_handler import insert_logger

class Retriever:
    def __init__(self, vectorstore_client: MilvusClient, mysql_client: MysqlClient, es_client: ESClient):
        self.mysql_client = mysql_client
        self.milvus_client = vectorstore_client
        self.es_client = es_client.es_store
        self.parent_chunk_size = DEFAULT_PARENT_CHUNK_SIZE

    # 現在
    @get_time_async
    async def insert_documents(self, docs, parent_chunk_size, single_parent=False):
        insert_logger.info(f"Inserting {len(docs)} documents, parent_chunk_size: {parent_chunk_size}, single_parent: {single_parent}")
        if parent_chunk_size != self.parent_chunk_size:
            self.parent_chunk_size = parent_chunk_size
        # insert_logger.info(f'insert documents: {len(docs)}')
        ids = None if not single_parent else [doc.metadata['doc_id'] for doc in docs]
        return await self.aadd_documents(docs, parent_chunk_size=parent_chunk_size,
                                                   es_client=self.es_client, ids=ids, single_parent=single_parent)
    async def get_retrieved_documents(self, query: str, vector_store: MilvusClient, es_store: ESClient, partition_keys: List[str], time_record: dict,
                                    hybrid_search: bool, top_k: int, expr: str = None):
        milvus_start_time = time.perf_counter()
        #  把milvus搜索转为Document类型 
        query_docs = vector_store.search_docs(query, expr, top_k, partition_keys)
        for doc in query_docs:
            doc.metadata['retrieval_source'] = 'milvus'
        milvus_end_time = time.perf_counter()
        time_record['retriever_search_by_milvus'] = round(milvus_end_time - milvus_start_time, 2)

        if not hybrid_search:
            return query_docs
        try:
            filter = [{"terms": {"metadata.kb_id.keyword": partition_keys}}]
            es_sub_docs = await es_store.asimilarity_search(query, k=top_k, filter=filter)
            print(es_sub_docs)
            for doc in es_sub_docs:
                doc.metadata['retrieval_source'] = 'es'
            time_record['retriever_search_by_es'] = round(time.perf_counter() - milvus_end_time, 2)
            debug_logger.info(f"Got {len(query_docs)} documents from vectorstore and {len(es_sub_docs)} documents from es, total {len(query_docs) + len(es_sub_docs)} merged documents.")
            query_docs.extend(es_sub_docs)
        except Exception as e:
            debug_logger.error(f"Error in get_retrieved_documents on es_search: {e}")
        return query_docs