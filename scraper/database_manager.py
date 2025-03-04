import logging
import sqlite3
import os


class DatabaseManager:
    logger: logging.Logger

    def __init__(self, logger: logging.Logger):
        self.logger = logger


    def create_database(self):
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                # Table that holds potential jobs that are available
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        jobid TEXT,
                        title TEXT,
                        company TEXT,
                        location TEXT,
                        remote_status TEXT,
                        linkedin_url TEXT
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            self.logger.critical(f"Error creating jobs table: {e}")
            raise e
        
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                # Table that holds employers for a career within a state
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS employers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company TEXT,
                        state TEXT
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            self.logger.critical(f"Error creating employers table: {e}")
            raise e
    

    def add_job(self, jobid: str, title: str, company: str, location: str,
                remote_status: str, linkedin_url: str) -> None:
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO jobs (jobid, title, company, location, remote_status, linkedin_url)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (jobid, title, company, location, remote_status, linkedin_url))
                conn.commit()

            self.logger.info(f'Job Added To DB: {company} - {title} - {location}')
        except sqlite3.Error as e:
            self.logger.critical(f'add_job() error when adding new job to db: {e}')
            raise e
        
    
    def add_employer(self, company: str, state: str) -> None:
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO employers (company, state)
                VALUES (?, ?)
            ''', (company, state))
                conn.commit()

            self.logger.info(f'Employer Added To DB: {company} - {state}')
        except sqlite3.Error as e:
            self.logger.critical(f'add_employer() error when adding new employer to db: {e}')
            raise e


    def search_jobs(self, search_term: str) -> None:
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM jobs
                    WHERE title LIKE ? OR company LIKE ? OR location LIKE ? OR remote_status LIKE ?
                ''', ('%' + search_term + '%', '%' + search_term + '%', '%' + search_term + '%', '%' + search_term + '%'))
                jobs = cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.critical(f'search_jobs() error when searching jobs in db: {e}')
            raise e
           
        if not jobs:
            self.logger.info("No matching jobs found")
        else:
            for job in jobs:
                self.logger.info(job)


    def is_a_new_job(self, jobid: str) -> bool:
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT jobid FROM jobs WHERE jobid = ?', (jobid,))
                job = cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.critical(f"Error verifying if it's a new job in DB: {e}")
            raise e

        return not job
    

    def is_a_new_employer(self, company: str) -> bool:
        try:
            with sqlite3.connect(os.getenv('DATABASE_PATH')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT company FROM employers WHERE company = ?', (company,))
                company = cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.critical(f"Error verifying if it's a new employer in DB: {e}")
            raise e
        
        return not company
