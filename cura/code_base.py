#import pysqlite3
import sys
#sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import (
    Language,
    RecursiveCharacterTextSplitter,
)
from langchain_core.documents import Document
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import LocalFileStore, create_kv_docstore

from .utils import TimeRecorder
import os
import logging
from typing import Optional
class CodeBase:
    def __init__(self, name: str, get_file_content: callable, storage_root: str = "storage", logger: Optional[logging.Logger] = None):
        self._get_file_content: callable[[str], str] = get_file_content
        self.logger = logger if logger is not None else logging.getLogger(self.__class__.__name__)
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
        
        self.storage_root = storage_root
        self.chroma_path = os.path.join(self.storage_root, name, "chroma")
        self.parent_path = os.path.join(self.storage_root, name, "parent")
        
        self.vector_store = Chroma(
            collection_name=name,
            embedding_function=embeddings,
            persist_directory=self.chroma_path,
        )
        self.storage = create_kv_docstore(LocalFileStore(root_path=self.parent_path))
        self.retriever = ParentDocumentRetriever(
            vectorstore=self.vector_store,
            docstore=self.storage,
            child_splitter=RecursiveCharacterTextSplitter(),
            search_type="mmr",
            search_kwargs={
                'k': 20,
                #'score_threshold': 0.05,
            }
        )
    
    def add_files(self, files: set[str]):
        self.logger.info(f"Adding {len(files)} files to code base.")
        file_contents = {}
        for file in files:
            try:
                content = self._get_file_content(file)
                if content != "":
                    file_contents[file] = content
            except Exception as e:
                self.logger.warning(f"Error getting file content for {file}: {e}")
        extension_to_splitter = {
            ".py": RecursiveCharacterTextSplitter(separators=["\nclass ", "\ndef ", "\n\tdef "]),
            ".md": RecursiveCharacterTextSplitter.from_language(
                language=Language.MARKDOWN, chunk_size=100, chunk_overlap=0
            ),
        }
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=100, chunk_overlap=10
        )
        
        for extension in extension_to_splitter:
            files = { file: content for file, content in file_contents.items() if file.endswith(extension) }
            if not files:
                continue
            self.retriever.child_splitter = extension_to_splitter[extension]
            docs = [Document(page_content=content, metadata={"file_path": file_path}) for file_path, content in files.items()]
            with TimeRecorder(f"Adding {extension} files"):
                self.retriever.add_documents(docs)
        
        other_files = { file: content for file, content in file_contents.items() if not any(file.endswith(extension) for extension in extension_to_splitter) }
        if other_files:
            self.retriever.child_splitter = text_splitter
            docs = [Document(page_content=content, metadata={"file_path": file_path}) for file_path, content in other_files.items()]
            self.retriever.add_documents(docs)
    
    @property
    def empty(self) -> bool:
        return len(list(self.storage.yield_keys())) == 0
    
    def retrieve_files(self, query: str) -> list[Document]:
        return self.retriever.invoke(query)