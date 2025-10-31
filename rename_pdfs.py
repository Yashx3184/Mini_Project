import os
import glob

def rename_pdfs_sequentially():
    """
    Rename all PDF files in the '4th Sem Results' folder to VTU_01.pdf, VTU_02.pdf, etc.
    """
    # Define the folder path
    folder_path = "4th Sem Results"
    
    # Check if the folder exists
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' not found!")
        return
    
    # Get all files in the folder and filter for PDF files manually
    try:
        all_files = os.listdir(folder_path)
        all_pdf_files = []
        
        for filename in all_files:
            if filename.lower().endswith('.pdf'):
                full_path = os.path.join(folder_path, filename)
                all_pdf_files.append(full_path)
                
    except Exception as e:
        print(f"Error reading folder: {e}")
        return
    
    if not all_pdf_files:
        print("No PDF files found in the folder!")
        return
    
    print(f"Found {len(all_pdf_files)} PDF files to rename...")
    
    # Sort the files to ensure consistent ordering
    all_pdf_files.sort()
    
    # Display current files
    print("\nCurrent PDF files:")
    for i, file_path in enumerate(all_pdf_files, 1):
        filename = os.path.basename(file_path)
        print(f"{i:2d}. {filename}")
    
    # Ask for confirmation
    print(f"\nThis will rename all {len(all_pdf_files)} PDF files to VTU_01.pdf, VTU_02.pdf, etc.")
    confirm = input("Do you want to proceed? (y/n): ").lower().strip()
    
    if confirm != 'y' and confirm != 'yes':
        print("Operation cancelled.")
        return
    
    # Rename the files
    renamed_count = 0
    errors = []
    counter = 1
    
    for old_file_path in all_pdf_files:
        try:
            # Create new filename with zero-padded number
            new_filename = f"VTU_{counter:02d}.pdf"
            new_file_path = os.path.join(folder_path, new_filename)
            
            # Check if the new filename already exists and skip if it's the same file
            if os.path.exists(new_file_path):
                if os.path.samefile(old_file_path, new_file_path):
                    print(f"Skipped: {os.path.basename(old_file_path)} (already has correct name)")
                    counter += 1
                    continue
                else:
                    print(f"Warning: {new_filename} already exists. Skipping {os.path.basename(old_file_path)}")
                    continue
            
            # Rename the file
            os.rename(old_file_path, new_file_path)
            print(f"Renamed: {os.path.basename(old_file_path)} → {new_filename}")
            renamed_count += 1
            counter += 1
            
        except Exception as e:
            error_msg = f"Error renaming {os.path.basename(old_file_path)}: {str(e)}"
            print(error_msg)
            errors.append(error_msg)
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Successfully renamed: {renamed_count} files")
    if errors:
        print(f"Errors encountered: {len(errors)}")
        print("Error details:")
        for error in errors:
            print(f"  - {error}")
    
    print(f"\nOperation completed!")

if __name__ == "__main__":
    print("PDF Batch Renamer - VTU Results")
    print("=" * 40)
    
    try:
        rename_pdfs_sequentially()
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
    
    input("\nPress Enter to exit...")