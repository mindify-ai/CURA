# %%
from tqdm import tqdm
import dotenv
dotenv.load_dotenv()

# %%
from datasets import load_dataset
swebench = load_dataset('princeton-nlp/SWE-bench', split='test')

# Randomly select a test set with 10 samples
num_samples = int(len(swebench) * 0.25)
print(num_samples)
test_set = swebench.shuffle(seed=42).select(range(num_samples))

print(test_set)

from cura.prediction import do_prediction
results = []

for i in tqdm(range(num_samples)):
    results.append(do_prediction(test_set[i]))
    
print(results)