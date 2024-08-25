import sys
import argparse
import multiprocessing as mp
from func_timeout import func_timeout, FunctionTimedOut
from evaluation_utils import (
    load_json,
    execute_sql,
    sort_results,
    print_data,
    postprocess_results
)
import pandas as pd
from pathlib import Path
import json
import numpy as np


exec_result = []

def result_callback(result):
    exec_result.append(result)


def calculate_ex(predicted_res, ground_truth_res):
    res = [0, '', '', '']
    if set(predicted_res) == set(ground_truth_res):
        res = [1, '', '', '']
    else:
        error = ''
        predicted_shape = np.asarray(predicted_res).shape
        gold_shape = np.asarray(ground_truth_res).shape
        if gold_shape[0] != predicted_shape[0]:
            error = 'number of rows is less than expected' if gold_shape[0] > predicted_shape[0] else 'number of rows is more than expected'
        elif gold_shape[1] != predicted_shape[1]:
            error = 'number of columns is less than expected' if gold_shape[0] > predicted_shape[0] else 'number of columns is more than expected'
        else:
            error = 'values are different although number of rows and number of columns are correct'
        res = [0, error, json.dumps(ground_truth_res), json.dumps(predicted_res)]
    return res


def execute_model(
    predicted_sql, ground_truth, db_place, idx, meta_time_out, sql_dialect, sql_seq_no
):
    error = ''
    try:
        res = func_timeout(
            meta_time_out,
            execute_sql,
            args=(predicted_sql, ground_truth, db_place, sql_dialect, calculate_ex),
        )
    except KeyboardInterrupt:
        sys.exit(0)
    except FunctionTimedOut:
        error = 'timeout'
        res = [0, error, '', '']
    except Exception as e:
        error = str(e)  # possibly len(query) > 512 or not executable
        res = [0, error, '', '']
    db = Path(db_place).stem
    result = {"sql_idx": idx, "res": res[0], "err": res[1], "predicted": predicted_sql, "gold": ground_truth, "db": db, "seq": sql_seq_no, 'gold_res': res[2], 'predicted_res': res[3]}
    return result


def run_sqls_parallel(
    sqls, db_places, num_cpus=1, meta_time_out=30.0, sql_dialect="SQLite", sql_seq_no=[]
):
    pool = mp.Pool(processes=min(num_cpus, len(sqls)))
    for i, sql_pair in enumerate(sqls):

        predicted_sql, ground_truth = sql_pair
        pool.apply_async(
            execute_model,
            args=(
                predicted_sql,
                ground_truth,
                db_places[i],
                i,
                meta_time_out,
                sql_dialect,
                sql_seq_no[i]
            ),
            callback=result_callback,
        )
    pool.close()
    pool.join()


def compute_acc_by_diff(exec_results, diff_json_path, sql_seq_no):
    num_queries = len(exec_results)
    results = [res["res"] for res in exec_results]
    contents = load_json(diff_json_path)
    simple_results, moderate_results, challenging_results = [], [], []

    for i, seq_no in enumerate(sql_seq_no):
        content = contents[seq_no]     
        if content["difficulty"] == "simple":
            simple_results.append(exec_results[i])

        if content["difficulty"] == "moderate":
            moderate_results.append(exec_results[i])

        if content["difficulty"] == "challenging":
            try:
                challenging_results.append(exec_results[i])
            except:
                print(i)

    if len(simple_results) > 0:
        simple_acc = sum([res["res"] for res in simple_results]) / len(simple_results)
    else:
        simple_acc = 0.0
    if len(moderate_results):
        moderate_acc = sum([res["res"] for res in moderate_results]) / len(moderate_results)
    else:
        moderate_acc = 0.0
    if len(challenging_results) > 0:
        challenging_acc = sum([res["res"] for res in challenging_results]) / len(
            challenging_results
        )
    else:
        challenging_acc = 0.0

    all_acc = sum(results) / num_queries
    count_lists = [
        len(simple_results),
        len(moderate_results),
        len(challenging_results),
        num_queries,
    ]
    return (
        simple_acc * 100,
        moderate_acc * 100,
        challenging_acc * 100,
        all_acc * 100,
        count_lists,
    )


def dump_wrong_sqls(exec_result, args):
    wrong_sqls = []
    questions = load_json(args.diff_json_path)
    for res in exec_result:
        result = {}
        if res['res'] == 0:
            result['question_id'] = res['seq']
            result['question'] = questions[res['seq']]['question']
            result['evidence'] = questions[res['seq']]['evidence']
            result["SQL"] = questions[res['seq']]['SQL']
            result["difficulty"] = questions[res['seq']]['difficulty']
            result['db_id'] = questions[res['seq']]['db_id']
            result['error'] = res['err']
            result['predicted'] = res['predicted']
            result['gold_result'] = res['gold_res']
            result['predicted_result'] = res['predicted_res']
            wrong_sqls.append(result)        
    with open(str(Path(args.predicted_sql_path) / 'wrong_sqls.json'), 'w') as f:
        json.dump(wrong_sqls, f, indent=2)


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
    
    args = args_parser.parse_args()
    
    pred_queries, gt_queries, db_paths, sql_seq_no = postprocess_results(args.db_root_path, args.predicted_sql_path)

    query_pairs = list(zip(pred_queries, gt_queries))

    run_sqls_parallel(
        query_pairs,
        db_places=db_paths,
        num_cpus=args.num_cpus,
        meta_time_out=args.meta_time_out,
        sql_dialect=args.sql_dialect,
        sql_seq_no=sql_seq_no
    )
    exec_result = sort_results(exec_result)
    pd.DataFrame(exec_result).to_csv(Path(args.predicted_sql_path) / 'evaluation_results.csv', index=False)
    
    dump_wrong_sqls(exec_result, args)
    
    print("start calculate")
    simple_acc, moderate_acc, challenging_acc, acc, count_lists = compute_acc_by_diff(
        exec_result, args.diff_json_path, sql_seq_no
    )
    score_lists = [simple_acc, moderate_acc, challenging_acc, acc]
    print(f"EX for {args.engine} on {args.sql_dialect} set")
    print("start calculate")
    print_data(score_lists, count_lists, metric="EX")
    print(
        "==========================================================================================="
    )
    print(f"Finished EX evaluation for {args.engine} on {args.sql_dialect} set")
    print("\n\n")
