#!/usr/bin/env python
"""
PostgreSQL Database Creation Script for Novel Web Scraper
Creates a PostgreSQL database and user for the novel web scraper project.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


def get_db_config():
    """
    Get database configuration from environment variables or defaults.
    
    Returns:
        dict: Database configuration
    """
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "user": os.getenv("DB_ADMIN_USER", "postgres"),
        "password": os.getenv("DB_ADMIN_PASSWORD", "postgres"),
        "database": os.getenv("DB_NAME", "novel_scraper_db"),
        "db_user": os.getenv("DB_USER", "scraper_user"),
        "db_password": os.getenv("DB_PASSWORD", "scraper_secure_password"),
    }


def create_tables(cursor):
    """
    Create all necessary tables for the novel scraper project.
    
    Args:
        cursor: PostgreSQL cursor object
    """
    
    # Create ENUM types
    cursor.execute("""
        DO $$ BEGIN
            CREATE TYPE source_type AS ENUM ('AO3', 'FanFictionNet', 'Kemono', 'NovelBin');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    
    cursor.execute("""
        DO $$ BEGIN
            CREATE TYPE scrape_status AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'paused');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create Sources table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id SERIAL PRIMARY KEY,
            name source_type NOT NULL UNIQUE,
            url VARCHAR(500) NOT NULL,
            description TEXT,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✓ Created 'sources' table")
    
    # Create Authors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authors (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            source_author_id VARCHAR(255),
            url VARCHAR(500),
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_id, source_author_id)
        );
    """)
    print("✓ Created 'authors' table")
    
    # Create Novels/Stories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS novels (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            author_id INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
            source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            source_novel_id VARCHAR(255),
            description TEXT,
            url VARCHAR(500),
            status VARCHAR(50) DEFAULT 'ongoing',
            rating DECIMAL(3, 2),
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            language VARCHAR(50) DEFAULT 'English',
            publication_date DATE,
            last_updated DATE,
            cover_url VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_id, source_novel_id)
        );
    """)
    print("✓ Created 'novels' table")
    
    # Create Chapters table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chapters (
            id SERIAL PRIMARY KEY,
            novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
            chapter_number INTEGER NOT NULL,
            title VARCHAR(500),
            url VARCHAR(500),
            content TEXT,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            published_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(novel_id)
        );
    """)
    print("✓ Created 'chapters' table")
    
    # Create Categories/Tags table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✓ Created 'tags' table")
    
    # Create Novel-Tags junction table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS novel_tags (
            novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (novel_id, tag_id)
        );
    """)
    print("✓ Created 'novel_tags' table")
    
    # Create Scrape History/Logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scrape_logs (
            id SERIAL PRIMARY KEY,
            source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            novel_id INTEGER REFERENCES novels(id) ON DELETE SET NULL,
            status scrape_status DEFAULT 'pending',
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            chapters_scraped INTEGER DEFAULT 0,
            error_message TEXT,
            success BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✓ Created 'scrape_logs' table")
    
    # Create Favorites/Bookmarks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id SERIAL PRIMARY KEY,
            novel_id INTEGER NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
            bookmark_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✓ Created 'bookmarks' table")
    
    # Create Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_novels_source_id ON novels(source_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_novels_author_id ON novels(author_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chapters_novel_id ON chapters(novel_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scrape_logs_source_id ON scrape_logs(source_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scrape_logs_novel_id ON scrape_logs(novel_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_novels_title ON novels(title);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_authors_name ON authors(name);")
    print("✓ Created indexes")


def create_database():
    """
    Create PostgreSQL database and user for the novel scraper project.
    """
    config = get_db_config()
    
    try:
        # Connect to PostgreSQL server with admin credentials
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database="postgres",  # Connect to default postgres database
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print(f"✓ Connected to PostgreSQL at {config['host']}:{config['port']}")
        
        # Check if database already exists
        cursor.execute(
            sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"),
            [config["database"]],
        )
        
        if cursor.fetchone():
            print(f"⚠ Database '{config['database']}' already exists")
            db_exists = True
        else:
            # Create database
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(config["database"])
                )
            )
            print(f"✓ Database '{config['database']}' created successfully")
            db_exists = False
        
        # Check if user already exists
        cursor.execute(
            sql.SQL("SELECT 1 FROM pg_user WHERE usename = %s"),
            [config["db_user"]],
        )
        
        if cursor.fetchone():
            print(f"⚠ User '{config['db_user']}' already exists")
        else:
            # Create user/role
            cursor.execute(
                sql.SQL("CREATE USER {} WITH PASSWORD %s").format(
                    sql.Identifier(config["db_user"])
                ),
                [config["db_password"]],
            )
            print(f"✓ User '{config['db_user']}' created successfully")
        
        # Grant privileges to user on database
        cursor.execute(
            sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                sql.Identifier(config["database"]),
                sql.Identifier(config["db_user"]),
            )
        )
        print(f"✓ Privileges granted to '{config['db_user']}' on '{config['database']}'")
        
        # Grant schema privileges
        cursor.execute(
            sql.SQL("GRANT ALL PRIVILEGES ON SCHEMA public TO {}").format(
                sql.Identifier(config["db_user"])
            ),
        )
        cursor.execute(
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {}").format(
                sql.Identifier(config["db_user"])
            ),
        )
        cursor.execute(
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {}").format(
                sql.Identifier(config["db_user"])
            ),
        )
        print(f"✓ Schema privileges granted")
        
        cursor.close()
        conn.close()
        
        # Connect to the new database to create tables
        print("\n" + "=" * 60)
        print("Creating Tables...")
        print("=" * 60)
        
        conn = psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["db_user"],
            password=config["db_password"],
            database=config["database"],
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        create_tables(cursor)
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Database setup completed successfully!")
        print("=" * 60)
        print("\nDatabase Configuration:")
        print(f"  Host: {config['host']}")
        print(f"  Port: {config['port']}")
        print(f"  Database: {config['database']}")
        print(f"  User: {config['db_user']}")
        print("\nConnection String (for reference):")
        print(f"  postgresql://{config['db_user']}:{config['db_password']}@{config['host']}:{config['port']}/{config['database']}")
        print("\nTables Created:")
        print("  - sources (source types and URLs)")
        print("  - authors (novel authors)")
        print("  - novels (main stories/novels)")
        print("  - chapters (individual chapters)")
        print("  - tags (story categories/tags)")
        print("  - novel_tags (novel-tag relationships)")
        print("  - scrape_logs (scraping history)")
        print("  - bookmarks (user bookmarks/favorites)")
        
        return True
        
    except psycopg2.Error as e:
        print(f"✗ PostgreSQL Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def main():
    """Main entry point."""
    print("=" * 60)
    print("PostgreSQL Database Setup for Novel Web Scraper")
    print("=" * 60)
    print()
    
    success = create_database()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
