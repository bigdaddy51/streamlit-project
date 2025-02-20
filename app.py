import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime
import csv
import logging
import os
from collections import defaultdict
import streamlit.components.v1 as components
import time  # Ensure time is imported; you can also add this at the top of your file.

# Set the page layout to wide
st.set_page_config(layout="wide")

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("student_funds.log"),
        logging.StreamHandler()
    ]
)

# Additional CSS to change cursor style on hover
css = """
<style>
.st-ay:hover {
    cursor: pointer !important;
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------- Database Functions ---------------- #

def connect_to_db():
    """Establish a connection to the MySQL database."""
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

def get_current_date():
    """Return the current date in YYYY-MM-DD format."""
    current_date = datetime.now().strftime('%Y-%m-%d')
    logging.info(f"Current Date: {current_date}")
    return current_date

def get_total_credits(db, student_id, start_date, end_date):
    """Fetch the total credits for a student within the specified term dates."""
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

def get_total_enrollment_credits(db, student_id):
    """Fetch the total enrollment credits for a student from the enrollments table."""
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT CREDIT as total_enrollment_credits
        FROM `enrollments`
        WHERE `ID` = %s
          AND `STATUS` IN ("C", "P", "W","L")
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

def get_term_dates(db, current_date):
    """Fetch the current term's code, start date, and end date based on the current date."""
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT TERMCODE, STARTDATE, ENDDATE
        FROM `termlist`
        WHERE (`ENDDATE` >= %s)
          AND (`STARTDATE` <= %s)
          AND ACTIVE = 1
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

def get_enrollments(db, limit=None):
    """Fetch the most recent enrollment for each student with specific statuses ("C","P","W","X") and type 'E'."""
    cursor = db.cursor(buffered=True)
    try:
        limit_clause = f"LIMIT {limit}" if limit else ""
        query = f"""
        SELECT e.ID, e.STARTDATE, e.PROGRAM, e.STATUS, e.ENROLLMENTNUMBER
        FROM enrollments e
        JOIN (
            SELECT ID, MAX(ENROLLMENTNUMBER) AS maxEnroll
            FROM enrollments
            WHERE STATUS IN ("C", "P", "W","L") AND TYPE = 'E'
            GROUP BY ID
        ) latest ON e.ID = latest.ID AND e.ENROLLMENTNUMBER = latest.maxEnroll
        WHERE e.STATUS IN ("C", "P", "W","L")
        {limit_clause};
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

def get_program_details(db, program_code):
    """
    Get the program details (using COACODE as price per credit) from the programs table.
    If COACODE is empty or invalid, default to 0.0.
    """
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
            if coacode_str == '':
                logging.warning(f"COACODE for Program {program_code} is empty.")
                return 0.0
            try:
                price_per_credit = float(coacode_str)
                return price_per_credit
            except ValueError:
                logging.error(f"Invalid COACODE format for Program {program_code}: '{coacode_str}'. Setting Price per Credit to 0.0.")
                return 0.0
        else:
            logging.warning(f"No active COACODE found for Program {program_code}. Setting Price per Credit to 0.0.")
            return 0.0
    except mysql.connector.Error as e:
        logging.error(f"Error in get_program_details for Program {program_code}: {e}")
        return 0.0
    finally:
        cursor.close()

def check_account_ledger(db, student_id, term_start_date, term_end_date):
    """Check the account ledger for a student and return the tuition amount or 'No Tuition'."""
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



#WHERE `DISBSTATUS` NOT IN ("X")
#AND `ID` = %s
#AND `DATESCHED` >= %s
#AND `DATESCHED` <= %s;




def get_term_scheduled_funds(db, student_id, term_start_date, term_end_date):
    """Check scheduled funds for the current term for a student."""
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT SUM(NETAMOUNTSCHED) as term_scheduled_funds
        FROM `disbursements`
        WHERE `ID` = %s
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


#WHERE DISBSTATUS NOT IN ("X")
#AND ID = %s
#AND ENROLLMENTNUMBER = %s;



def get_total_scheduled_funds(db, student_id):
    """Check total scheduled funds for the most recent enrollment (by enrollment number) for a student."""
    enrollment_number = get_latest_enrollment_number(db, student_id)
    if enrollment_number is None:
        return 0.0

    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT SUM(NETAMOUNTSCHED) as total_scheduled_funds
        FROM disbursements
        WHERE ID = %s
          AND ENROLLMENTNUMBER = %s;
        '''
        query2 = '''
        SELECT SUM(NETAMOUNTSCHED) as total_scheduled_funds
        FROM disbursements
        WHERE ID = %s
          AND ENROLLMENTNUMBER = %s;
        '''

        cursor.execute(query, (student_id, enrollment_number))
        result = cursor.fetchone()
        if result and result[0] is not None:
            return float(result[0])
        return 0.0
    except mysql.connector.Error as e:
        logging.error(f"Error in get_total_scheduled_funds for Student ID {student_id}: {e}")
        return 0.0
    finally:
        cursor.close()

def get_latest_enrollment_number(db, student_id):
    """Return the most recent (largest) enrollment number for the given student."""
    cursor = db.cursor(buffered=True)
    try:
        query = "SELECT MAX(ENROLLMENTNUMBER) FROM enrollments WHERE ID = %s;"
        cursor.execute(query, (student_id,))
        result = cursor.fetchone()
        if result and result[0] is not None:
            return result[0]
        else:
            logging.warning(f"No enrollment number found for Student ID {student_id}.")
            return None
    except mysql.connector.Error as e:
        logging.error(f"Error in get_latest_enrollment_number for Student ID {student_id}: {e}")
        return None
    finally:
        cursor.close()

def get_student_name(db, student_id):
    """Return the first name and last name for the given student ID."""
    cursor = db.cursor(buffered=True)
    try:
        query = '''
        SELECT FNAME, LNAME
        FROM students
        WHERE ID = %s;
        '''
        cursor.execute(query, (student_id,))
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        else:
            logging.warning(f"No name found for Student ID {student_id}.")
            return "", ""
    except mysql.connector.Error as e:
        logging.error(f"Error retrieving name for Student ID {student_id}: {e}")
        return "", ""
    finally:
        cursor.close()

# ---------------- Main Check Function ---------------- #

def run_check():
    """Run all the checks, write data to CSV files, and log the results."""
    db = connect_to_db()
    if db:
        try:
            current_date = get_current_date()
            term_code, term_start_date, term_end_date = get_term_dates(db, current_date)
            if not term_start_date or not term_end_date:
                logging.warning("No active term found. Exiting...")
                return

            logging.info(f"Term Start Date: {term_start_date}, Term End Date: {term_end_date}")

            enrollments = get_enrollments(db)
            enrollments = sorted(enrollments, key=lambda x: x['student_id'])

            # CSV file setup for main data
            csv_file = "student_funds.csv"
            with open(csv_file, mode='w', newline='') as file:
                writer = csv.writer(file)
                header = [
                    "Student ID",
                    "First Name",
                    "Last Name",
                    "Program",
                    "Start Date",
                    "Term Code",
                    "Status",
                    "Tuition",
                    "Term Expected",
                    "Total Expected",
                    "Credits",
                    "Price per Credit",
                    "Semester Price",
                    "Overall Enrollment Credits",
                    "Overall Price",
                    "Remaining Need",
                    "Link"
                ]
                writer.writerow(header)

                processed_count = 0
                total_records = len(enrollments)
                progress_text_placeholder = st.empty()
                my_bar = st.progress(0)

                for enrollment in enrollments:
                    student_id = enrollment['student_id']
                    enrollment_start_date = enrollment['start_date']
                    program_code = enrollment['program']
                    status = enrollment['status']

                    logging.info(f"Processing Student ID: {student_id}, Enrollment Start Date: {enrollment_start_date}, Program: {program_code}, Status: {status}")

                    tuition_amount = check_account_ledger(db, student_id, term_start_date, term_end_date)
                    term_scheduled_funds = get_term_scheduled_funds(db, student_id, term_start_date, term_end_date)
                    total_scheduled_funds = get_total_scheduled_funds(db, student_id)
                    total_credits = get_total_credits(db, student_id, term_start_date, term_end_date)
                    total_enrollment_credits = get_total_enrollment_credits(db, student_id)
                    price_per_credit = get_program_details(db, program_code)
                    semester_price = float(total_credits) * price_per_credit if price_per_credit else 0.0
                    overall_price = float(total_enrollment_credits) * price_per_credit if price_per_credit else 0.0
                    remaining_need = overall_price - total_scheduled_funds

                    # Create the link as plain text (will be converted to clickable HTML later)
                    link = f"https://mediatechcloud.com/index.php?name={student_id}"

                    first_name, last_name = get_student_name(db, student_id)
                    row_data = [
                        student_id,
                        first_name,
                        last_name,
                        program_code,
                        enrollment_start_date,
                        term_code,
                        status,
                        tuition_amount,
                        term_scheduled_funds,
                        total_scheduled_funds,
                        total_credits,
                        price_per_credit,
                        semester_price,
                        total_enrollment_credits,
                        overall_price,
                        remaining_need,
                        link
                    ]
                    writer.writerow(row_data)

                    processed_count += 1
                    percent_complete = int((processed_count / total_records) * 100)
                    progress_text = f"Processing record {processed_count} of {total_records}. Please wait."
                    progress_text_placeholder.text(progress_text)
                    my_bar.progress(percent_complete)
                    time.sleep(0.1)  # Add a short delay to allow the UI to update

                logging.info(f"CSV file '{csv_file}' created successfully with {processed_count} records.")

            # Identify duplicate records and write them to a separate CSV file
            student_id_counts = defaultdict(list)
            duplicate_records = []
            with open(csv_file, mode='r') as file:
                reader = csv.reader(file)
                header = next(reader)  # Skip header
                for row in reader:
                    student_id = row[0]
                    student_id_counts[student_id].append(row)
                    if len(student_id_counts[student_id]) > 1:
                        duplicate_records.extend(student_id_counts[student_id])

            with open("duplicate_student_funds.csv", mode='w', newline='') as dup_file:
                dup_writer = csv.writer(dup_file)
                dup_writer.writerow(header)  # Write header
                for record in duplicate_records:
                    dup_writer.writerow(record)

            logging.info(f"Duplicate CSV file 'duplicate_student_funds.csv' created successfully with {len(duplicate_records)} records.")

        except Exception as e:
            logging.error(f"An error occurred: {e}")
        finally:
            db.close()
            logging.info("Database connection closed.")

# ---------------- Streamlit Main Application ---------------- #

def main():
    st.title("Student Funds Check")

    # Sidebar navigation
    page = st.sidebar.selectbox("Choose a page", ["Run Check", "Download CSV"])

    if page == "Run Check":
        st.header("Run Check")
        if st.button("Run Check"):
            run_check()
            st.success("Check completed!")

        # Read the CSV file and display it using Streamlit's built-in methods
        try:
            df = pd.read_csv("student_funds.csv")
            
            # Add a search box to filter table content
            search_value = st.text_input("Search Table", "")
            if search_value:
                df = df[df.apply(lambda row: row.astype(str).str.contains(search_value, case=False, na=False).any(), axis=1)]
            
            # Convert the 'Link' column to clickable HTML links (if not already converted)
            if 'Link' in df.columns:
                df['Link'] = df['Link'].apply(lambda x: f'<a href="{x}" target="_blank">Click here</a>' if pd.notnull(x) else '')

            # Display the DataFrame as an HTML table enhanced with DataTables for column sorting
            html_table = df.to_html(escape=False, index=False, table_id="myTable", classes="display")
            
            html_string = f"""
            <html>
              <head>
                <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css"/>
                <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
                <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
                <style>
                  /* Force table to fill the container width */
                  #myTable {{ width: 100%; }}
                </style>
              </head>
              <body>
                {html_table}
                <script>
                  $(document).ready(function() {{
                      var table = $('#myTable').DataTable({{
                        "searching": false,   // disable DataTables search (using our external search box)
                        "paging": false,      // disable pagination to display all records
                        "scrollY": "550px",   // enable vertical scrolling with a 550px view area
                        "scrollX": true,      // enable horizontal scrolling for proper column alignment
                        "autoWidth": false,   // disable automatic column width calculation      
                        "scrollCollapse": true
                      }});
                      table.columns.adjust().draw();  // Adjust column widths after initialization
                  }});
                </script>
              </body>
            </html>
            """

            components.html(html_string, height=600)
            
        except (FileNotFoundError, pd.errors.EmptyDataError):
            st.error("No data found. Please run the check first.")

    elif page == "Download CSV":
        st.header("Download CSV")
        try:
            with open("student_funds.csv", "rb") as f:
                st.download_button(
                    label="Download Student Funds CSV",
                    data=f.read(),
                    file_name="student_funds.csv",
                    mime="text/csv"
                )
            with open("duplicate_student_funds.csv", "rb") as f:
                st.download_button(
                    label="Download Duplicate Student Funds CSV",
                    data=f.read(),
                    file_name="duplicate_student_funds.csv",
                    mime="text/csv"
                )
        except FileNotFoundError:
            st.error("CSV files not found. Please run the check first.")

from flask import Flask, jsonify, request
app = Flask(__name__)

@app.route("/net_profit_by_class/<date_macro>/<qb_class>")
def fetch_net_profit_by_class(date_macro, qb_class):
    """
    Get net profit for a specific class (Dallas School or Houston School)
    Example: /net_profit_by_class/custom/Dallas%20School?start_date=2024-01-01&end_date=2024-03-31
    """
    access_token = Token.get_current_access_token()
    if not access_token:
        return jsonify({"error": "Unable to retrieve a valid access token"}), 500

    url = f'https://quickbooks.api.intuit.com/v3/company/{COMPANY_ID}/reports/ProfitAndLoss?minorversion=14'
    
    # Add class filter
    url += f'&class={urllib.parse.quote(qb_class)}'
    
    # Handle custom date range
    if date_macro == 'custom':
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if not (start_date and end_date):
            return jsonify({"error": "start_date and end_date are required for custom date range"}), 400
        url += f'&start_date={start_date}&end_date={end_date}'
    else:
        url += f'&date_macro={date_macro}'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        rows = data.get("Rows", {}).get("Row", [])
        for row in rows:
            if row.get("group") == "NetIncome":
                net_income = row.get("Summary", {}).get("ColData", [])[1].get("value")
                if net_income is not None:
                    net_income_float = float(net_income)
                    formatted_net_income = '${:,.2f}'.format(net_income_float)
                    return jsonify({"net_profit": formatted_net_income})

        return jsonify({"error": "Net income data not found in the response"}), 404
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Unable to get net profit: {str(e)}"}), 500

if __name__ == '__main__':
    main()
