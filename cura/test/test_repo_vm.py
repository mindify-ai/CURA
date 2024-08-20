from cura.vm import RepoVM

test_repo = "sqlfluff/sqlfluff"
test_commit_hash = "c7e791d5ff3bf681a1eb2d717a69c8e166029c42"

def test_repo_vm_init():
    with RepoVM(image_name="swe_img:latest", repo_name=test_repo, commit_hash=test_commit_hash) as vm:
        repo_path = test_repo.split('/')[-1]
        assert vm.repo_name == test_repo
        assert vm.commit_hash == test_commit_hash
        assert repo_path in vm.run_command("ls /")
        assert vm.run_command(f"bash -c 'cd {repo_path} && git rev-parse HEAD'").strip() == test_commit_hash
        