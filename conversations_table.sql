-- Create the Conversations table for voicebot data storage
-- Run this script in your MySQL database

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

-- Verify the table was created
DESCRIBE Conversations;

-- Show current record count
SELECT COUNT(*) as total_conversations FROM Conversations;
