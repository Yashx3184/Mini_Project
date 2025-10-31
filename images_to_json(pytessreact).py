import os
import json
import sys
from pathlib import Path
import re
from datetime import datetime

try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    
    # Try to set Tesseract path for Windows
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break
            
except ImportError as e:
    print("Required libraries not found!")
    print("Please install the required packages using:")
    print("pip install pytesseract pillow opencv-python")
    print("\nNote: You also need to install Tesseract OCR:")
    print("- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
    print("- Or use: winget install UB-Mannheim.TesseractOCR")
    sys.exit(1)

def preprocess_image(image_path):
    """
    Preprocess image to improve OCR accuracy.
    """
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Apply threshold to get binary image
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Apply morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return processed
        
    except Exception as e:
        print(f"Error preprocessing {image_path}: {e}")
        return None

def extract_text_from_image(image_path):
    """
    Extract text from image using OCR.
    """
    try:
        # First try with original image
        img = Image.open(image_path)
        
        # Configure tesseract for better accuracy
        config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,():/-\n '
        
        # Extract text
        text = pytesseract.image_to_string(img, config=config)
        
        # If text is too short, try with preprocessed image
        if len(text.strip()) < 50:
            processed_img = preprocess_image(image_path)
            if processed_img is not None:
                pil_img = Image.fromarray(processed_img)
                text = pytesseract.image_to_string(pil_img, config=config)
        
        return text.strip()
        
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
        
        # Patterns for common VTU result fields
        patterns = {
            "usn": r"(?i)(?:usn|register\s*number|reg\s*no)[:\s]*([A-Z0-9]+)",
            "name": r"(?i)(?:name|student\s*name)[:\s]*([A-Za-z\s]+?)(?:\n|$)",
            "college": r"(?i)(?:college|institution)[:\s]*([A-Za-z0-9\s,.-]+?)(?:\n|$)",
            "branch": r"(?i)(?:branch|course)[:\s]*([A-Za-z\s&]+?)(?:\n|$)",
            "semester": r"(?i)(?:semester|sem)[:\s]*([0-9]+)",
            "result": r"(?i)(?:result|status)[:\s]*([A-Za-z\s]+?)(?:\n|$)",
            "cgpa": r"(?i)(?:cgpa|gpa)[:\s]*([0-9.]+)",
            "percentage": r"(?i)(?:percentage|%)[:\s]*([0-9.]+)"
        }
        
        # Extract basic information
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.MULTILINE)
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
        
        # Try to extract subject information
        subject_patterns = [
            r"([A-Z0-9]{2,6})\s+([A-Za-z\s&-]+?)\s+([0-9]+)\s+([A-Z]+|\d+)\s+([A-Z]+|\d+)",
            r"([A-Z0-9]{2,6})\s+(.+?)\s+([A-Z]+)\s+([0-9]+)",
        ]
        
        subjects = []
        for line in lines:
            for pattern in subject_patterns:
                match = re.search(pattern, line)
                if match:
                    groups = match.groups()
                    if len(groups) >= 3:
                        subject = {
                            "code": groups[0],
                            "name": groups[1].strip(),
                            "credits": groups[2] if len(groups) > 2 else "",
                            "grade": groups[3] if len(groups) > 3 else "",
                            "marks": groups[4] if len(groups) > 4 else ""
                        }
                        subjects.append(subject)
                        break
        
        if subjects:
            parsed["subjects"] = subjects
        
        # Extract dates
        date_pattern = r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})"
        dates = re.findall(date_pattern, text)
        if dates:
            parsed["result_info"]["exam_dates"] = dates
        
        # Try to identify VTU-specific information
        if "VTU" in text.upper() or "VISVESVARAYA" in text.upper():
            parsed["institution_info"]["university"] = "Visvesvaraya Technological University"
        
        # Count total subjects
        if subjects:
            parsed["summary"]["total_subjects"] = len(subjects)
            
            # Calculate pass/fail count
            passed = sum(1 for s in subjects if s.get("grade", "").upper() in ["A+", "A", "B+", "B", "C", "P"])
            failed = len(subjects) - passed
            parsed["summary"]["subjects_passed"] = passed
            parsed["summary"]["subjects_failed"] = failed
        
        result_data["parsed_data"] = parsed
        
    except Exception as e:
        print(f"Error parsing text for {filename}: {e}")
        result_data["parsing_error"] = str(e)
    
    return result_data

def extract_data_from_images():
    """
    Extract data from all images and convert to JSON files.
    """
    # Define paths
    images_folder = os.path.join("4th Sem Results", "Images")
    output_folder = os.path.join("4th Sem Results", "JSON_Data")
    
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
    
    print(f"Found {len(image_files)} image files to process...")
    
    # Display files to be processed
    print("\nImage files to process:")
    for i, (_, filename) in enumerate(image_files[:10], 1):  # Show first 10
        print(f"{i:2d}. {filename}")
    if len(image_files) > 10:
        print(f"    ... and {len(image_files) - 10} more files")
    
    # Ask for confirmation
    print(f"\nThis will extract text from {len(image_files)} images and create JSON files")
    print(f"JSON files will be saved in: {output_folder}")
    confirm = input("Do you want to proceed? (y/n): ").lower().strip()
    
    if confirm != 'y' and confirm != 'yes':
        print("Operation cancelled.")
        return
    
    # Process images
    processed_count = 0
    errors = []
    
    print(f"\nStarting OCR extraction...")
    print("=" * 60)
    
    for i, (image_path, image_filename) in enumerate(image_files, 1):
        try:
            print(f"Processing {i}/{len(image_files)}: {image_filename}")
            
            # Extract text from image
            extracted_text = extract_text_from_image(image_path)
            
            if not extracted_text:
                print(f"  ⚠ No text extracted from {image_filename}")
                continue
            
            # Parse the extracted text
            result_data = parse_vtu_result_text(extracted_text, image_filename)
            
            # Create JSON filename
            base_name = os.path.splitext(image_filename)[0]
            json_filename = f"{base_name}.json"
            json_path = os.path.join(output_folder, json_filename)
            
            # Save JSON data
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            # Show brief info about extracted data
            parsed = result_data.get("parsed_data", {})
            student_info = parsed.get("student_info", {})
            usn = student_info.get("usn", "Unknown")
            name = student_info.get("name", "Unknown")
            
            print(f"  ✓ Saved: {json_filename}")
            print(f"    USN: {usn}, Name: {name[:30]}{'...' if len(name) > 30 else ''}")
            print(f"    Text length: {len(extracted_text)} characters")
            
            processed_count += 1
            
        except Exception as e:
            error_msg = f"Error processing {image_filename}: {str(e)}"
            print(f"  ✗ {error_msg}")
            errors.append(error_msg)
    
    # Summary
    print("\n" + "=" * 60)
    print("OCR EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Successfully processed: {processed_count}/{len(image_files)} image files")
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
        print(f"\n✓ OCR extraction completed!")
        print(f"Check the '{output_folder}' folder for JSON files.")
        
        # Create a summary JSON file
        try:
            summary_data = {
                "extraction_summary": {
                    "timestamp": datetime.now().isoformat(),
                    "total_images": len(image_files),
                    "processed_successfully": processed_count,
                    "errors": len(errors),
                    "output_folder": output_folder
                },
                "files_processed": [filename for _, filename in image_files[:processed_count]]
            }
            
            summary_path = os.path.join(output_folder, "_extraction_summary.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            print(f"Summary saved to: _extraction_summary.json")
            
        except Exception as e:
            print(f"Could not create summary file: {e}")
    else:
        print(f"\n✗ No files were processed successfully.")

def check_dependencies():
    """Check if required dependencies are available."""
    try:
        import pytesseract
        from PIL import Image
        import cv2
        
        # Try to find and set Tesseract path
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
        ]
        
        tesseract_found = False
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                tesseract_found = True
                print(f"✓ Found Tesseract at: {path}")
                break
        
        if not tesseract_found:
            print("✗ Tesseract OCR executable not found.")
            print("Searched in common locations:")
            for path in possible_paths:
                print(f"  - {path}")
            print("\nPlease install Tesseract OCR:")
            print("- Windows: winget install UB-Mannheim.TesseractOCR")
            print("- Or download from: https://github.com/UB-Mannheim/tesseract/wiki")
            return False
        
        # Test tesseract installation
        try:
            version = pytesseract.get_tesseract_version()
            print(f"✓ Tesseract OCR version: {version}")
        except Exception as e:
            print(f"✗ Error testing Tesseract: {e}")
            return False
            
        print("✓ Required libraries are installed.")
        return True
        
    except ImportError as e:
        print("✗ Missing required libraries.")
        print("\nTo install required packages, run:")
        print("pip install pytesseract pillow opencv-python")
        return False

if __name__ == "__main__":
    print("Image to JSON Converter (OCR)")
    print("=" * 45)
    
    # Check dependencies first
    if not check_dependencies():
        print("\nPlease install the missing dependencies and try again.")
        input("Press Enter to exit...")
        sys.exit(1)
    
    try:
        extract_data_from_images()
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to exit...")