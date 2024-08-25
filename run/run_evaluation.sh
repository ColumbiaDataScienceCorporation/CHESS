db_root_path='./data/dev/dev_databases/'

data_mode='mini_dev' # not used any more
diff_json_path='./data/dev/dev.json' # _sqlite.json, _mysql.json, _postgresql.json
# Path where the predicted SQL queries are stored
#predicted_sql_path='./results/dev/keyword_extraction+entity_retrieval+context_retrieval+candidate_generation+revision+evaluation/sub_sampled_bird_dev_set/2024-08-19-20-46-53'
predicted_sql_path='./results/dev/keyword_extraction+entity_retrieval+context_retrieval+candidate_generation+revision+evaluation/sub_sampled_bird_dev_set/2024-08-22-17-16-26'


ground_truth_path='./data/'    # not used any more
num_cpus=6
meta_time_out=30.0
mode_gt='gt'                  # not used any more
mode_predict='gpt'            # not used any more

# Choose the engine to run, e.g. gpt-4, gpt-4-32k, gpt-4-turbo, gpt-35-turbo, GPT35-turbo-instruct
engine='gpt-4o'          # not used any more


# Choose the SQL dialect to run, e.g. SQLite, MySQL, PostgreSQL
# PLEASE NOTE: You have to setup the database information in evaluation_utils.py 
# if you want to run the evaluation script using MySQL or PostgreSQL
sql_dialect='SQLite'

# echo "starting to compare with knowledge for ex engine: ${engine} sql_dialect: ${sql_dialect}"
# python3 -u ./src/evaluation_ex.py --db_root_path ${db_root_path} --predicted_sql_path ${predicted_sql_path} --data_mode ${data_mode} \
# --ground_truth_path ${ground_truth_path} --num_cpus ${num_cpus} --mode_gt ${mode_gt} --mode_predict ${mode_predict} \
# --diff_json_path ${diff_json_path} --meta_time_out ${meta_time_out} --engine ${engine} --sql_dialect ${sql_dialect}


echo "starting to compare with knowledge for ves engine: ${engine} sql_dialect: ${sql_dialect}"
python3 -u ./src/evaluation_ves.py --db_root_path ${db_root_path} --predicted_sql_path ${predicted_sql_path} --data_mode ${data_mode} \
--ground_truth_path ${ground_truth_path} --num_cpus ${num_cpus} --mode_gt ${mode_gt} --mode_predict ${mode_predict} \
--diff_json_path ${diff_json_path} --meta_time_out ${meta_time_out}  --engine ${engine} --sql_dialect ${sql_dialect}


# echo "starting to compare with knowledge for soft-f1 engine: ${engine} sql_dialect: ${sql_dialect}"
# python3 -u ./src/evaluation_f1.py --db_root_path ${db_root_path} --predicted_sql_path ${predicted_sql_path} --data_mode ${data_mode} \
# --ground_truth_path ${ground_truth_path} --num_cpus ${num_cpus} --mode_gt ${mode_gt} --mode_predict ${mode_predict} \
# --diff_json_path ${diff_json_path} --meta_time_out ${meta_time_out}  --engine ${engine} --sql_dialect ${sql_dialect}