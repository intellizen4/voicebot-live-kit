#!/usr/bin/env python3
"""
Database Table Check Script

This script checks the existing Conversations table structure and identifies any issues.
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

def check_table_structure():
    """Check the current Conversations table structure."""
    try:
        print("🔍 Checking Conversations table structure...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            # Get table structure
            result = connection.execute(text("DESCRIBE Conversations"))
            columns = result.fetchall()
            
            print("\n📊 Current table structure:")
            print(f"{'Field':<20} {'Type':<20} {'Null':<5} {'Key':<5} {'Default':<15} {'Extra'}")
            print("-" * 80)
            
            existing_columns = []
            for column in columns:
                field, type_, null, key, default, extra = column
                existing_columns.append(field)
                default_str = str(default) if default is not None else "NULL"
                print(f"{field:<20} {type_:<20} {null:<5} {key:<5} {default_str:<15} {extra}")
            
            # Check for required columns
            required_columns = [
                'Conversation', 'User_ID', 'Store_ID', 'Session_ID', 
                'Session_Time', 'Duration_of_Call', 'Call_Reason', 
                'Escalation', 'Query_Type'
            ]
            
            print(f"\n🔍 Checking for required columns...")
            missing_columns = []
            for col in required_columns:
                if col in existing_columns:
                    print(f"✅ {col}")
                else:
                    print(f"❌ {col} - MISSING")
                    missing_columns.append(col)
            
            if missing_columns:
                print(f"\n⚠️  Missing columns: {missing_columns}")
                return False, missing_columns
            else:
                print(f"\n✅ All required columns are present!")
                return True, []
                
    except Exception as e:
        print(f"❌ Error checking table structure: {e}")
        return False, []

def test_insert():
    """Test inserting a sample record to identify the exact error."""
    try:
        print("\n🧪 Testing database insert...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            # Test data matching the voicebot's insert format
            test_data = {
                'Conversation': 'Test conversation',
                'User_ID': 1,
                'Store_ID': 1,
                'Session_ID': 'test_session_123',
                'Session_Time': '2024-01-01 12:00:00',
                'Duration_of_Call': 60,
                'Call_Reason': 'Test call',
                'Escalation': False,
                'Query_Type': 'test'
            }
            
            # Try the exact insert query from the voicebot
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
            
            print("✅ Test insert successful!")
            
            # Clean up test record
            connection.execute(text("DELETE FROM Conversations WHERE Session_ID = 'test_session_123'"))
            connection.commit()
            print("🧹 Test record cleaned up")
            
            return True
            
    except Exception as e:
        print(f"❌ Test insert failed: {e}")
        return False

def fix_missing_columns(missing_columns):
    """Add missing columns to the existing table."""
    try:
        print(f"\n🔧 Adding missing columns...")
        engine = connect_with_connector()
        
        column_definitions = {
            'Conversation': 'TEXT',
            'User_ID': 'INT',
            'Store_ID': 'INT', 
            'Session_ID': 'VARCHAR(255)',
            'Session_Time': 'DATETIME',
            'Duration_of_Call': 'INT',
            'Call_Reason': 'VARCHAR(255)',
            'Escalation': 'BOOLEAN DEFAULT FALSE',
            'Query_Type': 'VARCHAR(255)'
        }
        
        with engine.connect() as connection:
            for column in missing_columns:
                if column in column_definitions:
                    alter_sql = f"ALTER TABLE Conversations ADD COLUMN {column} {column_definitions[column]}"
                    print(f"Adding column: {column}")
                    connection.execute(text(alter_sql))
            
            connection.commit()
            print("✅ Missing columns added successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error adding columns: {e}")
        return False

def show_sample_records():
    """Show existing records in the table."""
    try:
        print("\n📋 Sample records from Conversations table:")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT COUNT(*) as count FROM Conversations"))
            count = result.fetchone()[0]
            print(f"Total records: {count}")
            
            if count > 0:
                result = connection.execute(text("SELECT * FROM Conversations ORDER BY id DESC LIMIT 3"))
                records = result.fetchall()
                
                for record in records:
                    print(f"\nRecord ID: {record[0]}")
                    print(f"Session ID: {record[4] if len(record) > 4 else 'N/A'}")
                    print(f"User ID: {record[2] if len(record) > 2 else 'N/A'}")
                    print(f"Store ID: {record[3] if len(record) > 3 else 'N/A'}")
                    print("-" * 40)
                    
    except Exception as e:
        print(f"❌ Error showing records: {e}")

def main():
    """Main function to diagnose and fix the database table."""
    print("🔍 Database Table Diagnostic Tool")
    print("=" * 50)
    
    try:
        # Check table structure
        structure_ok, missing_columns = check_table_structure()
        
        if not structure_ok and missing_columns:
            print(f"\n🔧 Found missing columns. Attempting to fix...")
            if fix_missing_columns(missing_columns):
                print("✅ Table structure fixed!")
                # Re-check structure
                structure_ok, _ = check_table_structure()
            else:
                print("❌ Could not fix table structure automatically.")
                print("💡 You may need to manually add the missing columns.")
        
        if structure_ok:
            # Test the insert operation
            if test_insert():
                print("\n🎉 Database table is working correctly!")
                print("✅ Your voicebot should be able to save conversations.")
            else:
                print("\n⚠️  Table structure looks correct but insert test failed.")
                print("💡 There might be a data type or constraint issue.")
        
        # Show sample records
        show_sample_records()
        
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")
        print("\n💡 Make sure your database connection settings are correct.")

if __name__ == "__main__":
    main()
