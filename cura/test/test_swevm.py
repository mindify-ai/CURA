from cura.vm import SWEVM
import pytest
import dotenv
from cura.test.utils import TEST_DATA
from datasets import load_dataset
from swebench.harness.constants import USE_X86
import platform
dotenv.load_dotenv()

def test_init():
    with SWEVM(data=TEST_DATA) as vm:
        repo_path = vm.data['repo'].split('/')[-1]
        assert vm.data == TEST_DATA
        assert repo_path in vm.run_command("ls /")
        assert vm.run_command(f"bash -c 'cd {repo_path} && git rev-parse HEAD'").strip() == vm.data['base_commit']
        assert vm.code_base is not None


def test_all_swebench_env_install():
    start_index = 65
    swebench = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
    if platform.machine() == 'arm64':
        swebench = [x for x in swebench if x['instance_id'] not in USE_X86]
        
    seen = set()
    unique_data = []
    for entry in swebench:
        key = (entry['repo'], entry['version'])
        if key not in seen:
            seen.add(key)
            unique_data.append(entry)
    
    print(f"Testing {len(unique_data)} entries")
    unpass = []
    for i, data in enumerate(unique_data, start_index):
        try:
            with SWEVM(data=data, create_code_base=False):
                pass
        except Exception as e:
            unpass.append(i)
            print(f"Failed on {data['repo']} {data['version']}")
            print(e)
        print(f"Passed {i+1}/{len(unique_data)}")
    
    print(f"Failed on {len(unpass)} entries")
    print(unpass)
            
    