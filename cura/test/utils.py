from datasets import load_dataset
IMAGE_NAME = 'swe:x86_64'

TEST_DATA = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')[0]