import os
import json
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

# 🔧 Configuration
image_folder = "C:\\Users\\YASHWANTH\\OneDrive\\Desktop\\Vtu_results_project\\4th Sem Results\\Images"  # Folder containing images
output_folder = "C:\\Users\\YASHWANTH\\OneDrive\\Desktop\\Vtu_results_project\\4th Sem Results\\JSON_Data_DOCTR"  # Folder for individual JSON files

# Create output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Load OCR model
model = ocr_predictor(pretrained=True)

# Process each image in the folder
for filename in os.listdir(image_folder):
    if filename.lower().endswith((".png", ".jpg", ".jpeg")):
        image_path = os.path.join(image_folder, filename)
        doc = DocumentFile.from_images(image_path)
        result = model(doc)

        words_data = []
        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    for word in line.words:
                        words_data.append({
                            "text": word.value,
                            "bbox": word.geometry  # [x_min, y_min, x_max, y_max]
                        })

        # Create individual JSON file for this image
        image_output = {
            "image_path": image_path,
            "words": words_data
        }
        
        # Generate output filename
        base_name = os.path.splitext(filename)[0]
        json_filename = f"{base_name}_doctr.json"
        json_path = os.path.join(output_folder, json_filename)
        
        # Save individual JSON file
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(image_output, f, indent=2)
        
        print(f"OCR results saved to {json_filename}")

print(f"All individual JSON files saved to {output_folder}")
