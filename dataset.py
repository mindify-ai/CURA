from datasets import load_dataset

ds = load_dataset("princeton-nlp/SWE-bench_Lite")

ds = ds['test']

# Turn the dataset into a csv file
ds_csv = ds.to_csv("swe_bench_lite.csv")