#!/usr/bin/env python3
"""
Local runner: this script calls the run_check() function from app.py
to execute the Student Funds Check and generate CSV files without using Streamlit.
"""

from app import run_check

def main():
    print("Running Student Funds Check...")
    run_check()
    print("Check completed! CSV files generated.")

if __name__ == '__main__':
    main() 