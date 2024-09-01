from tqdm import tqdm
import dotenv
from cura.prediction import do_prediction_plan
from datasets import load_dataset
from concurrent.futures import ThreadPoolExecutor, as_completed
dotenv.load_dotenv()

def main():
    swebench = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')

    num_samples = 1
    test_set = swebench.shuffle(seed=42).select(range(num_samples))

    results = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(do_prediction_plan, test_set[i]) for i in range(num_samples)]
        for future in tqdm(as_completed(futures), total=num_samples):
            result = future.result()
            results.append(result)

    print(results)

if __name__ == '__main__':
    main()