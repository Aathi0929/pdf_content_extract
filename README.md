# USB Power Delivery (USB PD) Specification Parser

A comprehensive Python-based parsing system that extracts and structures content from USB PD specification PDF documents into machine-readable JSONL format.

##  Project Overview

This system parses USB Power Delivery specification PDFs and produces:
- **Structured JSONL output** representing Table of Contents (ToC) hierarchy
- **Complete section extraction** with metadata preservation
- **Validation reports** comparing ToC against parsed content
- **Hierarchical data** with proper parent-child relationships

## Features

-  **PDF Text Extraction** using multiple libraries (pdfplumber, PyMuPDF)
-  **Table of Contents Parsing** with regex pattern matching
-  **Hierarchical Section Detection** (chapters, sections, subsections)
-  **JSONL Output Generation** with standardized schema
-  **Validation Reporting** in Excel format
-  **Semantic Tag Generation** based on content analysis
-  **Robust Error Handling** and logging
-  **Progress Tracking** with tqdm progress bars

 Project Structure

```
usb-pd-parser/
├── usb_pd_parser.py          
├── demo.py                   
├── requirements.txt          
├── README.md                 
├── sample_usb_pd_toc.jsonl   
├── sample_usb_pd_metadata.json 
└── output/                   
    ├── usb_pd_toc.jsonl    
    ├── usb_pd_spec.jsonl    
    ├── usb_pd_metadata.jsonl 
    └── usb_pd_validation_report.xlsx 
```


##  Output Files

### JSONL Schema

Each line in the JSONL files contains a section object with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `section_id` | string | Hierarchical identifier (e.g., "2.1.2") |
| `title` | string | Section title (without numbering) |
| `page` | integer | Starting page number |
| `level` | integer | Depth level (1=chapter, 2=section, 3=subsection) |
| `parent_id` | string/null | Parent section ID (null for top level) |
| `full_path` | string | Complete section path with ID and title |
| `doc_title` | string | Document name/version |
| `tags` | array | Semantic tags for content categorization |


##  Supported Section Patterns

The parser recognizes these ToC formats:

1. **Dotted leaders**: `2.1.2 Section Title ........ 53`
2. **Simple spacing**: `2.1.2 Section Title 53`  
3. **Tab-separated**: `2.1.2\tSection Title\t53`

##  Validation Report

The Excel validation report includes:

- **Summary Sheet**: Statistics comparing ToC vs parsed sections
- **ToC Sections**: Complete Table of Contents data
- **All Sections**: All parsed sections from document
- **Mismatches**: Sections missing or extra in parsing



### Processing Parameters

- **ToC Search Range**: First 20 pages (configurable)
- **Pattern Matching**: Multiple regex patterns for flexibility
- **Tag Generation**: Keyword-based semantic tagging

## Error Handling

The parser includes robust error handling for:

- **Missing PDF files**: Clear error messages
- **Corrupted PDFs**: Graceful degradation
- **Parsing failures**: Continue processing other sections
- **Output errors**: Detailed logging for debugging


 ##output:
```
 Sample data files created:
- sample_usb_pd_toc.jsonl
- sample_usb_pd_metadata.json

 USB PD Parser Usage Example:
Sample Section: 2.1.2 Power Delivery Contract Negotiation
Level: 3, Parent: 2.1
Tags: ['contracts', 'negotiation']
```


##  Dependencies

- **pdfplumber**: PDF text extraction and layout analysis
- **PyMuPDF (fitz)**: Alternative PDF processing
- **pandas**: Data manipulation and Excel export
- **openpyxl**: Excel file creation
- **jsonlines**: JSONL file handling
- **regex**: Advanced pattern matching
- **tqdm**: Progress bar display


### Common Issues

1. **"PDF file not found"**: Check file path and permissions
2. **"No sections extracted"**: Verify PDF has extractable text
3. **"Pattern not matching"**: PDF may use different ToC format
4. **"Memory errors"**: Large PDFs may need processing optimization


##  Support

For questions or issues:
- Review the validation report for parsing accuracy
- Check logs for detailed error information
- Verify PDF text is extractable (not scanned images)
- Ensure all dependencies are installed correctly




