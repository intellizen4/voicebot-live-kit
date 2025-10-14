#!/usr/bin/env python3
"""
Database Issue Fix Script

This script helps identify and fix database connection and table issues.
"""

import sqlalchemy
import pymysql
import os
from google.cloud.sql.connector import Connector, IPTypes
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    """Create a connection pool to a Cloud SQL instance."""
    instance_connection_name = os.environ.get('SQL_INSTANCE', 'YOUR_SQL_INSTANCE')
    db_user = os.environ.get('DB_USER', 'USER_NAME')
    db_pass = os.environ.get('DB_PASS', 'PASSWORD')
    db_name = os.environ.get('DB_NAME', 'DB_NAME')
    ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC
    
    connector = Connector(ip_type)
    
    def getconn() -> pymysql.connections.Connection:
        conn: pymysql.connections.Connection = connector.connect(
            instance_connection_name,
            "pymysql",
            user=db_user,
            password=db_pass,
            db=db_name,
        )
        return conn
    
    pool = sqlalchemy.create_engine("mysql+pymysql://", creator=getconn)
    return pool

def check_database_connection():
    """Check database connection and show current database."""
    try:
        print("🔗 Checking database connection...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            # Get current database
            result = connection.execute(text("SELECT DATABASE()"))
            current_db = result.fetchone()[0]
            print(f"✅ Connected to database: {current_db}")
            
            # Show all databases
            result = connection.execute(text("SHOW DATABASES"))
            databases = [row[0] for row in result.fetchall()]
            print(f"📊 Available databases: {databases}")
            
            # Check if 'Intellizen' database exists
            if 'Intellizen' in databases:
                print("✅ 'Intellizen' database exists")
            else:
                print("❌ 'Intellizen' database does not exist")
                print("💡 This might be the issue - the code expects 'Intellizen' database")
            
            return current_db, databases
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None, []

def check_conversations_table_in_database(db_name):
    """Check if Conversations table exists in a specific database."""
    try:
        print(f"\n🔍 Checking Conversations table in database '{db_name}'...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            # Switch to the database
            connection.execute(text(f"USE {db_name}"))
            
            # Check if table exists
            result = connection.execute(text("SHOW TABLES LIKE 'Conversations'"))
            tables = result.fetchall()
            
            if tables:
                print(f"✅ Conversations table exists in '{db_name}' database")
                
                # Show table structure
                result = connection.execute(text("DESCRIBE Conversations"))
                columns = result.fetchall()
                
                print(f"\n📋 Table structure in '{db_name}':")
                print(f"{'Field':<20} {'Type':<20} {'Null':<5} {'Key':<5}")
                print("-" * 60)
                for column in columns:
                    field, type_, null, key, default, extra = column
                    print(f"{field:<20} {type_:<20} {null:<5} {key:<5}")
                
                return True, columns
            else:
                print(f"❌ Conversations table does not exist in '{db_name}' database")
                return False, []
                
    except Exception as e:
        print(f"❌ Error checking table in '{db_name}': {e}")
        return False, []

def create_conversations_table_in_intellizen():
    """Create Conversations table in the Intellizen database."""
    try:
        print("\n🔧 Creating Conversations table in 'Intellizen' database...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            # Switch to Intellizen database
            connection.execute(text("USE Intellizen"))
            
            # Create table SQL
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS Conversations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                Conversation TEXT,
                User_ID INT,
                Store_ID INT,
                Session_ID VARCHAR(255),
                Session_Time DATETIME,
                Duration_of_Call INT,
                Call_Reason VARCHAR(255),
                Escalation BOOLEAN DEFAULT FALSE,
                Query_Type VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_session_id (Session_ID),
                INDEX idx_user_id (User_ID),
                INDEX idx_store_id (Store_ID),
                INDEX idx_session_time (Session_Time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            connection.execute(text(create_table_sql))
            connection.commit()
            
            print("✅ Conversations table created in 'Intellizen' database!")
            return True
            
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False

def test_insert_in_intellizen():
    """Test inserting a record in the Intellizen database."""
    try:
        print("\n🧪 Testing insert in 'Intellizen' database...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            connection.execute(text("USE Intellizen"))
            
            # Test data
            test_data = {
                'Conversation': 'Test conversation',
                'User_ID': 1,
                'Store_ID': 1,
                'Session_ID': 'test_session_intellizen',
                'Session_Time': '2024-01-01 12:00:00',
                'Duration_of_Call': 60,
                'Call_Reason': 'General inquiry',
                'Escalation': False,
                'Query_Type': None
            }
            
            insert_query = """
            INSERT INTO Conversations
                (Conversation, User_ID, Store_ID, Session_ID, Session_Time,
                 Duration_of_Call, Call_Reason, Escalation, Query_Type)
            VALUES
                (:Conversation, :User_ID, :Store_ID, :Session_ID, :Session_Time,
                 :Duration_of_Call, :Call_Reason, :Escalation, :Query_Type)
            """
            
            result = connection.execute(text(insert_query), test_data)
            connection.commit()
            
            print("✅ Test insert successful in 'Intellizen' database!")
            
            # Clean up test record
            connection.execute(text("DELETE FROM Conversations WHERE Session_ID = 'test_session_intellizen'"))
            connection.commit()
            print("🧹 Test record cleaned up")
            
            return True
            
    except Exception as e:
        print(f"❌ Test insert failed: {e}")
        return False

def fix_environment_variables():
    """Help fix environment variables if needed."""
    print("\n🔧 Environment Variable Check:")
    print("=" * 40)
    
    db_name = os.environ.get('DB_NAME', 'NOT_SET')
    sql_instance = os.environ.get('SQL_INSTANCE', 'NOT_SET')
    db_user = os.environ.get('DB_USER', 'NOT_SET')
    db_pass = os.environ.get('DB_PASS', 'NOT_SET')
    
    print(f"DB_NAME: {db_name}")
    print(f"SQL_INSTANCE: {sql_instance}")
    print(f"DB_USER: {db_user}")
    print(f"DB_PASS: {'*' * len(db_pass) if db_pass != 'NOT_SET' else 'NOT_SET'}")
    
    if db_name != 'Intellizen':
        print(f"\n⚠️  Your DB_NAME is '{db_name}' but the error shows 'Intellizen'")
        print("💡 You might need to update your DB_NAME environment variable")
        print("   or create the table in the correct database.")

def main():
    """Main function to diagnose and fix the database issue."""
    print("🔍 Database Issue Diagnostic Tool")
    print("=" * 50)
    
    # Check environment variables
    fix_environment_variables()
    
    # Check database connection
    current_db, databases = check_database_connection()
    
    if not current_db:
        print("\n❌ Cannot proceed without database connection.")
        return
    
    # Check if Conversations table exists in current database
    table_exists, columns = check_conversations_table_in_database(current_db)
    
    # Check if Conversations table exists in Intellizen database
    if 'Intellizen' in databases:
        intellizen_table_exists, intellizen_columns = check_conversations_table_in_database('Intellizen')
        
        if not intellizen_table_exists:
            print("\n🔧 Creating Conversations table in 'Intellizen' database...")
            if create_conversations_table_in_intellizen():
                # Test the insert
                test_insert_in_intellizen()
            else:
                print("❌ Failed to create table in 'Intellizen' database")
        else:
            print("\n✅ Conversations table exists in 'Intellizen' database")
            # Test insert anyway
            test_insert_in_intellizen()
    else:
        print("\n❌ 'Intellizen' database does not exist!")
        print("💡 Solutions:")
        print("   1. Create the 'Intellizen' database")
        print("   2. Update your DB_NAME environment variable")
        print("   3. Create the Conversations table in your current database")
        
        # Ask user what they want to do
        choice = input("\nDo you want to create the 'Intellizen' database? (y/N): ").strip().lower()
        if choice == 'y':
            try:
                engine = connect_with_connector()
                with engine.connect() as connection:
                    connection.execute(text("CREATE DATABASE IF NOT EXISTS Intellizen"))
                    connection.commit()
                print("✅ 'Intellizen' database created!")
                
                # Now create the table
                if create_conversations_table_in_intellizen():
                    test_insert_in_intellizen()
                    
            except Exception as e:
                print(f"❌ Error creating database: {e}")

if __name__ == "__main__":
    main()
