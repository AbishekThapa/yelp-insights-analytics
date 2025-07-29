import json
import logging
import time
import os
import warnings
import pandas as pd
from sqlalchemy import create_engine

#Reads private database credentials from config.py
try:
    import config
except ImportError:
    print("FATAL ERROR: Configuration file 'config.py' not found.")
    print("Please copy 'config_template.py' to 'config.py' and fill it out.")
    exit()

#Data File Paths
# Public dataset paths are defined here for clarity.
DATA_PATHS = {
    'business': os.path.join(config.BASE_DIR, 'yelp_academic_dataset_business.json'),
    'checkin':  os.path.join(config.BASE_DIR, 'yelp_academic_dataset_checkin.json'),
    'review':   os.path.join(config.BASE_DIR, 'yelp_academic_dataset_review.json'),
    'tip':      os.path.join(config.BASE_DIR, 'yelp_academic_dataset_tip.json'),
    'users':    os.path.join(config.BASE_DIR, 'yelp_academic_dataset_user.json'),
}

#Core Functions
def setup_logging():
    """Initializes logging to the file specified in the config."""
    logging.basicConfig(
        filename=config.LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='w'
    )
    warnings.filterwarnings('ignore')

def create_db_engine():
    """Creates a database engine from settings in config.py."""
    try:
        connection_url = (
            f'postgresql+psycopg2://{config.DB_USER}:{config.DB_PASSWORD}@'
            f'{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}'
        )
        engine = create_engine(connection_url)
        engine.connect()
        logging.info("Successfully connected to PostgreSQL database.")
        return engine
    except Exception as e:
        logging.error(f"PostgreSQL connection failed: {e}")
        print("Error: Could not connect to the database. Check credentials in config.py.")
        return None

def load_json_to_dataframe(file_key):
    """Loads data from a JSON file into a pandas DataFrame."""
    
    file_path = DATA_PATHS.get(file_key)
    try:
        logging.info(f"Reading data from {file_path}...")
        data = [json.loads(line) for line in open(file_path, 'r', encoding='utf-8')]
        df = pd.DataFrame(data)
        logging.info(f"Successfully created DataFrame for {file_key}.")
        return df
    except FileNotFoundError:
        logging.error(f"Error: The file {file_path} was not found.")
        print(f"Error: Data file not found at {file_path}.")
    except Exception as e:
        logging.error(f"An unexpected error occurred loading {file_path}: {e}")
    return None

def load_df_to_postgres(df, table_name, engine):
    """Writes a DataFrame to a specified table in the database."""
    try:
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        logging.info(f"Successfully wrote DataFrame to table '{table_name}'.")
        print(f"Data loaded into PostgreSQL table '{table_name}'.")
    except Exception as e:
        logging.error(f"Failed to write to table '{table_name}': {e}")
        print(f"Error loading data into table '{table_name}'.")

#Main Execution
def run_etl_pipeline():
    """Coordinates and executes the full ETL process."""
    setup_logging()
    start_time = time.time()
    logging.info("Starting Yelp ETL pipeline...")

    engine = create_db_engine()
    if not engine:
        print("ETL pipeline aborted.")
        return

    for data_key in DATA_PATHS:
        print(f"\nProcessing '{data_key}' data...")
        
        #EXTRACT
        df = load_json_to_dataframe(data_key)
        if df is None:
            continue

        #TRANSFORM
        sql_table_name = data_key
        if data_key == 'business':
            df.drop(columns=['attributes', 'hours'], errors='ignore', inplace=True)
        elif data_key == 'user':
            df.drop(columns=['compliments'], errors='ignore', inplace=True)
            sql_table_name = 'users'
        
        #LOAD
        load_df_to_postgres(df, sql_table_name, engine)
            
    end_time = time.time()
    total_seconds = end_time - start_time
    minutes, seconds = divmod(total_seconds, 60)

    final_message = (
        f"ETL Process Finished in {int(minutes)} minutes and {seconds:.2f} seconds."
        )
    logging.info(final_message)
    print(final_message)

if __name__ == "__main__":
    run_etl_pipeline()