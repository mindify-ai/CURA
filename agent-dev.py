import logging

logging.basicConfig(
    filename='logs/agent-dev.log',
    level=logging.DEBUG,
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

import dotenv
from cura.prediction import do_prediction_plan
from datasets import load_dataset
from swebench.harness.constants import USE_X86
from swebench.harness.run_evaluation import run_instances
import platform

dotenv.load_dotenv()



def main():
    swebench = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
    if platform.machine() == 'arm64':
        swebench = swebench.filter(lambda x: x['instance_id'] not in USE_X86)

    data = swebench.shuffle(seed=40).select(range(1))[0]

    patch = do_prediction_plan(data)
    logging.info(f"Patch: {patch}")
    predictions = {
        data['instance_id']: {
            'model_patch': patch,
            'model_name_or_path': 'gpt-4o-mini',
            'instance_id': data['instance_id']
        }
    }
    run_instances(
        predictions=predictions,
        instances=[data],
        cache_level="env",
        clean=False,
        run_id="test",
        force_rebuild=False,
        max_workers=1,
        timeout=180,
    )
    

if __name__ == '__main__':
    main()