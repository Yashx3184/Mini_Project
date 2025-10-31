import os
from pathlib import Path
import sys

try:
    from pdf2image import convert_from_path
    from PIL import Image
except ImportError as e:
    print("Required libraries not found!")
    print("Please install the required packages using:")
    print("pip install pdf2image pillow")
    print("\nNote: You may also need to install poppler-utils:")
    print("- Windows: Download poppler from https://github.com/oschwartz10612/poppler-windows/releases/")
    print("- Or use: conda install -c conda-forge poppler")
    sys.exit(1)

def convert_pdfs_to_images():
    """
    Convert all PDF files in the '4th Sem Results' folder to images.
    Creates an 'Images' subfolder to store the converted images.
    """
    # Define paths
    pdf_folder = "4th Sem Results"
    output_folder = os.path.join(pdf_folder, "Images")
    
    # Check if PDF folder exists
    if not os.path.exists(pdf_folder):
        print(f"Error: PDF folder '{pdf_folder}' not found!")
        return
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all PDF files
    try:
        all_files = os.listdir(pdf_folder)
        pdf_files = []
        
        for filename in all_files:
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(pdf_folder, filename)
                # Skip if it's a directory
                if os.path.isfile(pdf_path):
                    pdf_files.append((pdf_path, filename))
                    
    except Exception as e:
        print(f"Error reading PDF folder: {e}")
        return
    
    if not pdf_files:
        print("No PDF files found in the folder!")
        return
    
    print(f"Found {len(pdf_files)} PDF files to convert...")
    
    # Display files to be converted
    print("\nPDF files to convert:")
    for i, (_, filename) in enumerate(pdf_files, 1):
        print(f"{i:2d}. {filename}")
    
    # Ask for conversion settings
    print("\nConversion Settings:")
    print("1. Image format: PNG (high quality, larger file size)")
    print("2. Image format: JPEG (good quality, smaller file size)")
    
    format_choice = input("Choose format (1 for PNG, 2 for JPEG) [default: PNG]: ").strip()
    if format_choice == "2":
        image_format = "JPEG"
        file_ext = ".jpg"
    else:
        image_format = "PNG"
        file_ext = ".png"
    
    # DPI setting
    dpi_input = input("Enter DPI (dots per inch) [default: 200]: ").strip()
    try:
        dpi = int(dpi_input) if dpi_input else 200
        if dpi < 50 or dpi > 600:
            print("DPI should be between 50 and 600. Using default 200.")
            dpi = 200
    except ValueError:
        print("Invalid DPI value. Using default 200.")
        dpi = 200
    
    # Ask for confirmation
    print(f"\nThis will convert {len(pdf_files)} PDF files to {image_format} images at {dpi} DPI")
    print(f"Images will be saved in: {output_folder}")
    confirm = input("Do you want to proceed? (y/n): ").lower().strip()
    
    if confirm != 'y' and confirm != 'yes':
        print("Operation cancelled.")
        return
    
    # Convert PDFs to images
    converted_count = 0
    total_pages = 0
    errors = []
    
    print(f"\nStarting conversion...")
    print("=" * 50)
    
    for i, (pdf_path, pdf_filename) in enumerate(pdf_files, 1):
        try:
            print(f"Converting {i}/{len(pdf_files)}: {pdf_filename}")
            
            # Convert PDF to images
            pages = convert_from_path(
                pdf_path, 
                dpi=dpi,
                fmt=image_format.lower(),
                thread_count=4  # Use multiple threads for faster conversion
            )
            
            # Save each page
            base_filename = os.path.splitext(pdf_filename)[0]
            
            if len(pages) == 1:
                # Single page PDF
                image_filename = f"{base_filename}{file_ext}"
                image_path = os.path.join(output_folder, image_filename)
                
                if image_format == "JPEG":
                    pages[0].save(image_path, "JPEG", quality=95, optimize=True)
                else:
                    pages[0].save(image_path, "PNG", optimize=True)
                
                print(f"  → Saved: {image_filename}")
                total_pages += 1
                
            else:
                # Multi-page PDF
                for page_num, page in enumerate(pages, 1):
                    image_filename = f"{base_filename}_page_{page_num:02d}{file_ext}"
                    image_path = os.path.join(output_folder, image_filename)
                    
                    if image_format == "JPEG":
                        page.save(image_path, "JPEG", quality=95, optimize=True)
                    else:
                        page.save(image_path, "PNG", optimize=True)
                    
                    print(f"  → Saved: {image_filename}")
                    total_pages += 1
            
            converted_count += 1
            
        except Exception as e:
            error_msg = f"Error converting {pdf_filename}: {str(e)}"
            print(f"  ✗ {error_msg}")
            errors.append(error_msg)
    
    # Summary
    print("\n" + "=" * 50)
    print("CONVERSION SUMMARY")
    print("=" * 50)
    print(f"Successfully converted: {converted_count}/{len(pdf_files)} PDF files")
    print(f"Total pages converted: {total_pages}")
    print(f"Image format: {image_format}")
    print(f"DPI: {dpi}")
    print(f"Output folder: {output_folder}")
    
    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        print("Error details:")
        for error in errors:
            print(f"  - {error}")
    
    if converted_count > 0:
        print(f"\n✓ Conversion completed successfully!")
        print(f"Check the '{output_folder}' folder for your images.")
    else:
        print(f"\n✗ No files were converted successfully.")

def check_dependencies():
    """Check if required dependencies are available."""
    try:
        import pdf2image
        from PIL import Image
        print("✓ Required libraries are installed.")
        return True
    except ImportError:
        print("✗ Missing required libraries.")
        print("\nTo install required packages, run:")
        print("pip install pdf2image pillow")
        print("\nAdditional system requirements:")
        print("- Windows: Install poppler (download from GitHub or use conda)")
        print("- Linux: sudo apt-get install poppler-utils")
        print("- macOS: brew install poppler")
        return False

if __name__ == "__main__":
    print("PDF to Image Converter")
    print("=" * 40)
    
    # Check dependencies first
    if not check_dependencies():
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    try:
        convert_pdfs_to_images()
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
    
    input("\nPress Enter to exit...")