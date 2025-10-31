import os
import json
import sys
from pathlib import Path
import re
from datetime import datetime
import numpy as np

try:
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
    from PIL import Image
    import torch
except ImportError as e:
    print("Required libraries not found!")
    print("Please install the required packages using:")
    print("pip install python-doctr[torch] pillow torch torchvision")
    print("\nDOCTR is a deep learning-based OCR library that provides better accuracy")
    print("than traditional OCR methods for document text recognition.")
    sys.exit(1)

def extract_text_from_image_doctr(image_path, model):
    """
    Extract text from image using DOCTR OCR.
    """
    try:
        # Load the document
        doc = DocumentFile.from_images(image_path)
        
        # Apply OCR
        result = model(doc)
        
        # Extract text from result
        text_blocks = []
        
        # Iterate through pages
        for page in result.pages:
            # Iterate through blocks
            for block in page.blocks:
                # Iterate through lines
                for line in block.lines:
                    # Collect words in the line
                    line_words = []
                    for word in line.words:
                        if word.confidence > 0.3:  # Filter low confidence words
                            line_words.append(word.value)
                    
                    if line_words:
                        line_text = ' '.join(line_words)
                        text_blocks.append(line_text)
        
        # Join all text blocks
        extracted_text = '\n'.join(text_blocks)
        return extracted_text.strip()
        
    except Exception as e:
        print(f"Error extracting text from {image_path}: {e}")
        return ""

def parse_vtu_result_text(text, filename):
    """
    Parse VTU result text and extract structured data.
    """
    result_data = {
        "filename": filename,
        "extraction_timestamp": datetime.now().isoformat(),
        "extraction_method": "DOCTR",
        "raw_text": text,
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
        
        # Enhanced patterns for VTU result fields with DOCTR-specific adjustments
        patterns = {
            "usn": r"(?i)(?:usn|university\s*seat\s*number|register\s*number|reg\s*no)[:\s]*([A-Z0-9]{8,15})",
            "name": r"(?i)(?:student\s*name|name)[:\s]*([A-Za-z\s]+?)(?=\s*(?:semester|branch|usn|$))",
            "college": r"(?i)(?:college|institution)[:\s]*([A-Za-z0-9\s,.-]+?)(?=\s*(?:branch|semester|$))",
            "branch": r"(?i)(?:branch|course)[:\s]*([A-Za-z\s&]+?)(?=\s*(?:semester|$))",
            "semester": r"(?i)(?:semester|sem)[:\s]*([0-9]+)",
            "result": r"(?i)(?:result|status)[:\s]*([A-Za-z\s]+?)(?=\s*(?:announced|updated|$))",
            "cgpa": r"(?i)(?:cgpa|gpa)[:\s]*([0-9.]+)",
            "percentage": r"(?i)(?:percentage|%)[:\s]*([0-9.]+)"
        }
        
        # Extract basic information
        full_text = ' '.join(lines)  # Join for better pattern matching
        
        for key, pattern in patterns.items():
            match = re.search(pattern, full_text, re.MULTILINE | re.DOTALL)
            if match:
                value = match.group(1).strip()
                if key in ["usn", "name", "college", "branch", "result"]:
                    parsed["student_info"][key] = value
                elif key in ["semester"]:
                    parsed["result_info"][key] = int(value) if value.isdigit() else value
                elif key in ["cgpa", "percentage"]:
                    try:
                        parsed["summary"][key] = float(value)
                    except ValueError:
                        parsed["summary"][key] = value
        
        # Enhanced subject extraction patterns for DOCTR
        subject_patterns = [
            # Pattern for: CODE NAME INTERNAL EXTERNAL TOTAL GRADE DATE
            r"([A-Z]{2,4}[0-9]{3}[A-Z]?)\s+([A-Za-z\s&-]+?)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([A-Z]+|P|F)\s+(20\d{2}-\d{2}-\d{2})",
            # Pattern for: CODE NAME INTERNAL EXTERNAL TOTAL GRADE
            r"([A-Z]{2,4}[0-9]{3}[A-Z]?)\s+([A-Za-z\s&-]+?)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([A-Z]+|P|F)",
            # Pattern for: CODE NAME MARKS GRADE
            r"([A-Z]{2,4}[0-9]{3}[A-Z]?)\s+([A-Za-z\s&-]+?)\s+([0-9]+)\s+([A-Z]+|P|F)",
            # More flexible pattern
            r"([A-Z0-9]{4,8})\s+([A-Za-z\s&-]{10,50}?)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([A-Z]+)"
        ]
        
        subjects = []
        processed_codes = set()  # To avoid duplicates
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 20:  # Skip short lines
                continue
                
            for pattern in subject_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    groups = match.groups()
                    subject_code = groups[0].strip()
                    
                    # Avoid duplicate subjects
                    if subject_code in processed_codes:
                        continue
                        
                    if len(groups) >= 4:
                        subject = {
                            "code": subject_code,
                            "name": groups[1].strip(),
                            "internal_marks": groups[2] if len(groups) > 2 else "",
                            "external_marks": groups[3] if len(groups) > 3 else "",
                            "total_marks": groups[4] if len(groups) > 4 else "",
                            "grade": groups[5] if len(groups) > 5 else "",
                            "date": groups[6] if len(groups) > 6 else ""
                        }
                        
                        # Clean up subject name
                        subject["name"] = re.sub(r'\s+', ' ', subject["name"]).strip()
                        
                        subjects.append(subject)
                        processed_codes.add(subject_code)
                        break
        
        if subjects:
            parsed["subjects"] = subjects
        
        # Extract University Seat Number more aggressively
        usn_patterns = [
            r"([0-9][A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{3})",  # Pattern like 4AD24EC403
            r"([A-Z0-9]{10,12})",  # General alphanumeric pattern
        ]
        
        for pattern in usn_patterns:
            matches = re.findall(pattern, full_text)
            if matches:
                parsed["student_info"]["usn"] = matches[0]
                break
        
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
            parsed["result_info"]["exam_dates"] = list(set(dates))  # Remove duplicates
        
        # Identify VTU
        if any(keyword in full_text.upper() for keyword in ["VTU", "VISVESVARAYA", "TECHNOLOGICAL", "UNIVERSITY"]):
            parsed["institution_info"]["university"] = "Visvesvaraya Technological University"
        
        # Calculate statistics
        if subjects:
            parsed["summary"]["total_subjects"] = len(subjects)
            
            # Count pass/fail based on grades
            passed = 0
            failed = 0
            
            for subject in subjects:
                grade = subject.get("grade", "").upper()
                if grade in ["A+", "A", "B+", "B", "C", "P", "PASS"]:
                    passed += 1
                elif grade in ["F", "FAIL", "RA", "AB"]:
                    failed += 1
            
            parsed["summary"]["subjects_passed"] = passed
            parsed["summary"]["subjects_failed"] = failed
            
            if passed + failed > 0:
                parsed["summary"]["pass_percentage"] = (passed / (passed + failed)) * 100
        
        result_data["parsed_data"] = parsed
        
    except Exception as e:
        print(f"Error parsing text for {filename}: {e}")
        result_data["parsing_error"] = str(e)
    
    return result_data

def extract_data_from_images_doctr():
    """
    Extract data from all images using DOCTR and convert to JSON files.
    """
    # Define paths
    images_folder = os.path.join("4th Sem Results", "Images")
    output_folder = os.path.join("4th Sem Results", "JSON_Data_DOCTR")
    
    # Check if images folder exists
    if not os.path.exists(images_folder):
        print(f"Error: Images folder '{images_folder}' not found!")
        print("Please run the PDF to images converter first.")
        return
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all image files
    try:
        all_files = os.listdir(images_folder)
        image_files = []
        
        for filename in all_files:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(images_folder, filename)
                if os.path.isfile(image_path):
                    image_files.append((image_path, filename))
                    
    except Exception as e:
        print(f"Error reading images folder: {e}")
        return
    
    if not image_files:
        print("No image files found in the folder!")
        return
    
    # Limit to only 1 image for testing
    image_files = image_files[:1]
    
    print(f"Found {len(image_files)} image file to process (limited to 1 for testing)...")
    
    # Display files to be processed
    print("\nImage file to process:")
    for i, (_, filename) in enumerate(image_files, 1):
        print(f"{i:2d}. {filename}")
    
    # Ask for model selection
    print("\nDOCTR Model Options:")
    print("1. Fast model (db_resnet50 + crnn_vgg16_bn) - Faster processing")
    print("2. Accurate model (db_resnet50 + crnn_mobilenet_v3_large) - Better accuracy")
    print("3. Best model (db_resnet50 + parseq) - Highest accuracy, slower")
    
    model_choice = input("Choose model (1/2/3) [default: 2]: ").strip()
    
    # Initialize DOCTR model
    print("\nInitializing DOCTR model...")
    try:
        if model_choice == "1":
            model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)
            model_name = "Fast (db_resnet50 + crnn_vgg16_bn)"
        elif model_choice == "3":
            model = ocr_predictor(det_arch='db_resnet50', reco_arch='parseq', pretrained=True)
            model_name = "Best (db_resnet50 + parseq)"
        else:
            model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_mobilenet_v3_large', pretrained=True)
            model_name = "Accurate (db_resnet50 + crnn_mobilenet_v3_large)"
        
        print(f"✓ DOCTR model loaded: {model_name}")
        
        # Set device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"✓ Using device: {device}")
        
    except Exception as e:
        print(f"✗ Error loading DOCTR model: {e}")
        print("This might be due to missing dependencies or network issues.")
        return
    
    # Ask for confirmation
    print(f"\nThis will extract text from {len(image_files)} image using DOCTR and create JSON file")
    print(f"JSON file will be saved in: {output_folder}")
    confirm = input("Do you want to proceed? (y/n): ").lower().strip()
    
    if confirm != 'y' and confirm != 'yes':
        print("Operation cancelled.")
        return
    
    # Process images
    processed_count = 0
    errors = []
    
    print(f"\nStarting DOCTR OCR extraction...")
    print("=" * 70)
    
    for i, (image_path, image_filename) in enumerate(image_files, 1):
        try:
            print(f"Processing {i}/{len(image_files)}: {image_filename}")
            
            # Extract text from image using DOCTR
            extracted_text = extract_text_from_image_doctr(image_path, model)
            
            if not extracted_text:
                print(f"  ⚠ No text extracted from {image_filename}")
                continue
            
            # Parse the extracted text
            result_data = parse_vtu_result_text(extracted_text, image_filename)
            
            # Create JSON filename
            base_name = os.path.splitext(image_filename)[0]
            json_filename = f"{base_name}_doctr.json"
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
            
            print(f"  ✓ Saved: {json_filename}")
            print(f"    USN: {usn}, Name: {name[:25]}{'...' if len(name) > 25 else ''}")
            print(f"    Text: {len(extracted_text)} chars, Subjects: {subjects_count}")
            
            processed_count += 1
            
        except Exception as e:
            error_msg = f"Error processing {image_filename}: {str(e)}"
            print(f"  ✗ {error_msg}")
            errors.append(error_msg)
    
    # Summary
    print("\n" + "=" * 70)
    print("DOCTR OCR EXTRACTION SUMMARY")
    print("=" * 70)
    print(f"Successfully processed: {processed_count}/{len(image_files)} image files")
    print(f"JSON files created: {processed_count}")
    print(f"Model used: {model_name}")
    print(f"Output folder: {output_folder}")
    
    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        print("Error details:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")
    
    if processed_count > 0:
        print(f"\n✓ DOCTR OCR extraction completed!")
        print(f"Check the '{output_folder}' folder for JSON files.")
        
        # Create a summary JSON file
        try:
            summary_data = {
                "extraction_summary": {
                    "timestamp": datetime.now().isoformat(),
                    "method": "DOCTR",
                    "model": model_name,
                    "device": device,
                    "total_images": len(image_files),
                    "processed_successfully": processed_count,
                    "errors": len(errors),
                    "output_folder": output_folder
                },
                "files_processed": [filename for _, filename in image_files[:processed_count]]
            }
            
            summary_path = os.path.join(output_folder, "_extraction_summary_doctr.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            print(f"Summary saved to: _extraction_summary_doctr.json")
            
        except Exception as e:
            print(f"Could not create summary file: {e}")
    else:
        print(f"\n✗ No files were processed successfully.")

def check_dependencies():
    """Check if required dependencies are available."""
    try:
        from doctr.models import ocr_predictor
        from doctr.io import DocumentFile
        import torch
        from PIL import Image
        
        print("✓ Required libraries are installed.")
        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        
        # Test model loading
        try:
            print("Testing DOCTR model loading...")
            test_model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)
            print("✓ DOCTR model can be loaded successfully.")
            del test_model  # Free memory
            return True
        except Exception as e:
            print(f"⚠ Warning: Could not load DOCTR model: {e}")
            print("This might be due to network issues during first run.")
            print("The script will attempt to download models when running.")
            return True
            
    except ImportError as e:
        print("✗ Missing required libraries.")
        print("\nTo install required packages, run:")
        print("pip install python-doctr[torch] pillow torch torchvision")
        print("\nNote: DOCTR requires PyTorch. If you don't have it, install with:")
        print("pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")
        return False

if __name__ == "__main__":
    print("Image to JSON Converter using DOCTR (OCR)")
    print("=" * 55)
    
    # Check dependencies first
    if not check_dependencies():
        print("\nPlease install the missing dependencies and try again.")
        input("Press Enter to exit...")
        sys.exit(1)
    
    try:
        extract_data_from_images_doctr()
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to exit...")