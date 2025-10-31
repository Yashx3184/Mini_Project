import os
import json
import sys
from pathlib import Path
import re
from datetime import datetime

try:
    import pdfplumber
    from PIL import Image
except ImportError as e:
    print("Required libraries not found!")
    print("Please install the required packages using:")
    print("pip install pdfplumber pillow")
    print("\nPdfplumber is excellent for extracting text and tables from PDFs")
    print("with high accuracy and structure preservation.")
    sys.exit(1)

def extract_text_from_pdf_plumber(pdf_path):
    """
    Extract text from PDF using pdfplumber.
    """
    try:
        extracted_text = ""
        tables_data = []
        
        with pdfplumber.open(pdf_path) as pdf:
            print(f"  PDF has {len(pdf.pages)} page(s)")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"    Processing page {page_num}...")
                
                # Extract text from page
                page_text = page.extract_text()
                if page_text:
                    extracted_text += f"=== PAGE {page_num} ===\n"
                    extracted_text += page_text
                    extracted_text += f"\n=== END PAGE {page_num} ===\n\n"
                
                # Extract tables from page
                tables = page.extract_tables()
                if tables:
                    print(f"    Found {len(tables)} table(s) on page {page_num}")
                    for table_num, table in enumerate(tables, 1):
                        table_data = {
                            "page": page_num,
                            "table_number": table_num,
                            "headers": table[0] if table else [],
                            "rows": table[1:] if len(table) > 1 else [],
                            "total_rows": len(table) - 1 if len(table) > 1 else 0
                        }
                        tables_data.append(table_data)
        
        return extracted_text.strip(), tables_data
        
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return "", []

def parse_vtu_result_text_plumber(text, tables, filename):
    """
    Parse VTU result text extracted by pdfplumber and extract structured data.
    """
    result_data = {
        "filename": filename,
        "extraction_timestamp": datetime.now().isoformat(),
        "extraction_method": "pdfplumber",
        "raw_text": text,
        "tables_data": tables,
        "parsed_data": {}
    }
    
    try:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Initialize parsed data structure
        parsed = {
            "student_info": {},
            "institution_info": {},
            "result_info": {},
            "subjects": [],
            "summary": {}
        }
        
        # Enhanced patterns for VTU result fields optimized for pdfplumber
        patterns = {
            "usn": r"(?i)(?:university\s*seat\s*number|usn|register\s*number)[:\s]*([A-Z0-9]{8,15})",
            "name": r"(?i)(?:student\s*name|name)[:\s]*([A-Za-z\s]+?)(?=\s*(?:semester|branch|father|mother|$))",
            "college": r"(?i)(?:college|institution)[:\s]*([A-Za-z0-9\s,.-]+?)(?=\s*(?:branch|semester|$))",
            "branch": r"(?i)(?:branch|course)[:\s]*([A-Za-z\s&]+?)(?=\s*(?:semester|$))",
            "semester": r"(?i)(?:semester|sem)[:\s]*([0-9]+)",
            "result": r"(?i)(?:result|status)[:\s]*([A-Za-z\s]+?)(?=\s*(?:announced|updated|$))",
            "cgpa": r"(?i)(?:cgpa|gpa)[:\s]*([0-9.]+)",
            "percentage": r"(?i)(?:percentage|%)[:\s]*([0-9.]+)",
            "father_name": r"(?i)(?:father['\s]*s?\s*name)[:\s]*([A-Za-z\s]+?)(?=\s*(?:mother|semester|$))",
            "mother_name": r"(?i)(?:mother['\s]*s?\s*name)[:\s]*([A-Za-z\s]+?)(?=\s*(?:semester|branch|$))"
        }
        
        # Extract basic information
        full_text = ' '.join(lines)  # Join for better pattern matching
        
        for key, pattern in patterns.items():
            match = re.search(pattern, full_text, re.MULTILINE | re.DOTALL)
            if match:
                value = match.group(1).strip()
                if key in ["usn", "name", "college", "branch", "result", "father_name", "mother_name"]:
                    parsed["student_info"][key] = value
                elif key in ["semester"]:
                    parsed["result_info"][key] = int(value) if value.isdigit() else value
                elif key in ["cgpa", "percentage"]:
                    try:
                        parsed["summary"][key] = float(value)
                    except ValueError:
                        parsed["summary"][key] = value
        
        # Extract subjects from tables (pdfplumber advantage)
        subjects = []
        processed_codes = set()
        
        for table in tables:
            if table.get("headers") and table.get("rows"):
                headers = [str(h).strip() if h else "" for h in table["headers"]]
                
                # Check if this looks like a subjects table
                header_text = " ".join(headers).lower()
                if any(keyword in header_text for keyword in ["subject", "code", "marks", "grade", "internal", "external"]):
                    print(f"    Processing subjects table with {len(table['rows'])} rows")
                    
                    for row in table["rows"]:
                        if not row or len(row) < 3:
                            continue
                        
                        row = [str(cell).strip() if cell else "" for cell in row]
                        
                        # Try to identify subject code (usually first or second column)
                        subject_code = ""
                        for cell in row[:3]:  # Check first 3 columns for subject code
                            if re.match(r"^[A-Z]{2,4}[0-9]{3}[A-Z]?", cell):
                                subject_code = cell
                                break
                        
                        if subject_code and subject_code not in processed_codes:
                            subject = {
                                "code": subject_code,
                                "name": "",
                                "internal_marks": "",
                                "external_marks": "",
                                "total_marks": "",
                                "grade": "",
                                "result": ""
                            }
                            
                            # Map other columns based on common patterns
                            for i, cell in enumerate(row):
                                if i == 0 and not subject["code"]:
                                    if re.match(r"^[A-Z]{2,4}[0-9]{3}", cell):
                                        subject["code"] = cell
                                elif i == 1 and len(cell) > 5:  # Likely subject name
                                    subject["name"] = cell
                                elif cell.isdigit() and len(cell) <= 3:  # Likely marks
                                    if not subject["internal_marks"]:
                                        subject["internal_marks"] = cell
                                    elif not subject["external_marks"]:
                                        subject["external_marks"] = cell
                                    elif not subject["total_marks"]:
                                        subject["total_marks"] = cell
                                elif cell in ["A+", "A", "B+", "B", "C", "P", "F", "RA", "AB"]:
                                    subject["grade"] = cell
                                elif cell in ["PASS", "FAIL", "P", "F"]:
                                    subject["result"] = cell
                            
                            # If we still don't have a subject name, look for it in the row
                            if not subject["name"]:
                                for cell in row:
                                    if len(cell) > 8 and not cell.isdigit() and cell not in ["P", "F", "PASS", "FAIL"]:
                                        subject["name"] = cell
                                        break
                            
                            subjects.append(subject)
                            processed_codes.add(subject_code)
        
        # If no subjects found in tables, try text parsing
        if not subjects:
            print("    No subjects found in tables, trying text parsing...")
            subject_patterns = [
                r"([A-Z]{2,4}[0-9]{3}[A-Z]?)\s+([A-Za-z\s&-]+?)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([A-Z]+|P|F)",
                r"([A-Z]{2,4}[0-9]{3}[A-Z]?)\s+(.+?)\s+([0-9]+)\s+([A-Z]+|P|F)"
            ]
            
            for line in lines:
                if len(line) < 20:  # Skip short lines
                    continue
                
                for pattern in subject_patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        groups = match.groups()
                        subject_code = groups[0].strip()
                        
                        if subject_code not in processed_codes:
                            subject = {
                                "code": subject_code,
                                "name": groups[1].strip() if len(groups) > 1 else "",
                                "internal_marks": groups[2] if len(groups) > 2 else "",
                                "external_marks": groups[3] if len(groups) > 3 else "",
                                "total_marks": groups[4] if len(groups) > 4 else "",
                                "grade": groups[5] if len(groups) > 5 else ""
                            }
                            
                            subjects.append(subject)
                            processed_codes.add(subject_code)
                            break
        
        if subjects:
            parsed["subjects"] = subjects
            print(f"    Extracted {len(subjects)} subjects")
        
        # Extract University information
        if any(keyword in full_text.upper() for keyword in ["VTU", "VISVESVARAYA", "TECHNOLOGICAL", "UNIVERSITY"]):
            parsed["institution_info"]["university"] = "Visvesvaraya Technological University"
        
        if "BELAGAVI" in full_text.upper():
            parsed["institution_info"]["location"] = "Belagavi, Karnataka, India"
        
        # Extract dates
        date_patterns = [
            r"(20\d{2}-\d{2}-\d{2})",
            r"(\d{2}-\d{2}-20\d{2})",
            r"(\d{1,2}/\d{1,2}/20\d{2})"
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, full_text))
        
        if dates:
            parsed["result_info"]["exam_dates"] = list(set(dates))
        
        # Calculate statistics
        if subjects:
            parsed["summary"]["total_subjects"] = len(subjects)
            
            passed = 0
            failed = 0
            
            for subject in subjects:
                grade = subject.get("grade", "").upper()
                result = subject.get("result", "").upper()
                
                if grade in ["A+", "A", "B+", "B", "C", "P"] or result in ["PASS", "P"]:
                    passed += 1
                elif grade in ["F", "RA", "AB"] or result in ["FAIL", "F"]:
                    failed += 1
            
            parsed["summary"]["subjects_passed"] = passed
            parsed["summary"]["subjects_failed"] = failed
            
            if passed + failed > 0:
                parsed["summary"]["pass_percentage"] = round((passed / (passed + failed)) * 100, 2)
        
        result_data["parsed_data"] = parsed
        
    except Exception as e:
        print(f"Error parsing text for {filename}: {e}")
        result_data["parsing_error"] = str(e)
    
    return result_data

def extract_data_from_pdfs_plumber():
    """
    Extract data from all PDF files using pdfplumber and convert to JSON files.
    """
    # Define paths
    pdf_folder = "4th Sem Results"
    output_folder = os.path.join(pdf_folder, "JSON_Data_Pdfplumber")
    
    # Check if PDF folder exists
    if not os.path.exists(pdf_folder):
        print(f"Error: PDF folder '{pdf_folder}' not found!")
        return
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all PDF files
    try:
        all_files = os.listdir(pdf_folder)
        pdf_files = []
        
        for filename in all_files:
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(pdf_folder, filename)
                if os.path.isfile(pdf_path):
                    pdf_files.append((pdf_path, filename))
                    
    except Exception as e:
        print(f"Error reading PDF folder: {e}")
        return
    
    if not pdf_files:
        print("No PDF files found in the folder!")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process...")
    
    # Display files to be processed
    print("\nPDF files to process:")
    for i, (_, filename) in enumerate(pdf_files[:10], 1):  # Show first 10
        print(f"{i:2d}. {filename}")
    if len(pdf_files) > 10:
        print(f"    ... and {len(pdf_files) - 10} more files")
    
    # Ask for confirmation
    print(f"\nThis will extract text from {len(pdf_files)} PDF files using pdfplumber and create JSON files")
    print(f"JSON files will be saved in: {output_folder}")
    confirm = input("Do you want to proceed? (y/n): ").lower().strip()
    
    if confirm != 'y' and confirm != 'yes':
        print("Operation cancelled.")
        return
    
    # Process PDFs
    processed_count = 0
    errors = []
    
    print(f"\nStarting pdfplumber extraction...")
    print("=" * 70)
    
    for i, (pdf_path, pdf_filename) in enumerate(pdf_files, 1):
        try:
            print(f"Processing {i}/{len(pdf_files)}: {pdf_filename}")
            
            # Extract text and tables from PDF using pdfplumber
            extracted_text, tables_data = extract_text_from_pdf_plumber(pdf_path)
            
            if not extracted_text:
                print(f"  ⚠ No text extracted from {pdf_filename}")
                continue
            
            # Parse the extracted text and tables
            result_data = parse_vtu_result_text_plumber(extracted_text, tables_data, pdf_filename)
            
            # Create JSON filename
            base_name = os.path.splitext(pdf_filename)[0]
            json_filename = f"{base_name}_pdfplumber.json"
            json_path = os.path.join(output_folder, json_filename)
            
            # Save JSON data
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            # Show brief info about extracted data
            parsed = result_data.get("parsed_data", {})
            student_info = parsed.get("student_info", {})
            usn = student_info.get("usn", "Unknown")
            name = student_info.get("name", "Unknown")
            subjects_count = len(parsed.get("subjects", []))
            tables_count = len(tables_data)
            
            print(f"  ✓ Saved: {json_filename}")
            print(f"    USN: {usn}, Name: {name[:25]}{'...' if len(name) > 25 else ''}")
            print(f"    Text: {len(extracted_text)} chars, Tables: {tables_count}, Subjects: {subjects_count}")
            
            processed_count += 1
            
        except Exception as e:
            error_msg = f"Error processing {pdf_filename}: {str(e)}"
            print(f"  ✗ {error_msg}")
            errors.append(error_msg)
    
    # Summary
    print("\n" + "=" * 70)
    print("PDFPLUMBER EXTRACTION SUMMARY")
    print("=" * 70)
    print(f"Successfully processed: {processed_count}/{len(pdf_files)} PDF files")
    print(f"JSON files created: {processed_count}")
    print(f"Output folder: {output_folder}")
    
    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        print("Error details:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")
    
    if processed_count > 0:
        print(f"\n✓ Pdfplumber extraction completed!")
        print(f"Check the '{output_folder}' folder for JSON files.")
        
        # Create a summary JSON file
        try:
            summary_data = {
                "extraction_summary": {
                    "timestamp": datetime.now().isoformat(),
                    "method": "pdfplumber",
                    "total_pdfs": len(pdf_files),
                    "processed_successfully": processed_count,
                    "errors": len(errors),
                    "output_folder": output_folder
                },
                "files_processed": [filename for _, filename in pdf_files[:processed_count]]
            }
            
            summary_path = os.path.join(output_folder, "_extraction_summary_pdfplumber.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            print(f"Summary saved to: _extraction_summary_pdfplumber.json")
            
        except Exception as e:
            print(f"Could not create summary file: {e}")
    else:
        print(f"\n✗ No files were processed successfully.")

def check_dependencies():
    """Check if required dependencies are available."""
    try:
        import pdfplumber
        from PIL import Image
        
        print("✓ Required libraries are installed.")
        print(f"Pdfplumber version: {pdfplumber.__version__}")
        return True
        
    except ImportError as e:
        print("✗ Missing required libraries.")
        print("\nTo install required packages, run:")
        print("pip install pdfplumber pillow")
        print("\nPdfplumber is excellent for:")
        print("- Extracting text with better formatting preservation")
        print("- Handling tables and structured data")
        print("- Working directly with PDF files (no image conversion needed)")
        return False

if __name__ == "__main__":
    print("PDF to JSON Converter using Pdfplumber")
    print("=" * 50)
    
    # Check dependencies first
    if not check_dependencies():
        print("\nPlease install the missing dependencies and try again.")
        input("Press Enter to exit...")
        sys.exit(1)
    
    try:
        extract_data_from_pdfs_plumber()
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to exit...")