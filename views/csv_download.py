#!/usr/bin/env python3
import os
import csv
import time
import logging
import datetime
from collections import defaultdict

from flask import Blueprint, send_file, abort
import mysql.connector

# Create the blueprint
csv_download_bp = Blueprint('csv_download', __name__)

# Database credentials (adjust or use environment variables as needed)
DB_HOST = os.getenv('DB_HOST', 'campuscloud-public.mdb0002003.db.skysql.net')
DB_USER = os.getenv('DB_USER', 'russell')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Ab4W034#72ecqe')
DB_NAME = os.getenv('DB_NAME', 'mediatechcloud_sdb')
DB_PORT = int(os.getenv('DB_PORT', 5002))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ---------------- Database Functions ---------------- #

def connect_to_db():
    """Establish a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        if connection.is_connected():
            logging.info("Successfully connected to the database.")
        return connection
    except mysql.connector.Error as e:
        logging.error(f"Error connecting to database: {e}")
        return None

def get_current_date():
    """Return the current date in YYYY-MM-DD format."""
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    logging.info(f"Current Date: {current_date}")
    return current_date

def get_term_dates(db, current_date):
    """Fetch the current term's code, start date, and end date based on the current date."""
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT TERMCODE, STARTDATE, ENDDATE
        FROM termlist
        WHERE ENDDATE >= %s AND STARTDATE <= %s AND ACTIVE = 1
        LIMIT 1;
        '''
        cursor.execute(query, (current_date, current_date))
        result = cursor.fetchone()
        if result:
            return result[0], result[1], result[2]
        else:
            logging.warning("No active term found.")
            return None, None, None
    except mysql.connector.Error as e:
        logging.error(f"Error in get_term_dates: {e}")
        return None, None, None
    finally:
        cursor.close()

def get_enrollments(db):
    """Fetch the most recent enrollment for each student with statuses ('C','P','W','X') and type 'E'."""
    cursor = db.cursor(buffered=True)
    try:
        query = """
        SELECT e.ID, e.STARTDATE, e.PROGRAM, e.STATUS, e.ENROLLMENTNUMBER
        FROM enrollments e
        JOIN (
            SELECT ID, MAX(ENROLLMENTNUMBER) AS maxEnroll
            FROM enrollments
            WHERE STATUS IN ("C", "P", "W", "X") AND TYPE = 'E'
            GROUP BY ID
        ) latest ON e.ID = latest.ID AND e.ENROLLMENTNUMBER = latest.maxEnroll
        WHERE e.STATUS IN ("C", "P", "W", "X");
        """
        cursor.execute(query)
        results = cursor.fetchall()
        enrollments = [
            {'student_id': row[0],
             'start_date': row[1],
             'program': row[2],
             'status': row[3],
             'enrollment_number': row[4]}
            for row in results
        ]
        logging.info(f"Number of most recent enrollments found: {len(enrollments)}")
        return enrollments
    except mysql.connector.Error as e:
        logging.error(f"Error in get_enrollments: {e}")
        return []
    finally:
        cursor.close()

# ---------------- CSV Generation Function ---------------- #

def run_csv_check():
    """
    Connect to the database, run the necessary queries, generate the main CSV file,
    and return True if successful.
    """
    db = connect_to_db()
    if not db:
        return False
    try:
        current_date = get_current_date()
        term_code, term_start_date, term_end_date = get_term_dates(db, current_date)
        if not term_start_date or not term_end_date:
            logging.warning("No active term found. Exiting...")
            return False
        enrollments = get_enrollments(db)
        enrollments = sorted(enrollments, key=lambda x: x['student_id'])
        csv_file = "student_funds.csv"
        
        with open(csv_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            # For demonstration, only a few columns are written.
            header = [
                "Student ID",
                "Program",
                "Start Date",
                "Term Code",
                "Status"
            ]
            writer.writerow(header)
            
            total_records = len(enrollments)
            processed_count = 0
            for enrollment in enrollments:
                row = [
                    enrollment['student_id'],
                    enrollment['program'],
                    enrollment['start_date'],
                    term_code,
                    enrollment['status']
                ]
                writer.writerow(row)
                processed_count += 1
                percent_complete = int((processed_count / total_records) * 100)
                print(f"Processing record {processed_count} of {total_records} ({percent_complete}%)")
                time.sleep(0.1)
                
            logging.info(f"CSV file '{csv_file}' created successfully with {processed_count} records.")
        return True
    except Exception as e:
        logging.error(f"An error occurred in run_csv_check: {e}")
        return False
    finally:
        db.close()
        logging.info("Database connection closed.")

# ---------------- Blueprint Routes ---------------- #

@csv_download_bp.route('/download_csv', methods=['GET'])
def download_csv():
    if run_csv_check():
        try:
            return send_file("/tmp/student_funds.csv",
                             mimetype="text/csv",
                             attachment_filename="student_funds.csv",
                             as_attachment=True)
        except Exception as e:
            logging.error(f"Error sending file: {e}")
            abort(500)
    else:
        abort(500)