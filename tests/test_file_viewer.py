"""
Tests for file viewer functionality.
"""

import os
import tempfile
import pytest

from simplerun.utils.file.file_viewer import generate_file_viewer_html


def test_generate_file_viewer_html_pdf():
    """Test HTML generation for PDF files."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        # Create a minimal PDF file for testing
        f.write(b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids []\n/Count 0\n>>\nendobj\nxref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \ntrailer\n<<\n/Size 3\n/Root 1 0 R\n>>\nstartxref\n108\n%%EOF')
        file_path = f.name
    
    try:
        html = generate_file_viewer_html(file_path)
        assert '<!DOCTYPE html>' in html
        assert 'File Viewer' in html
        assert 'pdf.js' in html
        assert 'pdf.min.js' in html
    finally:
        os.unlink(file_path)


def test_generate_file_viewer_html_image():
    """Test HTML generation for image files."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        # Create a minimal PNG file for testing
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178\x00\x00\x00\x00IEND\xaeB`\x82')
        file_path = f.name
    
    try:
        html = generate_file_viewer_html(file_path)
        assert '<!DOCTYPE html>' in html
        assert 'File Viewer' in html
        assert 'img' in html
        # Check that the base64 content is included in the HTML
        assert 'fileBase64' in html
    finally:
        os.unlink(file_path)


def test_generate_file_viewer_html_unsupported():
    """Test HTML generation for unsupported files."""
    with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
        f.write(b'Test content')
        file_path = f.name
    
    try:
        with pytest.raises(ValueError, match='Unsupported file extension'):
            generate_file_viewer_html(file_path)
    finally:
        os.unlink(file_path)


def test_generate_file_viewer_html_nonexistent():
    """Test HTML generation for nonexistent files."""
    with pytest.raises(ValueError, match='File not found'):
        generate_file_viewer_html('/nonexistent/file.pdf')


def test_generate_file_viewer_html_directory():
    """Test HTML generation for directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with pytest.raises(ValueError, match='Unsupported file extension'):
            generate_file_viewer_html(temp_dir) 