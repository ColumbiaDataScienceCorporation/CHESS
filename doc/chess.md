## shell scripts under run folder

- run_main.sh - run am experiment with a list of questions
- run_evalution.sh - calculate EX, VEX, F1 statistics for a run
- run_preproess.sh - ingest db description, calculates embeddings to store in vector db, calculate MinHash to store in LSH

## main python scripts under src folder

- main.py - main script to run an experiment with a list of questions
- preproces.py - main script to preprocess a db to get ready for experiments
- evaluation_ex.py - calculate EX measure
- evaluation_f1.py - calculate F1 measure
- evaluation_vex.py - calculate VEX measure
- evaluation_llm.py - ask LLM to identify/category errors in incorrect SQLs
- evalution_utils.py - some utility methods for evalutions

# modules

## database_utils

- db_catalog
    
    1. csv_utils.py -load_tables_description(): read table description csv (original_column_name, column_name, column_description, data_format, value_description)

    2. preprocess.py - make_db_context_vec_db(): for each column in every table, create a document for each of 'column_name', 'column_description', and 'value_description', use Chroma to create a vector db of the documents

    3. search.py - query_vector_db(): return top_k documents in vector_db based on the query

- db_values

    1. preprocess.py - make_lsh(): Creates a MinHashLSH store for the database
        ```for each table
            for each text column
              for each value
                 calculate the minhash and put it into MinHashLSH store
           
           save minhashes: Dict['table_name_column_name_id', Tuple[MinHash, table_name, column_name, value]] in a pkl file
           
           save MinHashLSH in a pkl file
        ```
    2. search.py - query_lsh(): Queries the LSH for similar values to the given keyword and returns the top results.
        ```
            get results by querying LSH with minhash of query
            sort jaccard similairities of all results and minhash of query
            return top n
        ```

- execution.py - compare_sqls(), execute_sql(), aggregate_sql()
- db.info - get_db_all_tables(), get_table_all_columns()
- schema_generator.py - ?
- schema.py - ?
- sql_parser.py 
    1. get_sql_condition_literals() - Retrieves literals used in SQL query conditions and checks their existence in the database

## llm

- engine_configs.py - contains configs for many LLMs
- models.py - async_llm_chain_call(): handling multiple LLMs calls in thread pool; get_llm_chain(engine, temperature, base_uri) - return llm chain object 
- parsers.py - define LLM response parsers for each step in the pipeline
- prompts.py - methods to load prompt templates and construct prompts from templates.

## pipeline

- keyword_extraction.py - extract key words from user's question using its prompt template
    
    a. dependent nodes: entity_retrieval, context_retrieval

    b. results: {'keywords': a list of keywords }

- entity_retrieval.py - find columns and values similar to keywords extracted from user's question

    a. dependent nodes: column_filtering, column_selection, table_selection, candiate_generation, revision
    
    b. results: {'similar_columns': similar_columns, 
                 'similar_values': similar_values}
    
    1. for each keyword and all of its tokens, find the highest matching table and column
        a. filter columns by edit distance between keyword and column name
        b. return the column of the highest similarity between `{table}`.`{column}` name and "{question} {hint}" 
    
    2. for each keyword and all of its tokens, find  column values similar to keywords in user's question
        a. find the top 10 column values that are close to the minhash of keyword by LSH
        b. then find the top 5 columns values with the smallest edit distances
        c. then return the top column value with the highest similarity

- context_retrieval.py - for each keyword, find top_k tables/columns similar to '{question} {keyworkd}' and '{evidence} {keyword}' by searching vectordb
    
    a. dependent nodes: column_selection, table_selection, candidate_generation, revision

    b. result: {"schema_with_descriptions": schema_with_descriptions}
        
        schema_with_description is Dict[table, Dict[column, Dict['column_description', str]]]

- column_filtering.py - uses "column_filtering_with_examples" template. for each value in "similar_values", call llm to decide whether a column is relavant. if yes, add it to tentative_schema. Add all "similar_columns" to tentative_schema too.

    a. dependent nodes: all nodes that use tentative schema

    b. result: {"tentative_schema": tentative_schema}

- column_selection.py - use entity_retrieval's similar_values and context_retrieval's schema_with_description to ask LLM to to pick the columns 

    LLM ressponse:
    ```
    {{
    "chain_of_thought_reasoning": "Your reasoning for selecting the columns, be concise and clear.",
    "table_name1": ["column1", "column2", ...],
    "table_name2": ["column1", "column2", ...],
    ...
    }}
    ```
    a. dependent nodes: all nodes that use tentative schema

    b. result: {
            "tentative_schema": column_names,
            "model_selected_columns": column_names, 
            "chain_of_thought_reasoning": chain_of_thought_reasoning
        }

- table_selection.py - use "table_selection" template. use entity_retrieval's similar_values and and context_retrieval's schema_with_description to ask LLM to to pick the tables. Add all "similar_columns" to tentative_schema too.

    a. dependent nodes: all nodes that use tentative schema

    b. result: {
            "chain_of_thought_reasoning": aggregated_result["chain_of_thought_reasoning"],
            "selected_tables": table_names,
            "tentative_schema": tentative_schema
        }

- candidate_generation.py - use tentative_schema, entity_retrieval's similar_values and context_retrieval's schema_with_description to populate candidate_generation template to construst prompt and call llm with to generate SQL

    a. dependent nodes: revision, evaluation

    b. result: next(sqls)

- revision.py - use complete_schema, candidate_generation's SQL, and SQL's results if any, wrong entities, context_retrieval's schema_with_description to populate revision template

    a. dependent nodes: evaluation

    b. result: {
        "chain_of_thought_reasoning": chosen_res.get("chain_of_thought_reasoning", ""),
        "SQL": chosen_res["revised_SQL"],
    }

    1. wrong entities are detected by comparing entities used in SQL with entity_retrieval's similar_values by edit distance
    
- evalution.py - generate results using candidate_generation's SQL and revision's SQL

    a. dependent nodes: none

    b. result: { 
        
            "candidation_generation": {
                "Question": question,
                "Evidence": evidence,
                "GOLD_SQL": ground_truth_sql,
                "PREDICTED_SQL": predicted_sql
            },

            "revision": {
                "Question": question,
                "Evidence": evidence,
                "GOLD_SQL": ground_truth_sql,
                "PREDICTED_SQL": predicted_sql
            }
        }

    - pipeline_manager.py - utility methods: get_prompt_engine_parser(), get_template_name(), get_parser_name

    - utils.py -  utility methods
        1. node_decorator() - A decorator to add logging and error handling to pipeline node functions.
        2. get_last_node_result() - Retrieves the last result for a specific node type from the execution history.
        3. missings_status() - Checks for missing tables and columns in the tentative schema.
        4. add_columns_to_tentative_schema() - Adds columns to the tentative schema based on selected columns
    
    - workflow_builder.py - build_pipeline() - build a pipeline into a LangGraph using the nodes.

    # runner

    - logger.py - manages logging
        1. log_conversation() - log conversation with LLM for each question
        2. dump_history_to_file() - dump execution history into a json file for each question
        3. _set_log_level() - set log level and setup console and file loghandlers
        4. _init() - initialize a logger for a question
        4. __new()__  - factory method to construct a logger for a question

    - database_manager.py - manages methods that query db, MinHash and MinHashLSH stores.

        1. __new()__  - factory method to construct a database_manager for a question
        2. _init() - initialize a database_manager for a question
        3. query_lsh() - query MinHashLSH store by keyword and return top_n
        4. query_vector_db() - query vectordb by keyword and return top_k
        5. get_column_profiles() - Generates column profiles for the schema.
        6. get_database_schema_string() - Generates a schema string for the database.
        7. add_connections_to_tentative_schema() - Adds connections to the tentative schema.
        8. with_db_path() - Decorator to inject db_path as the first argument to the function.
        9. add_methods_to_class() - Adds methods to the class with db_path automatically provided via with_db_path() decorator

    - run_mananger.py - manage a run(experiment)
        1. initialize_tasks() - load the json that contains the questions for the run
        2. run_tasks() - run the tasks in a multiprocessing Pool
        3. worker() - Worker function to process a single task
        4. generate_sql_files() - dump SQLs from candidate_generation and revision into separate json files under result_directory
        5. task_done() - update statistics and dump statistics into a json file after each task is done
    
    - statistics_manager.py - manages statistics of a run
        1. update_stats() - Updates the statistics based on the evaluation result
        2. dump_statistics_to_file() - Dumps the current statistics to a JSON file
    
    - task.py - Task class Represents a task with question and database details

