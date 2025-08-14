"""
USB Power Delivery (USB PD) Specification PDF Parser

This script parses USB PD specification PDF files and extracts:
1. Table of Contents (ToC) hierarchy
2. All sections and subsections
3. Generates structured JSONL output files
4. Creates validation reports in Excel format
"""

import re
import json
import pandas as pd
import pdfplumber
import fitz  # PyMuPDF
import jsonlines
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Section:
    """Data class representing a document section"""
    section_id: str
    title: str
    page: int
    level: int
    parent_id: Optional[str]
    full_path: str
    doc_title: str
    tags: List[str]

class USBPDParser:
    """Main parser class for USB PD specification documents"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.doc_title = "USB Power Delivery Specification"
        self.sections: List[Section] = []
        self.toc_sections: List[Section] = []
        
        # Regex patterns for section identification
        self.section_patterns = [
            # Pattern: "2.1.2 Section Title ... 53"
            r'^(\d+(?:\.\d+)*)\s+([^.]+?)\s*\.{2,}\s*(\d+)$',
            # Pattern: "2.1.2 Section Title 53"
            r'^(\d+(?:\.\d+)*)\s+([^0-9]+?)\s+(\d+)$',
            # Pattern with tabs: "2.1.2\tSection Title\t53"
            r'^(\d+(?:\.\d+)*)\s*\t+([^\t]+?)\t+(\d+)$'
        ]
        
    def extract_document_title(self) -> str:
        """Extract document title from the first few pages"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # Check first 3 pages for title
                for page_num in range(min(3, len(pdf.pages))):
                    page = pdf.pages[page_num]
                    text = page.extract_text()
                    
                    if text:
                        lines = text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if 'usb' in line.lower() and ('power delivery' in line.lower() or 'pd' in line.lower()):
                                if 'specification' in line.lower() or 'spec' in line.lower():
                                    return line
                                    
        except Exception as e:
            logger.warning(f"Could not extract document title: {e}")
            
        return "USB Power Delivery Specification"
    
    def extract_toc_from_pdf(self) -> List[Section]:
        """Extract Table of Contents from PDF"""
        logger.info("Extracting Table of Contents...")
        toc_sections = []
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # Look for ToC in first 20 pages
                for page_num in range(min(20, len(pdf.pages))):
                    page = pdf.pages[page_num]
                    text = page.extract_text()
                    
                    if not text:
                        continue
                        
                    lines = text.split('\n')
                    
                    # Check if this page contains ToC
                    is_toc_page = any('contents' in line.lower() or 'table of contents' in line.lower() 
                                    for line in lines[:5])
                    
                    if not is_toc_page:
                        # Also check for numbered sections
                        numbered_lines = [line for line in lines if re.match(r'^\d+(?:\.\d+)*\s+', line.strip())]
                        if len(numbered_lines) < 3:
                            continue
                    
                    # Extract sections from this page
                    page_sections = self._extract_sections_from_text(lines, page_num + 1)
                    toc_sections.extend(page_sections)
                    
        except Exception as e:
            logger.error(f"Error extracting ToC: {e}")
            
        return toc_sections
    
    def _extract_sections_from_text(self, lines: List[str], page_num: int) -> List[Section]:
        """Extract sections from text lines using regex patterns"""
        sections = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try each regex pattern
            for pattern in self.section_patterns:
                match = re.match(pattern, line)
                if match:
                    section_id = match.group(1)
                    title = match.group(2).strip()
                    try:
                        page_ref = int(match.group(3))
                    except (ValueError, IndexError):
                        page_ref = page_num
                    
                    # Calculate level based on dots in section_id
                    level = section_id.count('.') + 1
                    
                    # Determine parent_id
                    parent_id = None
                    if '.' in section_id:
                        parent_parts = section_id.split('.')
                        parent_id = '.'.join(parent_parts[:-1])
                    
                    # Generate full_path
                    full_path = f"{section_id} {title}"
                    
                    # Generate tags based on title content
                    tags = self._generate_tags(title)
                    
                    section = Section(
                        section_id=section_id,
                        title=title,
                        page=page_ref,
                        level=level,
                        parent_id=parent_id,
                        full_path=full_path,
                        doc_title=self.doc_title,
                        tags=tags
                    )
                    
                    sections.append(section)
                    break
                    
        return sections
    
    def _generate_tags(self, title: str) -> List[str]:
        """Generate semantic tags based on section title"""
        tags = []
        title_lower = title.lower()
        
        # Define tag mappings
        tag_mappings = {
            'power': ['power'],
            'contract': ['contracts'],
            'negotiation': ['negotiation'],
            'communication': ['communication'],
            'cable': ['cable'],
            'device': ['devices'],
            'protocol': ['protocol'],
            'state': ['state-machine'],
            'message': ['messaging'],
            'data': ['data'],
            'control': ['control'],
            'source': ['source'],
            'sink': ['sink'],
            'vbus': ['vbus'],
            'cc': ['cc-line'],
            'sop': ['sop'],
            'collision': ['collision', 'avoidance'],
            'revision': ['revision'],
            'compatibility': ['compatibility'],
            'introduction': ['intro'],
            'overview': ['overview']
        }
        
        for keyword, tag_list in tag_mappings.items():
            if keyword in title_lower:
                tags.extend(tag_list)
        
        return list(set(tags))  # Remove duplicates
    
    def extract_all_sections_from_pdf(self) -> List[Section]:
        """Extract all sections from the entire PDF document"""
        logger.info("Extracting all sections from PDF...")
        all_sections = []
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(tqdm(pdf.pages, desc="Processing pages")):
                    text = page.extract_text()
                    
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    
                    # Look for section headers in the page content
                    for line in lines:
                        line = line.strip()
                        
                        # Check if line looks like a section header
                        if self._is_section_header(line):
                            section = self._parse_section_header(line, page_num + 1)
                            if section:
                                all_sections.append(section)
                                
        except Exception as e:
            logger.error(f"Error extracting all sections: {e}")
            
        return all_sections
    
    def _is_section_header(self, line: str) -> bool:
        """Determine if a line is likely a section header"""
        # Check for numbered section pattern at start of line
        if re.match(r'^\d+(?:\.\d+)*\s+[A-Z]', line):
            return True
            
        # Check for all caps headers
        if line.isupper() and len(line.split()) <= 8 and len(line) > 5:
            return True
            
        return False
    
    def _parse_section_header(self, line: str, page_num: int) -> Optional[Section]:
        """Parse a section header line into a Section object"""
        # Try to match numbered section
        match = re.match(r'^(\d+(?:\.\d+)*)\s+(.+)$', line)
        if match:
            section_id = match.group(1)
            title = match.group(2).strip()
            
            level = section_id.count('.') + 1
            parent_id = None
            if '.' in section_id:
                parent_parts = section_id.split('.')
                parent_id = '.'.join(parent_parts[:-1])
            
            full_path = f"{section_id} {title}"
            tags = self._generate_tags(title)
            
            return Section(
                section_id=section_id,
                title=title,
                page=page_num,
                level=level,
                parent_id=parent_id,
                full_path=full_path,
                doc_title=self.doc_title,
                tags=tags
            )
        
        return None
    
    def save_jsonl(self, sections: List[Section], filename: str):
        """Save sections to JSONL file"""
        output_path = Path(filename)
        logger.info(f"Saving {len(sections)} sections to {output_path}")
        
        try:
            with jsonlines.open(output_path, 'w') as writer:
                for section in sections:
                    writer.write(asdict(section))
            logger.info(f"Successfully saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving JSONL file {filename}: {e}")
    
    def generate_validation_report(self, toc_sections: List[Section], all_sections: List[Section]):
        """Generate Excel validation report comparing ToC and parsed sections"""
        logger.info("Generating validation report...")
        
        try:
            # Create DataFrames
            toc_df = pd.DataFrame([asdict(s) for s in toc_sections])
            all_df = pd.DataFrame([asdict(s) for s in all_sections])
            
            # Summary statistics
            summary_data = {
                'Metric': [
                    'Total ToC Sections',
                    'Total Parsed Sections',
                    'Sections in Both',
                    'ToC Only',
                    'Parsed Only',
                    'Level 1 Sections (ToC)',
                    'Level 2 Sections (ToC)',
                    'Level 3+ Sections (ToC)'
                ],
                'Count': [
                    len(toc_sections),
                    len(all_sections),
                    len(set(s.section_id for s in toc_sections) & set(s.section_id for s in all_sections)),
                    len(set(s.section_id for s in toc_sections) - set(s.section_id for s in all_sections)),
                    len(set(s.section_id for s in all_sections) - set(s.section_id for s in toc_sections)),
                    len([s for s in toc_sections if s.level == 1]),
                    len([s for s in toc_sections if s.level == 2]),
                    len([s for s in toc_sections if s.level >= 3])
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            
            # Find mismatches
            toc_ids = set(s.section_id for s in toc_sections)
            all_ids = set(s.section_id for s in all_sections)
            
            missing_in_parsed = toc_ids - all_ids
            extra_in_parsed = all_ids - toc_ids
            
            mismatch_data = []
            for section_id in missing_in_parsed:
                toc_section = next(s for s in toc_sections if s.section_id == section_id)
                mismatch_data.append({
                    'Section ID': section_id,
                    'Title': toc_section.title,
                    'Issue': 'Missing in parsed sections',
                    'ToC Page': toc_section.page,
                    'Parsed Page': 'N/A'
                })
            
            for section_id in extra_in_parsed:
                all_section = next(s for s in all_sections if s.section_id == section_id)
                mismatch_data.append({
                    'Section ID': section_id,
                    'Title': all_section.title,
                    'Issue': 'Extra in parsed sections',
                    'ToC Page': 'N/A',
                    'Parsed Page': all_section.page
                })
            
            mismatch_df = pd.DataFrame(mismatch_data)
            
            # Save to Excel
            with pd.ExcelWriter('usb_pd_validation_report.xlsx', engine='openpyxl') as writer:
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                if not toc_df.empty:
                    toc_df.to_excel(writer, sheet_name='ToC Sections', index=False)
                if not all_df.empty:
                    all_df.to_excel(writer, sheet_name='All Sections', index=False)
                if not mismatch_df.empty:
                    mismatch_df.to_excel(writer, sheet_name='Mismatches', index=False)
            
            logger.info("Validation report saved to usb_pd_validation_report.xlsx")
            
        except Exception as e:
            logger.error(f"Error generating validation report: {e}")
    
    def process_pdf(self, pdf_path: str):
        """Main method to process PDF and generate all outputs"""
        self.pdf_path = Path(pdf_path)
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Processing PDF: {self.pdf_path}")
        
        # Extract document title
        self.doc_title = self.extract_document_title()
        logger.info(f"Document title: {self.doc_title}")
        
        # Extract ToC sections
        self.toc_sections = self.extract_toc_from_pdf()
        logger.info(f"Extracted {len(self.toc_sections)} ToC sections")
        
        # Extract all sections
        self.sections = self.extract_all_sections_from_pdf()
        logger.info(f"Extracted {len(self.sections)} total sections")
        
        # Save JSONL files
        self.save_jsonl(self.toc_sections, 'usb_pd_toc.jsonl')
        self.save_jsonl(self.sections, 'usb_pd_spec.jsonl')
        
        # Generate metadata
        metadata = {
            'doc_title': self.doc_title,
            'total_toc_sections': len(self.toc_sections),
            'total_sections': len(self.sections),
            'processing_date': pd.Timestamp.now().isoformat(),
            'source_file': str(self.pdf_path)
        }
        
        with open('usb_pd_metadata.jsonl', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Generate validation report
        self.generate_validation_report(self.toc_sections, self.sections)
        
        logger.info("Processing complete!")

def main():
    """Main function to run the parser"""
    import argparse
    
    parser = argparse.ArgumentParser(description='USB PD Specification PDF Parser')
    parser.add_argument('pdf_file', help='Path to the USB PD specification PDF file')
    
    args = parser.parse_args()
    
    try:
        pdf_parser = USBPDParser(args.pdf_file)
        pdf_parser.process_pdf(args.pdf_file)
        
        print("\n Processing completed successfully!")
        print("Generated files:")
        print("- usb_pd_toc.jsonl (Table of Contents)")
        print("- usb_pd_spec.jsonl (All sections)")
        print("- usb_pd_metadata.jsonl (Metadata)")
        print("- usb_pd_validation_report.xlsx (Validation report)")
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        print(f"\n Error: {e}")

if __name__ == "__main__":
    main()


