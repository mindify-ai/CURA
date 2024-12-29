#python3 agent-bigcodebench.py 
python3 ./evaluate.py evaluate \
--split="average" \
--subset="hard" \
--samples="./samples.jsonl" \
--local_execute=True \
--parallel=8 \
--max_as_limit=40960 \
--max_data_limit=40960 \
--max_stack_limit=20 \
--min_time_limit=30.0 \
--no_execute=False
