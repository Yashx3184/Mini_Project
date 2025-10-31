#!/usr/bin/env python3
"""
Bio-Label JSON Data Script
==========================
This script processes JSON files from the pdfplumber extraction and applies bio-labeling
to create enhanced JSON files with performance metrics and subject classifications.

Features:
- Analyzes student performance and assigns overall labels
- Classifies subjects based on performance levels
- Calculates performance metrics and percentages
- Creates structured output with enhanced metadata

Author: AI Assistant
Date: October 31, 2025
"""

import os
import json
import math
from datetime import datetime
from typing import Dict, List, Any, Tuple

class BioLabelProcessor:
    """Class to handle bio-labeling of VTU result data"""
    
    def __init__(self):
        self.input_folder = "JSON_Data_Pdfplumber"
        self.output_folder = "JSON_Data_BioLabeled"
        self.summary_data = []
        
    def setup_directories(self):
        """Create output directory if it doesn't exist"""
        try:
            if not os.path.exists(self.output_folder):
                os.makedirs(self.output_folder)
                print(f"✓ Created output directory: {self.output_folder}")
            else:
                print(f"✓ Output directory exists: {self.output_folder}")
            return True
        except Exception as e:
            print(f"✗ Error creating directory: {e}")
            return False
    
    def classify_subject_performance(self, total_marks: int, grade: str) -> str:
        """
        Classify subject performance based on marks and grade
        
        Args:
            total_marks: Total marks obtained
            grade: Grade (P/F)
            
        Returns:
            Performance label string
        """
        if grade == "F":
            return "Fail_Subject"
        elif grade == "P":
            if total_marks >= 75:
                return "Strong_Subject"
            elif total_marks >= 50:
                return "Pass_Subject"
            else:
                return "Pass_Subject"  # Still passed but low marks
        else:
            return "Unknown"
    
    def classify_student_performance(self, pass_percentage: float, total_subjects: int, subjects_failed: int) -> Tuple[str, str]:
        """
        Classify overall student performance
        
        Args:
            pass_percentage: Percentage of subjects passed
            total_subjects: Total number of subjects
            subjects_failed: Number of failed subjects
            
        Returns:
            Tuple of (overall_label, performance_level)
        """
        # Overall label based on pass percentage and failure count
        if pass_percentage >= 90:
            overall_label = "Excellent"
        elif pass_percentage >= 75:
            overall_label = "Good"
        elif pass_percentage >= 60:
            overall_label = "Average"
        elif pass_percentage >= 40:
            overall_label = "At Risk"
        else:
            overall_label = "Critical"
        
        # Performance level based on detailed analysis
        if subjects_failed == 0:
            performance_level = "Excellent"
        elif subjects_failed <= 2 and pass_percentage >= 70:
            performance_level = "Good"
        elif subjects_failed <= 3 and pass_percentage >= 50:
            performance_level = "Moderate"
        elif subjects_failed <= 4 and pass_percentage >= 40:
            performance_level = "Below Average"
        else:
            performance_level = "Poor"
            
        return overall_label, performance_level
    
    def process_subjects(self, subjects: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Process subjects and add bio-labels
        
        Args:
            subjects: List of subject dictionaries
            
        Returns:
            Tuple of (processed_subjects, labels_distribution)
        """
        processed_subjects = []
        labels_count = {
            "Pass_Subjects": 0,
            "Fail_Subjects": 0,
            "Strong_Subjects": 0
        }
        
        for subject in subjects:
            try:
                # Clean and convert marks
                total_marks = int(str(subject.get('total_marks', '0')).strip())
                grade = str(subject.get('grade', 'F')).strip().upper()
                internal_marks = int(str(subject.get('internal_marks', '0')).strip())
                external_marks = int(str(subject.get('external_marks', '0')).strip())
                
                # Clean subject name (remove newlines)
                subject_name = str(subject.get('name', '')).replace('\n', ' ').strip()
                
                # Classify subject performance
                subject_label = self.classify_subject_performance(total_marks, grade)
                
                # Count labels
                if subject_label == "Strong_Subject":
                    labels_count["Strong_Subjects"] += 1
                elif subject_label == "Fail_Subject":
                    labels_count["Fail_Subjects"] += 1
                else:  # Pass_Subject
                    labels_count["Pass_Subjects"] += 1
                
                # Create processed subject
                processed_subject = {
                    "code": str(subject.get('code', '')).strip(),
                    "name": subject_name,
                    "internal_marks": internal_marks,
                    "external_marks": external_marks,
                    "total_marks": total_marks,
                    "grade": grade,
                    "label": subject_label
                }
                
                processed_subjects.append(processed_subject)
                
            except (ValueError, TypeError) as e:
                print(f"    ⚠ Warning: Error processing subject {subject.get('code', 'Unknown')}: {e}")
                # Add with default values
                processed_subject = {
                    "code": str(subject.get('code', '')).strip(),
                    "name": str(subject.get('name', '')).replace('\n', ' ').strip(),
                    "internal_marks": 0,
                    "external_marks": 0,
                    "total_marks": 0,
                    "grade": "F",
                    "label": "Fail_Subject"
                }
                processed_subjects.append(processed_subject)
                labels_count["Fail_Subjects"] += 1
        
        return processed_subjects, labels_count
    
    def create_bio_labeled_data(self, original_data: Dict) -> Dict:
        """
        Create bio-labeled version of the JSON data
        
        Args:
            original_data: Original JSON data from pdfplumber
            
        Returns:
            Bio-labeled JSON data
        """
        try:
            # Extract original parsed data
            parsed_data = original_data.get('parsed_data', {})
            student_info = parsed_data.get('student_info', {})
            subjects = parsed_data.get('subjects', [])
            
            # Process subjects and get labels distribution
            processed_subjects, labels_distribution = self.process_subjects(subjects)
            
            # Calculate metrics
            total_subjects = len(processed_subjects)
            subjects_passed = sum(1 for s in processed_subjects if s['grade'] == 'P')
            subjects_failed = total_subjects - subjects_passed
            pass_percentage = round((subjects_passed / total_subjects * 100), 2) if total_subjects > 0 else 0.0
            
            # Classify student performance
            overall_label, performance_level = self.classify_student_performance(
                pass_percentage, total_subjects, subjects_failed
            )
            
            # Create bio-labeled data structure
            bio_labeled_data = {
                "student_info": {
                    "usn": str(student_info.get('usn', '')).strip(),
                    "name": str(student_info.get('name', '')).strip(),
                    "overall_label": overall_label,
                    "pass_percentage": pass_percentage,
                    "performance_level": performance_level
                },
                "subjects": processed_subjects,
                "summary": {
                    "total_subjects": total_subjects,
                    "subjects_passed": subjects_passed,
                    "subjects_failed": subjects_failed,
                    "pass_percentage": pass_percentage,
                    "labels_distribution": labels_distribution
                },
                "metadata": {
                    "original_filename": original_data.get('filename', ''),
                    "extraction_method": original_data.get('extraction_method', 'pdfplumber'),
                    "bio_labeling_timestamp": datetime.now().isoformat(),
                    "bio_labeling_version": "1.0"
                }
            }
            
            return bio_labeled_data
            
        except Exception as e:
            print(f"    ✗ Error creating bio-labeled data: {e}")
            return None
    
    def process_single_file(self, filename: str) -> bool:
        """
        Process a single JSON file
        
        Args:
            filename: Name of the JSON file to process
            
        Returns:
            Success status
        """
        try:
            input_path = os.path.join(self.input_folder, filename)
            
            # Read original JSON
            with open(input_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            
            # Create bio-labeled data
            bio_labeled_data = self.create_bio_labeled_data(original_data)
            
            if bio_labeled_data is None:
                return False
            
            # Create output filename
            base_name = filename.replace('.json', '').replace('_pdfplumber', '')
            output_filename = f"{base_name}_biolabeled.json"
            output_path = os.path.join(self.output_folder, output_filename)
            
            # Save bio-labeled JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(bio_labeled_data, f, indent=2, ensure_ascii=False)
            
            # Add to summary
            self.summary_data.append({
                "original_file": filename,
                "output_file": output_filename,
                "usn": bio_labeled_data['student_info']['usn'],
                "name": bio_labeled_data['student_info']['name'],
                "overall_label": bio_labeled_data['student_info']['overall_label'],
                "pass_percentage": bio_labeled_data['student_info']['pass_percentage'],
                "total_subjects": bio_labeled_data['summary']['total_subjects'],
                "subjects_failed": bio_labeled_data['summary']['subjects_failed']
            })
            
            print(f"  ✓ Processed: {filename} → {output_filename}")
            print(f"    USN: {bio_labeled_data['student_info']['usn']}, "
                  f"Name: {bio_labeled_data['student_info']['name']}")
            print(f"    Label: {bio_labeled_data['student_info']['overall_label']}, "
                  f"Pass%: {bio_labeled_data['student_info']['pass_percentage']}%, "
                  f"Subjects: {bio_labeled_data['summary']['total_subjects']}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Error processing {filename}: {e}")
            return False
    
    def create_summary_report(self):
        """Create a summary report of all processed files"""
        try:
            summary_report = {
                "bio_labeling_summary": {
                    "timestamp": datetime.now().isoformat(),
                    "total_files_processed": len(self.summary_data),
                    "input_folder": self.input_folder,
                    "output_folder": self.output_folder
                },
                "performance_distribution": {
                    "Excellent": len([s for s in self.summary_data if s['overall_label'] == 'Excellent']),
                    "Good": len([s for s in self.summary_data if s['overall_label'] == 'Good']),
                    "Average": len([s for s in self.summary_data if s['overall_label'] == 'Average']),
                    "At Risk": len([s for s in self.summary_data if s['overall_label'] == 'At Risk']),
                    "Critical": len([s for s in self.summary_data if s['overall_label'] == 'Critical'])
                },
                "statistics": {
                    "average_pass_percentage": round(sum(s['pass_percentage'] for s in self.summary_data) / len(self.summary_data), 2) if self.summary_data else 0,
                    "total_students_at_risk": len([s for s in self.summary_data if s['overall_label'] in ['At Risk', 'Critical']]),
                    "average_subjects_per_student": round(sum(s['total_subjects'] for s in self.summary_data) / len(self.summary_data), 1) if self.summary_data else 0
                },
                "detailed_results": self.summary_data
            }
            
            # Save summary report
            summary_path = os.path.join(self.output_folder, "_bio_labeling_summary.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_report, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Summary report saved: {summary_path}")
            
        except Exception as e:
            print(f"✗ Error creating summary report: {e}")
    
    def process_all_files(self):
        """Process all JSON files in the input folder"""
        print("Bio-Label JSON Data Processor")
        print("=" * 50)
        
        # Setup directories
        if not self.setup_directories():
            return
        
        # Check if input folder exists
        if not os.path.exists(self.input_folder):
            print(f"✗ Input folder not found: {self.input_folder}")
            return
        
        # Get all JSON files
        json_files = [f for f in os.listdir(self.input_folder) 
                     if f.endswith('.json') and not f.startswith('_')]
        
        if not json_files:
            print(f"✗ No JSON files found in {self.input_folder}")
            return
        
        print(f"\nFound {len(json_files)} JSON files to process...")
        
        # Process each file
        successful = 0
        failed = 0
        
        for i, filename in enumerate(json_files, 1):
            print(f"\nProcessing {i}/{len(json_files)}: {filename}")
            
            if self.process_single_file(filename):
                successful += 1
            else:
                failed += 1
        
        # Create summary report
        if self.summary_data:
            self.create_summary_report()
        
        # Final summary
        print("\n" + "=" * 70)
        print("BIO-LABELING SUMMARY")
        print("=" * 70)
        print(f"Successfully processed: {successful}/{len(json_files)} files")
        print(f"Failed: {failed}/{len(json_files)} files")
        print(f"Output folder: {self.output_folder}")
        
        if successful > 0:
            print(f"\n✓ Bio-labeling completed!")
            print(f"Check the '{self.output_folder}' folder for bio-labeled JSON files.")
        
        return successful, failed

def main():
    """Main function"""
    try:
        processor = BioLabelProcessor()
        processor.process_all_files()
        
        print("\nPress Enter to exit...")
        input()
        
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        print("\nPress Enter to exit...")
        input()

if __name__ == "__main__":
    main()