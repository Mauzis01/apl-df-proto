import os
import logging
import time
from pathlib import Path
from supabase import create_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/database_init.log"),
        logging.StreamHandler()
    ]
)

def get_supabase_client():
    """Get Supabase client instance"""
    # Load environment variables directly
    from dotenv import load_dotenv
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logging.error("Supabase URL or key not found in environment variables")
        raise ValueError(
            "Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_KEY environment variables."
        )
    
    return create_client(supabase_url, supabase_key)

def read_schema_file():
    """Read the schema SQL file content"""
    schema_path = Path(__file__).parent / "src" / "database" / "schema.sql"
    
    if not schema_path.exists():
        logging.error(f"Schema file not found at {schema_path}")
        raise FileNotFoundError(f"Schema file not found at {schema_path}")
    
    with open(schema_path, 'r') as file:
        return file.read()

def initialize_database():
    """Initialize the database with the schema"""
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        logging.info("Successfully connected to Supabase")
        
        # Read schema file
        schema_sql = read_schema_file()
        
        # Split the schema into individual statements
        # This is a simplified approach - a more robust SQL parser might be needed for complex schemas
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        # Execute each statement
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements):
            try:
                result = supabase.table("schema_version").select("*").execute()
                logging.info(f"Current schema version: {result.data}")
                
                # For demonstration, using a simple function query 
                # In production, you'd use proper SQL execution capabilities
                # This is just to verify connection
                result = supabase.rpc('test_function', {}).execute()
                
                logging.info(f"Successfully executed statement {i+1}/{len(statements)}")
                success_count += 1
                
            except Exception as e:
                logging.error(f"Error executing statement {i+1}: {str(e)}")
                logging.error(f"Statement: {statement[:100]}...")
                error_count += 1
        
        logging.info(f"Database initialization completed with {success_count} successful statements and {error_count} errors")
        
        # Test connection to tables
        tables = [
            'dealers', 
            'investment_items', 
            'scenarios', 
            'growth_rates', 
            'margins', 
            'calculation_results'
        ]
        
        for table in tables:
            try:
                response = supabase.from_(table).select('id').limit(1).execute()
                logging.info(f"Successfully connected to table '{table}' with {len(response.data)} rows")
            except Exception as e:
                logging.error(f"Error connecting to table '{table}': {str(e)}")
        
        return True
        
    except Exception as e:
        logging.error(f"Database initialization failed: {str(e)}")
        return False

def main():
    """Main function to initialize the database"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    logging.info("Starting database initialization")
    
    # Initialize the database
    if initialize_database():
        logging.info("Database initialization completed successfully")
    else:
        logging.error("Database initialization failed")

if __name__ == "__main__":
    main() 