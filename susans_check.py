import streamlit as st
import mysql.connector
from datetime import datetime
import csv
import logging
import os
from collections import defaultdict
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("student_funds.log"),
        logging.StreamHandler()
    ]
)

# Database connection function
def connect_to_db():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'campuscloud-public.mdb0002003.db.skysql.net'),
            user=os.getenv('DB_USER', 'russell'),
            password=os.getenv('DB_PASSWORD', 'Ab4W034#72ecqe'),
            database=os.getenv('DB_NAME', 'mediatechcloud_sdb'),
            port=int(os.getenv('DB_PORT', 5002))
        )
        if connection.is_connected():
            logging.info("Successfully connected to the database.")
        return connection
    except mysql.connector.Error as e:
        logging.error(f"Error connecting to database: {e}")
        return None

# Get current date
def get_current_date():
    current_date = datetime.now().strftime('%Y-%m-%d')
    logging.info(f"Current Date: {current_date}")
    return current_date

# Fetch current credits for a student within a given date range
def get_total_credits(db, student_id, start_date, end_date):
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT SUM(CREDIT) as total_credits
        FROM `mediatechcloud_sdb`.`transcript`
        WHERE `ENDDATE` >= %s
        AND `STARTDATE` <= %s
        AND `ID` = %s;
        '''
        cursor.execute(query, (start_date, end_date, student_id))
        result = cursor.fetchone()
        if result and result[0] is not None:
            return float(result[0])
        return 0.0
    except mysql.connector.Error as e:
        logging.error(f"Error in get_total_credits for Student ID {student_id}: {e}")
        return 0.0
    finally:
        cursor.close()

# Fetch total enrollment credits for a student from enrollments table
def get_total_enrollment_credits(db, student_id):
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT CREDIT as total_enrollment_credits
        FROM `enrollments`
        WHERE `ID` = %s
        AND `STATUS` IN ("C", "P", "W")
        AND `TYPE` = 'E'
        LIMIT 1;
        '''
        cursor.execute(query, (student_id,))
        result = cursor.fetchone()
        if result and result[0] is not None:
            return float(result[0])
        return 0.0
    except mysql.connector.Error as e:
        logging.error(f"Error in get_total_enrollment_credits for Student ID {student_id}: {e}")
        return 0.0
    finally:
        cursor.close()

# Fetch current term dates using the current date
def get_term_dates(db, current_date):
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT TERMCODE, STARTDATE, ENDDATE
        FROM `termlist`
        WHERE (`ENDDATE` >= %s) AND (`STARTDATE` <= %s) AND ACTIVE=1
        LIMIT 1;
        '''
        cursor.execute(query, (current_date, current_date))
        result = cursor.fetchone()
        if result:
            return result[1], result[2]  # Start date, End date
        else:
            logging.warning("No active term found.")
            return None, None
    except mysql.connector.Error as e:
        logging.error(f"Error in get_term_dates: {e}")
        return None, None
    finally:
        cursor.close()

# Get enrollments for the DAL campus and print the number of students found
def get_enrollments(db, limit=None):
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT e.ID, e.STARTDATE, e.PROGRAM, e.STATUS
        FROM `enrollments` e
        WHERE e.`STATUS` IN ("C", "P", "W", "X")
        AND e.`TYPE` = 'E'
        {limit_clause};
        '''
        limit_clause = f"LIMIT {limit}" if limit else ""
        query = query.format(limit_clause=limit_clause)
        cursor.execute(query)
        results = cursor.fetchall()
        enrollments = [{'student_id': row[0], 'start_date': row[1], 'program': row[2], 'status': row[3]} for row in results]
        # Print the total number of students found
        logging.info(f"Number of students found: {len(enrollments)}")
        return enrollments
    except mysql.connector.Error as e:
        logging.error(f"Error in get_enrollments: {e}")
        return []
    finally:
        cursor.close()

# Get COACODE as price per credit from programs table
def get_program_details(db, program_code):
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT COACODE
        FROM `programs`
        WHERE `PROGRAMCODE` = %s
        AND `ACTIVE` = 1;
        '''
        cursor.execute(query, (program_code,))
        result = cursor.fetchone()
        if result and result[0] is not None:
            coacode_str = str(result[0]).strip()
            logging.info(f"Fetched COACODE for Program {program_code}: '{coacode_str}'")
            if coacode_str == '':
                logging.warning(f"COACODE for Program {program_code} is empty.")
                return 0.0  # Default value when COACODE is empty
            try:
                price_per_credit = float(coacode_str)
                return price_per_credit
            except ValueError:
                logging.error(f"Invalid COACODE format for Program {program_code}: '{coacode_str}'. Setting Price per Credit to 0.0.")
                return 0.0  # Default value when COACODE is invalid
        else:
            logging.warning(f"No active COACODE found for Program {program_code}. Setting Price per Credit to 0.0.")
            return 0.0  # Default value when COACODE is missing or program is inactive
    except mysql.connector.Error as e:
        logging.error(f"Error in get_program_details for Program {program_code}: {e}")
        return 0.0  # Default value on query error
    finally:
        cursor.close()

# Check account ledger for each student and return the tuition amount or "No Tuition"
def check_account_ledger(db, student_id, term_start_date, term_end_date):
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT SUM(TRANSACTIONAMOUNT) as tuition_amount
        FROM `accountledger`
        WHERE `TRANSACTIONCODE` = "Tuition"
        AND `TRANSACTIONDATE` <= %s
        AND `TRANSACTIONDATE` >= %s
        AND `ID` = %s;
        '''
        cursor.execute(query, (term_end_date, term_start_date, student_id))
        result = cursor.fetchone()
        if result and result[0] is not None:
            return float(result[0])
        return "No Tuition"
    except mysql.connector.Error as e:
        logging.error(f"Error in check_account_ledger for Student ID {student_id}: {e}")
        return "No Tuition"
    finally:
        cursor.close()

# Check scheduled funds within the current term
def get_term_scheduled_funds(db, student_id, term_start_date, term_end_date):
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT SUM(NETAMOUNTSCHED) as term_scheduled_funds
        FROM `disbursements`
        WHERE `DISBSTATUS` NOT IN ("X")
        AND `ID` = %s
        AND `DATESCHED` >= %s
        AND `DATESCHED` <= %s;
        '''
        cursor.execute(query, (student_id, term_start_date, term_end_date))
        result = cursor.fetchone()
        if result and result[0] is not None:
            return float(result[0])
        return 0.0
    except mysql.connector.Error as e:
        logging.error(f"Error in get_term_scheduled_funds for Student ID {student_id}: {e}")
        return 0.0
    finally:
        cursor.close()

# Check total scheduled funds for the entire enrollment from enrollment start date
def get_total_scheduled_funds(db, student_id, enrollment_start_date):
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT SUM(NETAMOUNTSCHED) as total_scheduled_funds
        FROM `disbursements`
        WHERE `DISBSTATUS` NOT IN ("X")
        AND `ID` = %s
        AND `DATESCHED` >= %s;
        '''
        cursor.execute(query, (student_id, enrollment_start_date))
        result = cursor.fetchone()
        if result and result[0] is not None:
            return float(result[0])
        return 0.0
    except mysql.connector.Error as e:
        logging.error(f"Error in get_total_scheduled_funds for Student ID {student_id}: {e}")
        return 0.0
    finally:
        cursor.close()

# Main function to run all checks and write to CSV
def run_check():
    db = connect_to_db()
    if db:
        try:
            # Get current date
            current_date = get_current_date()

            # Get term dates using current date
            term_start_date, term_end_date = get_term_dates(db, current_date)

            if not term_start_date or not term_end_date:
                logging.warning("No active term found. Exiting...")
                return

            logging.info(f"Term Start Date: {term_start_date}, Term End Date: {term_end_date}")

            # Get enrollments (Remove limit for full run)
            enrollments = get_enrollments(db)
            # For testing purposes, you can set a limit, e.g., get_enrollments(db, limit=10)

            # Sort enrollments by student ID
            enrollments = sorted(enrollments, key=lambda x: x['student_id'])

            # Print the count of enrollments
            logging.info(f"Total number of enrollments fetched: {len(enrollments)}")

            # CSV file setup
            csv_file = "student_funds.csv"
            duplicate_csv_file = "duplicate_student_funds.csv"
            with open(csv_file, mode='w', newline='') as file:
                writer = csv.writer(file)

                # Write the header
                header = [
                    "Student ID",
                    "Program",
                    "Start Date",
                    "Status",  # New Column
                    "Tuition",
                    "Term Expected (Scheduled Amount)",
                    "Total Expected",
                    "Credits",
                    "Price per Credit",
                    "Semester Price",          # New Column
                    "Overall Enrollment Credits",  # New Column
                    "Overall Price",           # New Column
                    "Remaining Need",          # New Column
                    "Link"
                ]
                writer.writerow(header)

                processed_count = 0

                # Loop through each student and perform checks
                for enrollment in enrollments:
                    student_id = enrollment['student_id']
                    enrollment_start_date = enrollment['start_date']
                    program_code = enrollment['program']
                    status = enrollment['status']  # New Field

                    # Print for debugging
                    logging.info(f"Processing Student ID: {student_id}, Enrollment Start Date: {enrollment_start_date}, Program: {program_code}, Status: {status}")

                    # Check account ledger for tuition
                    tuition_amount = check_account_ledger(db, student_id, term_start_date, term_end_date)
                    logging.info(f"Tuition for Student {student_id}: {tuition_amount}")

                    # Check scheduled funds for the current term
                    term_scheduled_funds = get_term_scheduled_funds(db, student_id, term_start_date, term_end_date)
                    logging.info(f"Term Scheduled Funds for Student {student_id}: {term_scheduled_funds}")

                    # Check total scheduled funds for the entire enrollment
                    total_scheduled_funds = get_total_scheduled_funds(db, student_id, enrollment_start_date)
                    logging.info(f"Total Scheduled Funds for Student {student_id}: {total_scheduled_funds}")

                    # Fetch total credits for the current term
                    total_credits = get_total_credits(db, student_id, term_start_date, term_end_date)
                    logging.info(f"Total Credits for Student {student_id}: {total_credits}")

                    # Fetch total enrollment credits
                    total_enrollment_credits = get_total_enrollment_credits(db, student_id)
                    logging.info(f"Total Enrollment Credits for Student {student_id}: {total_enrollment_credits}")

                    # Get program details (COACODE as price per credit)
                    price_per_credit = get_program_details(db, program_code)
                    logging.info(f"Program Details for {program_code} - Price per Credit: {price_per_credit}")

                    # Calculate semester price
                    semester_price = float(total_credits) * price_per_credit if price_per_credit else 0.0
                    logging.info(f"Semester Price for Student {student_id}: {semester_price}")

                    # Calculate overall price
                    overall_price = float(total_enrollment_credits) * price_per_credit if price_per_credit else 0.0
                    logging.info(f"Overall Price for Student {student_id}: {overall_price}")

                    # Calculate remaining need
                    remaining_need = overall_price - total_scheduled_funds
                    logging.info(f"Remaining Need for Student {student_id}: {remaining_need}")

                    # Create the link
                    link = f"https://mediatechcloud.com/index.php?name={student_id}"

                    # Prepare the row data
                    row_data = [
                        student_id,
                        program_code,
                        enrollment_start_date,
                        status,  # New Data Field
                        tuition_amount,
                        term_scheduled_funds,
                        total_scheduled_funds,
                        total_credits,
                        price_per_credit,
                        semester_price,          # New Data Field
                        total_enrollment_credits,  # New Data Field
                        overall_price,           # New Data Field
                        remaining_need,          # New Data Field
                        link
                    ]

                    # Write the student data to the CSV file
                    writer.writerow(row_data)

                    # Update and print progress after every 10 students
                    processed_count += 1
                    if processed_count % 10 == 0:
                        logging.info(f"Processed {processed_count} students.")

                logging.info(f"CSV file '{csv_file}' created successfully with {processed_count} records.")

            # Read the main CSV file and identify duplicates
            student_id_counts = defaultdict(list)
            duplicate_records = []
            with open(csv_file, mode='r') as file:
                reader = csv.reader(file)
                header = next(reader)  # Skip the header
                for row in reader:
                    student_id = row[0]
                    student_id_counts[student_id].append(row)
                    if len(student_id_counts[student_id]) > 1:
                        duplicate_records.extend(student_id_counts[student_id])

            # Write all duplicate records to the duplicate CSV file
            with open(duplicate_csv_file, mode='w', newline='') as dup_file:
                dup_writer = csv.writer(dup_file)
                dup_writer.writerow(header)  # Write the header
                for record in duplicate_records:
                    dup_writer.writerow(record)

            logging.info(f"Duplicate CSV file '{duplicate_csv_file}' created successfully with {len(duplicate_records)} records.")

        except Exception as e:
            logging.error(f"An error occurred: {e}")
        finally:
            db.close()
            logging.info("Database connection closed.")

def main():
    st.title("Student Funds Check")

    # Sidebar for navigation
    page = st.sidebar.selectbox("Choose a page", ["Run Check", "Download CSV"])

    if page == "Run Check":
        st.header("Run Check")
        if st.button("Run Check"):
            run_check()
            st.success("Check completed!")

        # Read the CSV file and display the table
        try:
            df = pd.read_csv("student_funds.csv")
            st.dataframe(df)
        except FileNotFoundError:
            st.error("No data found. Please run the check first.")

    elif page == "Download CSV":
        st.header("Download CSV")
        st.download_button(
            label="Download Student Funds CSV",
            data=open("student_funds.csv", "rb").read(),
            file_name="student_funds.csv",
            mime="text/csv"
        )

        st.download_button(
            label="Download Duplicate Student Funds CSV",
            data=open("duplicate_student_funds.csv", "rb").read(),
            file_name="duplicate_student_funds.csv",
            mime="text/csv"
        )

if __name__ == '__main__':
    main()