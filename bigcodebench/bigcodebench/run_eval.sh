python3 agent.py 
python3 ./evaluate.py evaluate \
--split="average" \
--subset="full" \
--samples="./full_output.jsonl" \
--local_execute=True \
--parallel=16 \
--max_as_limit=40960 \
--max_data_limit=40960 \
--max_stack_limit=20 \
--min_time_limit=30.0 \
--no_execute=False
