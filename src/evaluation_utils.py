import json
import sqlite3
import glob
from pathlib import Path
import os

def load_json(dir):
    with open(dir, "r") as j:
        contents = json.loads(j.read())
    return contents


def connect_db(sql_dialect, db_path):
    if sql_dialect == "SQLite":
        conn = sqlite3.connect(db_path)
    else:
        raise ValueError("Unsupported SQL dialect")
    return conn


def execute_sql(predicted_sql, ground_truth, db_path, sql_dialect, calculate_func):
    conn = connect_db(sql_dialect, db_path)
    # Connect to the database
    cursor = conn.cursor()
    cursor.execute(predicted_sql)
    predicted_res = cursor.fetchall()
    cursor.execute(ground_truth)
    ground_truth_res = cursor.fetchall()
    conn.close()
    res = calculate_func(predicted_res, ground_truth_res)
    return res


def package_sqls(
    sql_path, db_root_path, engine, sql_dialect="SQLite", mode="gpt", data_mode="dev"
):
    clean_sqls = []
    db_path_list = []
    if mode == "gpt":
        # use chain of thought
        sql_data = json.load(
            open(
                sql_path
                + "predict_"
                + data_mode
                + "_"
                + engine
                + "_cot_"
                + sql_dialect
                + ".json",
                "r",
            )
        )
        for _, sql_str in sql_data.items():
            if type(sql_str) == str:
                sql, db_name = sql_str.split("\t----- bird -----\t")
            else:
                sql, db_name = " ", "financial"
            clean_sqls.append(sql)
            db_path_list.append(db_root_path + db_name + "/" + db_name + ".sqlite")

    elif mode == "gt":
        sqls = open(sql_path + data_mode + "_" + sql_dialect + "_gold.sql")
        sql_txt = sqls.readlines()
        # sql_txt = [sql.split('\t')[0] for sql in sql_txt]
        for idx, sql_str in enumerate(sql_txt):
            # print(sql_str)
            sql, db_name = sql_str.strip().split("\t")
            clean_sqls.append(sql)
            db_path_list.append(db_root_path + db_name + "/" + db_name + ".sqlite")

    return clean_sqls, db_path_list


def sort_results(list_of_dicts):
    return sorted(list_of_dicts, key=lambda x: x["sql_idx"])


def print_data(score_lists, count_lists, metric="F1 Score"):
    levels = ["simple", "moderate", "challenging", "total"]
    print("{:20} {:20} {:20} {:20} {:20}".format("", *levels))
    print("{:20} {:<20} {:<20} {:<20} {:<20}".format("count", *count_lists))

    print(
        f"======================================    {metric}    ====================================="
    )
    print("{:20} {:<20.2f} {:<20.2f} {:<20.2f} {:<20.2f}".format(metric, *score_lists))


def postprocess_results(db_root_path, results_folder):
    sqls = []
    dbs = []
    sql_seq_no = []
    gold_sqls = []
    unrevised_sqls = []
    files=glob.glob(str(Path(results_folder) / '*_*.json'))
    for f in files:
        if not os.path.basename(f)[0].isnumeric():
            continue
        parts = os.path.basename(f)[:-5].split('_')
        sql_seq_no.append(int(parts[0]))
        db_name = '_'.join(parts[1:])
        dbs.append(str(Path(db_root_path) / db_name / (db_name + ".sqlite")))
        predicted = ''
        gold = ''
        with open(f) as s:
            j = json.load(s)
            for jj in j:
                if 'candidate_generation' in jj:
                    if "PREDICTED_SQL" in jj['revision']:
                        predicted = jj['revision']['PREDICTED_SQL']
                    if "GOLD_SQL" in jj['revision']:    
                        gold = jj['revision']['GOLD_SQL']
                    unrevised_sqls.append(predicted)
                
                if 'revision' in jj:
                    if "PREDICTED_SQL" in jj['revision']:
                        predicted = jj['revision']['PREDICTED_SQL']
                    if "GOLD_SQL" in jj['revision']:    
                        gold = jj['revision']['GOLD_SQL']

        sqls.append(predicted)
        gold_sqls.append(gold)
    return sqls, gold_sqls, dbs, sql_seq_no, unrevised_sqls


if __name__ == '__main__':
    postprocess_results('/mnt/c/python/CHESS/data/dev/dev_databases', '/mnt/c/python/CHESS/results/dev/keyword_extraction+entity_retrieval+context_retrieval+candidate_generation+revision+evaluation/dev_test/2024-08-19-13-55-20')
