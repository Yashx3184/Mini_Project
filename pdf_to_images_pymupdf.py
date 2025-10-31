import os
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
    from PIL import Image
except ImportError as e:
    print("Required libraries not found!")
    print("Please install the required packages using:")
    print("pip install PyMuPDF pillow")
    print("\nPyMuPDF is a self-contained library that doesn't require additional system dependencies.")
    sys.exit(1)

def convert_pdfs_to_images():
    """
    Convert all PDF files in the '4th Sem Results' folder to images using PyMuPDF.
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
        image_format = "PNG"  # PyMuPDF outputs PNG, we'll convert to JPEG if needed
        output_format = "JPEG"
        file_ext = ".jpg"
    else:
        image_format = "PNG"
        output_format = "PNG"
        file_ext = ".png"
    
    # DPI/Resolution setting
    dpi_input = input("Enter DPI (dots per inch) [default: 200]: ").strip()
    try:
        dpi = int(dpi_input) if dpi_input else 200
        if dpi < 50 or dpi > 600:
            print("DPI should be between 50 and 600. Using default 200.")
            dpi = 200
    except ValueError:
        print("Invalid DPI value. Using default 200.")
        dpi = 200
    
    # Calculate zoom factor (PyMuPDF uses zoom instead of DPI)
    # Standard PDF resolution is 72 DPI, so zoom = target_dpi / 72
    zoom = dpi / 72.0
    
    # Ask for confirmation
    print(f"\nThis will convert {len(pdf_files)} PDF files to {output_format} images at {dpi} DPI")
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
            
            # Open PDF document
            doc = fitz.open(pdf_path)
            
            # Get base filename without extension
            base_filename = os.path.splitext(pdf_filename)[0]
            
            # Convert each page
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Create transformation matrix for desired resolution
                mat = fitz.Matrix(zoom, zoom)
                
                # Render page to pixmap
                pix = page.get_pixmap(matrix=mat)
                
                # Determine filename
                if len(doc) == 1:
                    # Single page PDF
                    image_filename = f"{base_filename}{file_ext}"
                else:
                    # Multi-page PDF
                    image_filename = f"{base_filename}_page_{page_num + 1:02d}{file_ext}"
                
                image_path = os.path.join(output_folder, image_filename)
                
                # Save image
                if output_format == "PNG":
                    pix.save(image_path)
                else:
                    # Convert to JPEG using PIL for better quality control
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    # Convert RGBA to RGB for JPEG (if needed)
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')
                    img.save(image_path, "JPEG", quality=95, optimize=True)
                
                print(f"  → Saved: {image_filename}")
                total_pages += 1
            
            # Close document
            doc.close()
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
    print(f"Image format: {output_format}")
    print(f"DPI: {dpi} (zoom factor: {zoom:.2f})")
    print(f"Output folder: {output_folder}")
    
    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        print("Error details:")
        for error in errors:
            print(f"  - {error}")
    
    if converted_count > 0:
        print(f"\n✓ Conversion completed successfully!")
        print(f"Check the '{output_folder}' folder for your images.")
        
        # Show sample of created files
        try:
            image_files = [f for f in os.listdir(output_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if image_files:
                print(f"\nSample of created image files:")
                for filename in sorted(image_files)[:5]:  # Show first 5 files
                    file_path = os.path.join(output_folder, filename)
                    file_size = os.path.getsize(file_path)
                    size_mb = file_size / (1024 * 1024)
                    print(f"  - {filename} ({size_mb:.2f} MB)")
                if len(image_files) > 5:
                    print(f"  ... and {len(image_files) - 5} more files")
        except Exception as e:
            print(f"Could not list created files: {e}")
    else:
        print(f"\n✗ No files were converted successfully.")

def check_dependencies():
    """Check if required dependencies are available."""
    try:
        import fitz
        from PIL import Image
        print("✓ Required libraries are installed.")
        print(f"PyMuPDF version: {fitz.version[0]}")
        return True
    except ImportError:
        print("✗ Missing required libraries.")
        print("\nTo install required packages, run:")
        print("pip install PyMuPDF pillow")
        print("\nPyMuPDF is self-contained and doesn't require additional system dependencies like Poppler.")
        return False

if __name__ == "__main__":
    print("PDF to Image Converter (PyMuPDF)")
    print("=" * 45)
    
    # Import io here since we might need it for JPEG conversion
    import io
    
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
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to exit...")