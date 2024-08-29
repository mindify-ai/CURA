from cura.vm import RepoVM
import pytest
import dotenv

dotenv.load_dotenv()

test_repo = "sqlfluff/sqlfluff"
test_commit_hash = "c7e791d5ff3bf681a1eb2d717a69c8e166029c42"

def test_init():
    with RepoVM(image_name="swe_img:latest", repo_name=test_repo, commit_hash=test_commit_hash) as vm:
        repo_path = test_repo.split('/')[-1]
        assert vm.repo_name == test_repo
        assert vm.commit_hash == test_commit_hash
        assert repo_path in vm.run_command("ls /")
        assert vm.run_command(f"bash -c 'cd {repo_path} && git rev-parse HEAD'").strip() == test_commit_hash
        assert vm.code_base is not None



code_base = None
@pytest.mark.parametrize("search_term, expected_file", [
    ('def dialect_shell_complete(ctx, param, incomplete) -> List["CompletionItem"]:', 'autocomplete.py'),
    ('autocomplete', 'autocomplete.py'),
])
def test_repo_vm_vector_database_search(search_term: str, expected_file: str):
    global code_base
    with RepoVM(image_name="swe_img:latest", repo_name=test_repo, commit_hash=test_commit_hash, code_base=code_base) as vm:
        if code_base is None:
            code_base = vm.code_base
        results = vm.code_base.retrieve_files(search_term)
        has_expected_file = False
        for result in results:
            if expected_file in result.metadata["file_path"]:
                has_expected_file = True
                break
        if not has_expected_file:
            print(f"Expected file {expected_file} not found in results: {[result.metadata['file_path'] for result in results]}")
        assert has_expected_file
        