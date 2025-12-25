"""
Initialize PostgreSQL database for APDS.
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "apds")
POSTGRES_USER = os.getenv("POSTGRES_USER", "apds_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme_in_production")


def init_database():
    """Initialize database tables."""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        
        cursor = conn.cursor()
        
        # Create threat_classifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threat_classifications (
                id SERIAL PRIMARY KEY,
                detection_id VARCHAR(255) UNIQUE NOT NULL,
                camera_id VARCHAR(255) NOT NULL,
                threat_score FLOAT NOT NULL,
                threat_category VARCHAR(50) NOT NULL,
                confidence FLOAT NOT NULL,
                features JSONB,
                explanation TEXT,
                timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_detection_id ON threat_classifications(detection_id);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON threat_classifications(timestamp);
            CREATE INDEX IF NOT EXISTS idx_threat_score ON threat_classifications(threat_score);
        """)
        
        # Create alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                alert_id VARCHAR(255) UNIQUE NOT NULL,
                detection_id VARCHAR(255) NOT NULL,
                threat_score FLOAT NOT NULL,
                threat_category VARCHAR(50) NOT NULL,
                explanation TEXT,
                timestamp TIMESTAMP NOT NULL,
                acknowledged BOOLEAN DEFAULT FALSE,
                acknowledged_by VARCHAR(255),
                acknowledged_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_id ON alerts(alert_id);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON alerts(timestamp);
            CREATE INDEX IF NOT EXISTS idx_acknowledged ON alerts(acknowledged);
            CREATE INDEX IF NOT EXISTS idx_threat_category ON alerts(threat_category);
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✓ Database initialized successfully")
        return True
    
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    print("Initializing APDS database...")
    print(f"Host: {POSTGRES_HOST}:{POSTGRES_PORT}")
    print(f"Database: {POSTGRES_DB}")
    print(f"User: {POSTGRES_USER}\n")
    
    if init_database():
        print("\n✓ Database setup complete!")
    else:
        print("\n✗ Database setup failed!")
        exit(1)

