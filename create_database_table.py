#!/usr/bin/env python3
"""
Database Table Creation Script

This script creates the required Conversations table for storing voicebot conversation data.
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

def create_conversations_table():
    """Create the Conversations table with the required schema."""
    
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
    
    try:
        # Initialize database connection
        print("🔗 Connecting to database...")
        engine = connect_with_connector()
        
        # Test connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        
        # Create the table
        print("📋 Creating Conversations table...")
        with engine.connect() as connection:
            connection.execute(text(create_table_sql))
            connection.commit()
        
        print("✅ Conversations table created successfully!")
        
        # Verify table exists and show structure
        print("\n📊 Table structure:")
        with engine.connect() as connection:
            result = connection.execute(text("DESCRIBE Conversations"))
            columns = result.fetchall()
            
            print(f"{'Field':<20} {'Type':<20} {'Null':<5} {'Key':<5} {'Default':<15} {'Extra'}")
            print("-" * 80)
            for column in columns:
                field, type_, null, key, default, extra = column
                default_str = str(default) if default is not None else "NULL"
                print(f"{field:<20} {type_:<20} {null:<5} {key:<5} {default_str:<15} {extra}")
        
        # Check if table has any data
        with engine.connect() as connection:
            result = connection.execute(text("SELECT COUNT(*) as count FROM Conversations"))
            count = result.fetchone()[0]
            print(f"\n📈 Current records in Conversations table: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False

def create_alternative_simple_table():
    """Create a simplified version of the Conversations table if the full version fails."""
    
    simple_table_sql = """
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        print("🔧 Trying simplified table creation...")
        engine = connect_with_connector()
        
        with engine.connect() as connection:
            connection.execute(text(simple_table_sql))
            connection.commit()
        
        print("✅ Simplified Conversations table created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating simplified table: {e}")
        return False

def check_database_connection():
    """Check if we can connect to the database."""
    try:
        engine = connect_with_connector()
        with engine.connect() as connection:
            result = connection.execute(text("SELECT DATABASE()"))
            current_db = result.fetchone()[0]
            print(f"✅ Connected to database: {current_db}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n💡 Make sure your environment variables are set correctly:")
        print("   - SQL_INSTANCE")
        print("   - DB_USER") 
        print("   - DB_PASS")
        print("   - DB_NAME")
        return False

def main():
    """Main function to create the database table."""
    print("🗄️  Voicebot Database Setup")
    print("=" * 50)
    
    # Check database connection first
    if not check_database_connection():
        print("\n❌ Cannot proceed without database connection.")
        return
    
    # Try to create the full table
    if create_conversations_table():
        print("\n🎉 Database setup completed successfully!")
        print("\nYour voicebot can now save conversation data to the database.")
    else:
        print("\n⚠️  Full table creation failed, trying simplified version...")
        if create_alternative_simple_table():
            print("\n✅ Simplified table created. Your voicebot should work now.")
        else:
            print("\n❌ Failed to create any table. Please check your database permissions.")
            print("\n💡 You can also create the table manually using this SQL:")
            print("""
CREATE TABLE Conversations (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
            """)

if __name__ == "__main__":
    main()
