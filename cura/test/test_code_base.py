from cura.code_base import CodeBase
import pytest
import os
import threading

def clean_code_base(code_base: CodeBase):
    os.system(f"rm -rf {code_base.chroma_path}")
    os.system(f"rm -rf {code_base.parent_path}")

test_storage_root = "test_storage"

def test_init():
    def get_file_content(file: str) -> str:
        return "content"
    code_base = CodeBase("test_init", get_file_content, test_storage_root)
    assert code_base._get_file_content == get_file_content
    assert code_base.empty is True
    assert code_base.vector_store is not None
    assert code_base.retriever is not None
    
    clean_code_base(code_base)

dummy_files = {
    "file1.py": "def test():\n    print('Hello World')\n",
    "file2.py": "for i in range(10):\n    print(i)\n",
    "file3.md": "# Hello World\n",
    "file4.md": "# Hello World\n## Hello World\n",
}

def get_file_content(file: str) -> str:
    return dummy_files[file]


def test_add_files():
    code_base = CodeBase("test_add_files", get_file_content, test_storage_root)
    code_base.add_files(dummy_files.keys())
    assert len(list(code_base.storage.yield_keys())) == len(dummy_files.keys())
    
    clean_code_base(code_base)

id = 0
lock = threading.Lock()
@pytest.mark.parametrize("query, expected_file_name", [
    ("def test():\n    print('Hello World')\n", "file1.py"),
    ("for i in range(10):\n    print(i)\n", "file2.py"),
    ("# Hello World\n", "file3.md"),
    ("# Hello World\n## Hello World\n", "file4.md"),
    ("Find the file that is practicing for loops", "file2.py"),
    
])
def test_query(query: str, expected_file_name: str):
    global id
    with lock:
        my_id = id
        id += 1
    
    code_base = CodeBase(f"test_query_{my_id}", get_file_content, test_storage_root)
    code_base.add_files(dummy_files.keys())
    results = code_base.retrieve_files(query)
    has_file = False
    print([result.metadata["file_path"] for result in results])
    for result in results:
        if result.metadata["file_path"] == expected_file_name:
            has_file = True
            break
    assert has_file
    
    clean_code_base(code_base)

def test_storage():
    code_base = CodeBase("test_storage", get_file_content, test_storage_root)
    code_base.add_files(dummy_files.keys())
    assert len(list(code_base.storage.yield_keys())) == len(dummy_files.keys())
    
    code_base2 = CodeBase("test_storage", get_file_content, test_storage_root)
    assert list(code_base2.storage.yield_keys()) == list(code_base.storage.yield_keys())
    
    assert code_base2.empty is False
    assert code_base2.vector_store.get() == code_base.vector_store.get()
    
    
    clean_code_base(code_base)