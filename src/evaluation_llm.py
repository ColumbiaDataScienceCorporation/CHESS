import argparse
from evaluation_utils import (
    load_json,
)
import pandas as pd
from pathlib import Path
from llm.models import async_llm_chain_call
from llm import prompts
from llm.models import get_llm_chain
from llm.parsers import get_parser
from runner.logger import Logger
import json


def get_prompt_engine_parser(args):
    template_name = 'diagnosis'
    prompt = prompts.get_prompt(template_name)
    engine = get_llm_chain(engine=args.engine, temperature=0.7, base_uri='')
    parser = get_parser(template_name)
    return prompt, engine, parser
    

def use_llm_to_diagnose_error(results, diff_json_path, args):
    prompt, engine, parser = get_prompt_engine_parser(args)
    
    contents = load_json(diff_json_path)
    diagnosis = []
    for i, result in enumerate(results):
        if result['res'] == 0:
            t = result['seq']
            request_kwargs = {
                "QUESTION": contents[t]['question'],
                "EVIDENCE": contents[t]['evidence'],
                "GOLD_SQL": result['gold'],
                "PREDICTED_SQL": result['predicted'],
            }
            response = async_llm_chain_call(
                            prompt=prompt, 
                            engine=engine, 
                            parser=parser,
                            request_list=[request_kwargs],
                            step="diagnose",
                            sampling_count=1
                        )[0]
            
            diag = contents[t]
            diag['PREDICTED_SQL'] = result['predicted']
            diag['PROBLEMS'] = '; '.join(response[0]['problems'])
            diag['EXPLANATIONS'] = '; '.join(response[0]['explanations'])
            
            diagnosis.append(diag)
    return diagnosis


if __name__ == "__main__":
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "--predicted_sql_path", type=str, required=True, default=""
    )
    args_parser.add_argument("--ground_truth_path", type=str, required=True, default="")
    args_parser.add_argument("--data_mode", type=str, required=True, default="dev")
    args_parser.add_argument("--db_root_path", type=str, required=True, default="")
    args_parser.add_argument("--num_cpus", type=int, default=1)
    args_parser.add_argument("--meta_time_out", type=float, default=30.0)
    args_parser.add_argument("--mode_gt", type=str, default="gt")
    args_parser.add_argument("--mode_predict", type=str, default="gpt")
    args_parser.add_argument("--difficulty", type=str, default="simple")
    args_parser.add_argument("--diff_json_path", type=str, default="")
    args_parser.add_argument("--engine", type=str, default="")
    args_parser.add_argument("--sql_dialect", type=str, default="SQLite")
    args_parser.add_argument('--templates', type=str, default='mytemplates', help="number of workers.")
    
    args = args_parser.parse_args()
    
    prompts.TEMPLATES_ROOT_PATH = args.templates
    
    logger = Logger(db_id='', question_id='', result_directory=args.predicted_sql_path)
    logger._set_log_level('info', logfilename='evaluation_llm.log')
        
    exec_result = pd.read_csv(Path(args.predicted_sql_path) / 'evaluation_results.csv').to_dict('records')
    diagnosis = use_llm_to_diagnose_error(exec_result, args.diff_json_path, args)
    pd.DataFrame(diagnosis).to_csv(Path(args.predicted_sql_path) / 'evaluation_llm_results.csv', index=False)
    with open(str(Path(args.predicted_sql_path) / 'wrong_sqls_llm.json'), 'w') as f:
        json.dump(diagnosis, f, indent=2)