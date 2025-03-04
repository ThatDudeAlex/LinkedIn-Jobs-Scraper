import logging
import sqlite3
import os


class DatabaseManager:
    """
    Handles the creation of the `jobs` and `employers` tables. 
    Also handles the insertion and lookup of database entities
    """

    logger: logging.Logger

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.db_path = os.getenv('DATABASE_PATH')
        self.conn = None
        self.cursor = None
        self.connect()
        self.setup_database()
    

    def connect(self):
        """Establish a persistent database connection"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.logger.info("✅ Database connected successfully")
        except sqlite3.Error as e:
            self.logger.critical(f"❌ Database connection failed: {e}")
            raise e


    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            self.logger.info("✅ Database connection closed")


    def _execute_query(self, query, params=()):
        """Execute a SQL query and commits it"""
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.critical(f"❌ Database commit query failed: {e}")
            raise e


    def _fetch_query(self, query, params=()):
        """Fetch results from a SQL query"""
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.critical(f"❌ Database fetch query failed: {e}")
            raise e


    def setup_database(self):
        create_jobs_query = '''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jobid TEXT UNIQUE,
                title TEXT,
                company TEXT,
                location TEXT,
                remote_status TEXT,
                linkedin_url TEXT
            );
        ''' 

        create_employers_query = '''
            CREATE TABLE IF NOT EXISTS employers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT UNIQUE,
                state TEXT
            );
        '''

        try:
            self._execute_query(create_jobs_query)
        except Exception as e:
            self.logger.critical(f"❌ Error creating jobs table")
            raise e

        try:
            self._execute_query(create_employers_query)
        except Exception as e:
            self.logger.critical(f"❌ Error creating employers table")
            raise e
        
        self.logger.info("✅ Database setup successful")


    def add_job(self, jobid: str, title: str, company: str, location: str,
                remote_status: str, linkedin_url: str) -> None:
        """
        Adds a new job entity into the `jobs` table
        """
        try:
            if not jobid or not company or not title:
                self.logger.critical(f"❌ Skipping: can't insert job, is missing either {company} or {title}")
                return

            self._execute_query('''
                INSERT OR IGNORE INTO jobs (jobid, title, company, location, remote_status, linkedin_url)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (jobid, title, company, location, remote_status, linkedin_url))

            self.logger.info(f"✅ Job Added To DB: {company} - {title} - {location}")
        except sqlite3.Error as e:
            self.logger.critical(f"❌ Skipping: error when adding new job to db: {e}")
        
    
    def add_employer(self, company: str, state: str) -> None:
        """
        Adds a new employer entity into the `employers` table
        """
        try:
            if not company or not state:
                self.logger.critical(f"❌ Skipping: can't insert employer, is missing either {company} or {state}")
                return
            
            self._execute_query('''
                INSERT OR IGNORE INTO employers (company, state)
                VALUES (?, ?)
            ''', (company, state))

            self.logger.info(f'✅ Employer Added To DB: {company} - {state}')
        except sqlite3.Error as e:
            self.logger.critical(f"❌ Skipping: error when adding new employer to db: {e}")


    def search_jobs(self, search_term: str) -> None:
        """
        Logs all jobs that contain the `search_term` in any of it's fields
        """
        jobs = self._fetch_query('''
                    SELECT * FROM jobs
                    WHERE title LIKE ? OR company LIKE ? OR location LIKE ? OR remote_status LIKE ?
                ''', tuple(['%' + search_term + '%'] * 4))
        
        if not jobs:
            self.logger.info("No matching jobs found")
        else:
            for job in jobs:
                self.logger.info(job)


    def is_a_new_job(self, jobid: str) -> bool:
        """
        Returns if `jobid` is not found in the `jobs` table
        """
        try:
                self.cursor.execute('SELECT jobid FROM jobs WHERE jobid = ?', (jobid,))
                job = self.cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.critical(f"Error verifying if it's a new job in DB: {e}")
            raise e

        return not job


