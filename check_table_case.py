#!/usr/bin/env python3
"""
Table Case Sensitivity Check Script

This script checks the exact case of your table names and helps fix case sensitivity issues.
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

def check_mysql_case_sensitivity():
    """Check MySQL case sensitivity settings."""
    try:
        print("🔍 Checking MySQL case sensitivity settings...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            # Check lower_case_table_names setting
            result = connection.execute(text("SHOW VARIABLES LIKE 'lower_case_table_names'"))
            setting = result.fetchone()
            
            if setting:
                value = setting[1]
                print(f"lower_case_table_names = {value}")
                
                if value == '0':
                    print("✅ Case sensitive - table names must match exactly")
                elif value == '1':
                    print("✅ Case insensitive - table names can be any case")
                elif value == '2':
                    print("✅ Case sensitive but stored in lowercase")
                
                return int(value)
            else:
                print("❌ Could not determine case sensitivity setting")
                return None
                
    except Exception as e:
        print(f"❌ Error checking case sensitivity: {e}")
        return None

def list_all_tables_exact_case():
    """List all tables with their exact case."""
    try:
        print("\n📋 Listing all tables with exact case...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            # Get current database
            result = connection.execute(text("SELECT DATABASE()"))
            current_db = result.fetchone()[0]
            print(f"Current database: {current_db}")
            
            # List all tables
            result = connection.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            
            print(f"\nTables in '{current_db}':")
            for table in tables:
                print(f"  - '{table}'")
                
            # Check for conversations table variations
            conversations_variations = [t for t in tables if 'conversation' in t.lower()]
            if conversations_variations:
                print(f"\n🔍 Found conversation-related tables:")
                for table in conversations_variations:
                    print(f"  - '{table}' (exact case)")
                    
                return conversations_variations
            else:
                print(f"\n❌ No conversation-related tables found")
                return []
                
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
        return []

def test_table_access(table_name):
    """Test accessing a table with specific case."""
    try:
        print(f"\n🧪 Testing access to table '{table_name}'...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            # Try to describe the table
            result = connection.execute(text(f"DESCRIBE `{table_name}`"))
            columns = result.fetchall()
            
            print(f"✅ Successfully accessed '{table_name}'")
            print(f"Columns in '{table_name}':")
            for column in columns:
                print(f"  - {column[0]} ({column[1]})")
                
            return True, columns
            
    except Exception as e:
        print(f"❌ Cannot access '{table_name}': {e}")
        return False, []

def create_table_with_correct_case():
    """Create the Conversations table with the exact case expected by the code."""
    try:
        print("\n🔧 Creating 'Conversations' table with exact case...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS `Conversations` (
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            connection.execute(text(create_table_sql))
            connection.commit()
            
            print("✅ 'Conversations' table created successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False

def test_insert_with_exact_case():
    """Test inserting with the exact table name case."""
    try:
        print("\n🧪 Testing insert with exact case 'Conversations'...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            test_data = {
                'Conversation': 'Test conversation',
                'User_ID': 1,
                'Store_ID': 1,
                'Session_ID': 'test_case_sensitivity',
                'Session_Time': '2024-01-01 12:00:00',
                'Duration_of_Call': 60,
                'Call_Reason': 'General inquiry',
                'Escalation': False,
                'Query_Type': None
            }
            
            insert_query = """
            INSERT INTO `Conversations`
                (Conversation, User_ID, Store_ID, Session_ID, Session_Time,
                 Duration_of_Call, Call_Reason, Escalation, Query_Type)
            VALUES
                (:Conversation, :User_ID, :Store_ID, :Session_ID, :Session_Time,
                 :Duration_of_Call, :Call_Reason, :Escalation, :Query_Type)
            """
            
            connection.execute(text(insert_query), test_data)
            connection.commit()
            
            print("✅ Insert successful with exact case!")
            
            # Clean up
            connection.execute(text("DELETE FROM `Conversations` WHERE Session_ID = 'test_case_sensitivity'"))
            connection.commit()
            print("🧹 Test record cleaned up")
            
            return True
            
    except Exception as e:
        print(f"❌ Insert failed: {e}")
        return False

def main():
    """Main function to check and fix table case sensitivity issues."""
    print("🔍 Table Case Sensitivity Diagnostic")
    print("=" * 50)
    
    # Check MySQL case sensitivity
    case_setting = check_mysql_case_sensitivity()
    
    # List all tables with exact case
    existing_tables = list_all_tables_exact_case()
    
    # Check if we have any conversation tables
    if existing_tables:
        print(f"\n🔍 Found existing conversation tables:")
        for table in existing_tables:
            success, columns = test_table_access(table)
            if success:
                print(f"✅ '{table}' is accessible")
            else:
                print(f"❌ '{table}' is not accessible")
    
    # Check if 'Conversations' (exact case) exists
    if 'Conversations' in existing_tables:
        print(f"\n✅ 'Conversations' table exists with correct case!")
        test_insert_with_exact_case()
    else:
        print(f"\n❌ 'Conversations' table does not exist with exact case")
        print("🔧 Creating 'Conversations' table...")
        
        if create_table_with_correct_case():
            test_insert_with_exact_case()
        else:
            print("❌ Failed to create table")
    
    print(f"\n💡 Summary:")
    print(f"   - MySQL case sensitivity: {'Enabled' if case_setting == 0 else 'Disabled'}")
    print(f"   - Your code expects: 'Conversations' (capital C)")
    print(f"   - Existing tables: {existing_tables}")
    
    if case_setting == 0:
        print(f"\n⚠️  Your MySQL is case sensitive!")
        print(f"   Make sure your table name exactly matches 'Conversations'")

if __name__ == "__main__":
    main()
