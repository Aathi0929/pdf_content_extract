"""
Utility functions for USB PD Parser
Includes validation, testing, and helper functions
"""

import json
import jsonlines
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ParserValidator:
    """Utility class for validating parser output"""
    
    def __init__(self):
        self.validation_results = {}
    
    def validate_jsonl_schema(self, jsonl_file: str) -> Dict[str, Any]:
        """Validate JSONL file against expected schema"""
        required_fields = ['section_id', 'title', 'page', 'level', 'parent_id', 'full_path', 'doc_title', 'tags']
        
        validation_result = {
            'file': jsonl_file,
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'missing_fields': [],
            'field_types_valid': True,
            'errors': []
        }
        
        try:
            with jsonlines.open(jsonl_file, 'r') as reader:
                for i, record in enumerate(reader):
                    validation_result['total_records'] += 1
                    
                    # Check required fields
                    missing_fields = [field for field in required_fields if field not in record]
                    if missing_fields:
                        validation_result['missing_fields'].extend(missing_fields)
                        validation_result['invalid_records'] += 1
                        validation_result['errors'].append(f"Record {i+1}: Missing fields {missing_fields}")
                        continue
                    
                    # Check field types
                    type_checks = {
                        'section_id': str,
                        'title': str,
                        'page': int,
                        'level': int,
                        'full_path': str,
                        'doc_title': str,
                        'tags': list
                    }
                    
                    type_errors = []
                    for field, expected_type in type_checks.items():
                        if not isinstance(record[field], expected_type):
                            type_errors.append(f"{field}: expected {expected_type.__name__}, got {type(record[field]).__name__}")
                    
                    if type_errors:
                        validation_result['field_types_valid'] = False
                        validation_result['invalid_records'] += 1
                        validation_result['errors'].append(f"Record {i+1}: Type errors: {', '.join(type_errors)}")
                        continue
                    
                    validation_result['valid_records'] += 1
        
        except Exception as e:
            validation_result['errors'].append(f"File reading error: {str(e)}")
        
        return validation_result
    
    def validate_hierarchy(self, jsonl_file: str) -> Dict[str, Any]:
        """Validate section hierarchy consistency"""
        hierarchy_result = {
            'file': jsonl_file,
            'total_sections': 0,
            'orphaned_sections': [],
            'level_inconsistencies': [],
            'parent_child_mismatches': []
        }
        
        try:
            sections = []
            with jsonlines.open(jsonl_file, 'r') as reader:
                sections = list(reader)
            
            hierarchy_result['total_sections'] = len(sections)
            
            # Create lookup dictionary
            section_lookup = {s['section_id']: s for s in sections}
            
            for section in sections:
                section_id = section['section_id']
                parent_id = section.get('parent_id')
                level = section['level']
                
                # Check if parent exists (for non-root sections)
                if parent_id and parent_id not in section_lookup:
                    hierarchy_result['orphaned_sections'].append({
                        'section_id': section_id,
                        'title': section['title'],
                        'missing_parent': parent_id
                    })
                
                # Check level consistency
                expected_level = section_id.count('.') + 1
                if level != expected_level:
                    hierarchy_result['level_inconsistencies'].append({
                        'section_id': section_id,
                        'title': section['title'],
                        'actual_level': level,
                        'expected_level': expected_level
                    })
                
                # Check parent-child relationship
                if parent_id and parent_id in section_lookup:
                    parent_section = section_lookup[parent_id]
                    expected_parent_level = level - 1
                    if parent_section['level'] != expected_parent_level:
                        hierarchy_result['parent_child_mismatches'].append({
                            'section_id': section_id,
                            'parent_id': parent_id,
                            'section_level': level,
                            'parent_level': parent_section['level'],
                            'expected_parent_level': expected_parent_level
                        })
        
        except Exception as e:
            hierarchy_result['error'] = str(e)
        
        return hierarchy_result
    
    def generate_comprehensive_report(self, toc_file: str, spec_file: str, output_file: str = 'comprehensive_validation_report.xlsx'):
        """Generate comprehensive validation report"""
        print(" Generating comprehensive validation report...")
        
        # Schema validation
        toc_schema_validation = self.validate_jsonl_schema(toc_file)
        spec_schema_validation = self.validate_jsonl_schema(spec_file)
        
        # Hierarchy validation
        toc_hierarchy_validation = self.validate_hierarchy(toc_file)
        spec_hierarchy_validation = self.validate_hierarchy(spec_file)
        
        # Create Excel report
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Schema validation summary
            schema_data = []
            for validation in [toc_schema_validation, spec_schema_validation]:
                schema_data.append({
                    'File': Path(validation['file']).name,
                    'Total Records': validation['total_records'],
                    'Valid Records': validation['valid_records'],
                    'Invalid Records': validation['invalid_records'],
                    'Field Types Valid': validation['field_types_valid'],
                    'Error Count': len(validation['errors'])
                })
            
            pd.DataFrame(schema_data).to_excel(writer, sheet_name='Schema Validation', index=False)
            
            # Hierarchy validation summary
            hierarchy_data = []
            for validation in [toc_hierarchy_validation, spec_hierarchy_validation]:
                hierarchy_data.append({
                    'File': Path(validation['file']).name,
                    'Total Sections': validation['total_sections'],
                    'Orphaned Sections': len(validation['orphaned_sections']),
                    'Level Inconsistencies': len(validation['level_inconsistencies']),
                    'Parent-Child Mismatches': len(validation['parent_child_mismatches'])
                })
            
            pd.DataFrame(hierarchy_data).to_excel(writer, sheet_name='Hierarchy Validation', index=False)
            
            # Detailed errors
            all_errors = []
            for validation in [toc_schema_validation, spec_schema_validation]:
                for error in validation['errors']:
                    all_errors.append({
                        'File': Path(validation['file']).name,
                        'Error': error
                    })
            
            if all_errors:
                pd.DataFrame(all_errors).to_excel(writer, sheet_name='Detailed Errors', index=False)
        
        print(f" Comprehensive validation report saved to {output_file}")

def analyze_parsing_coverage(toc_file: str, spec_file: str):
    """Analyze parsing coverage between ToC and full document"""
    print(" Analyzing parsing coverage...")
    
    try:
        # Load data
        with jsonlines.open(toc_file, 'r') as reader:
            toc_sections = list(reader)
        
        with jsonlines.open(spec_file, 'r') as reader:
            spec_sections = list(reader)
        
        toc_ids = set(s['section_id'] for s in toc_sections)
        spec_ids = set(s['section_id'] for s in spec_sections)
        
        # Calculate metrics
        total_toc = len(toc_ids)
        total_spec = len(spec_ids)
        common = len(toc_ids & spec_ids)
        toc_only = len(toc_ids - spec_ids)
        spec_only = len(spec_ids - toc_ids)
        
        coverage_percentage = (common / total_toc * 100) if total_toc > 0 else 0
        
        print(f" Coverage Analysis Results:")
        print(f"   ToC sections: {total_toc}")
        print(f"   Spec sections: {total_spec}")
        print(f"   Common sections: {common}")
        print(f"   ToC only: {toc_only}")
        print(f"   Spec only: {spec_only}")
        print(f"   Coverage: {coverage_percentage:.1f}%")
        
        if toc_only > 0:
            print(f"\n⚠  {toc_only} sections found in ToC but not in full document parsing")
        
        if spec_only > 0:
            print(f"  {spec_only} sections found in full document but not in ToC")
    
    except Exception as e:
        print(f" Error analyzing coverage: {e}")

def create_sample_test_data():
    """Create sample test data for validation"""
    print(" Creating sample test data...")
    
    # Create a sample with intentional errors for testing
    test_data = [
        {
            "section_id": "1",
            "title": "Introduction",
            "page": 10,
            "level": 1,
            "parent_id": None,
            "full_path": "1 Introduction",
            "doc_title": "Test Document",
            "tags": ["intro"]
        },
        {
            "section_id": "1.1",
            "title": "Overview",
            "page": 11,
            "level": 2,
            "parent_id": "1",
            "full_path": "1.1 Overview",
            "doc_title": "Test Document",
            "tags": ["overview"]
        },
        {
            # Intentional error: missing parent "1.2"
            "section_id": "1.2.1",
            "title": "Orphaned Section",
            "page": 15,
            "level": 3,
            "parent_id": "1.2",
            "full_path": "1.2.1 Orphaned Section",
            "doc_title": "Test Document",
            "tags": []
        },
        {
            # Intentional error: wrong level (should be 2, not 3)
            "section_id": "2",
            "title": "Wrong Level Section",
            "page": 20,
            "level": 3,
            "parent_id": None,
            "full_path": "2 Wrong Level Section",
            "doc_title": "Test Document",
            "tags": []
        }
    ]
    
    with jsonlines.open('test_data.jsonl', 'w') as writer:
        for record in test_data:
            writer.write(record)
    
    print(" Sample test data created: test_data.jsonl")

def main():
    """Main function for utility script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='USB PD Parser Utilities')
    parser.add_argument('--validate', action='store_true', help='Run validation tests')
    parser.add_argument('--coverage', action='store_true', help='Analyze parsing coverage')
    parser.add_argument('--test-data', action='store_true', help='Create sample test data')
    parser.add_argument('--toc-file', default='usb_pd_toc.jsonl', help='ToC JSONL file')
    parser.add_argument('--spec-file', default='usb_pd_spec.jsonl', help='Spec JSONL file')
    
    args = parser.parse_args()
    
    if args.test_data:
        create_sample_test_data()
    
    if args.validate:
        validator = ParserValidator()
        if Path(args.toc_file).exists() and Path(args.spec_file).exists():
            validator.generate_comprehensive_report(args.toc_file, args.spec_file)
        else:
            print(" JSONL files not found. Run parser first or use --test-data to create sample data.")
    
    if args.coverage:
        if Path(args.toc_file).exists() and Path(args.spec_file).exists():
            analyze_parsing_coverage(args.toc_file, args.spec_file)
        else:
            print(" JSONL files not found. Run parser first.")
    
    if not any([args.validate, args.coverage, args.test_data]):
        print("  USB PD Parser Utilities")
        print("Usage:")
        print("  --validate: Run validation tests")
        print("  --coverage: Analyze parsing coverage")
        print("  --test-data: Create sample test data")

if __name__ == "__main__":
    main()

