# Install required packages
# pip install markitdown openai python-magic-bin pypdf2 pdf2image pillow

import os
import base64
from io import BytesIO
from typing import Optional, List
from pathlib import Path
# PDF processing imports
from markitdown import MarkItDown
from pdf2image import convert_from_path
from PIL import Image

# OpenAI for Ollama
from openai import OpenAI

class OllamaMarkItDown:
    def __init__(self, base_url: str = "http://localhost:11434/v1", model_name: str = "qwen2.5vl"):
        """
        Initialize MarkItDown with Ollama endpoint using OpenAI client
        
        Args:
            base_url (str): Ollama server base URL with /v1 endpoint
            model_name (str): Ollama model name for vision tasks
        """
        self.base_url = base_url
        self.model_name = model_name
        
        # Initialize OpenAI client for Ollama
        self.client = OpenAI(
            base_url=base_url,
            api_key="ollama"  # Ollama doesn't require real API key
        )
        
        # Initialize MarkItDown for text extraction
        self.markitdown = MarkItDown()
        
    def test_ollama_connection(self) -> bool:
        """Test if Ollama server is accessible"""
        try:
            # Test with a simple completion
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            print(f"Ollama connection test failed: {e}")
            return False
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 string"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def pil_image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    def extract_text_from_image(self, image_base64: str) -> str:
        """Extract text from image using Ollama vision model"""
        try:
            prompt = """Extract ALL text from this image exactly as it appears. 
            Preserve the EXACT formatting, spacing, layout, and structure.
            Include every single character, symbol, number, and punctuation mark.
            Maintain the original line breaks, indentation, and spacing.
            Do not add any explanations or extra text - just return the exact text as seen in the image.
            If there are tables, preserve the table structure with proper alignment.
            If there are lists, preserve the list formatting.
            If there are headings, preserve the heading hierarchy.
            Output everything in markdown format that matches the visual layout perfectly."""
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error extracting text from image: {e}")
            return ""
    
    def pdf_to_images(self, pdf_path: str, dpi: int = 300) -> List[Image.Image]:
        """Convert PDF pages to images"""
        try:
            print(f"Converting PDF to images with {dpi} DPI...")
            images = convert_from_path(pdf_path, dpi=dpi)
            print(f"Converted {len(images)} pages to images")
            return images
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            return []
    
    def process_pdf_with_vision(self, pdf_path: str, output_path: Optional[str] = None) -> str:
        """
        Process PDF using vision model to preserve exact formatting
        
        Args:
            pdf_path (str): Path to PDF file
            output_path (str): Optional output path for markdown file
            
        Returns:
            str: Markdown content with preserved formatting
        """
        try:
            # Check if PDF exists
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            print(f"Processing PDF with vision model: {pdf_path}")
            
            # Convert PDF to images
            images = self.pdf_to_images(pdf_path)
            
            if not images:
                print("Failed to convert PDF to images, falling back to text extraction")
                return self.pdf_to_markdown_fallback(pdf_path, output_path)
            
            # Process each page
            all_pages_content = []
            
            for i, image in enumerate(images):
                print(f"Processing page {i+1}/{len(images)}...")
                
                # Convert PIL image to base64
                image_base64 = self.pil_image_to_base64(image)
                
                # Extract text from image
                page_content = self.extract_text_from_image(image_base64)
                
                if page_content:
                    # Add page separator if not first page
                    if i > 0:
                        all_pages_content.append(f"\n\n---\n*Page {i+1}*\n\n")
                    all_pages_content.append(page_content)
                else:
                    print(f"Warning: No text extracted from page {i+1}")
            
            # Combine all pages
            final_content = "".join(all_pages_content)
            
            # Save to file if output path provided
            if output_path:
                self._save_markdown(final_content, output_path)
                print(f"Markdown saved to: {output_path}")
            
            return final_content
            
        except Exception as e:
            print(f"Error processing PDF with vision: {str(e)}")
            print("Falling back to text extraction...")
            return self.pdf_to_markdown_fallback(pdf_path, output_path)
    
    def pdf_to_markdown_fallback(self, pdf_path: str, output_path: Optional[str] = None) -> str:
        """Fallback method using MarkItDown for text extraction"""
        try:
            print("Using fallback text extraction method...")
            result = self.markitdown.convert(pdf_path)
            content = result.text_content
            
            if output_path:
                self._save_markdown(content, output_path)
                print(f"Fallback markdown saved to: {output_path}")
            
            return content
            
        except Exception as e:
            print(f"Error in fallback conversion: {str(e)}")
            return ""
    
    def _save_markdown(self, content: str, output_path: str):
        """Save markdown content to file"""
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def batch_convert(self, pdf_directory: str, output_directory: str = None, use_vision: bool = True):
        """
        Convert multiple PDFs to markdown
        
        Args:
            pdf_directory (str): Directory containing PDF files
            output_directory (str): Directory to save markdown files
            use_vision (bool): Whether to use vision model for processing
        """
        if not os.path.exists(pdf_directory):
            print(f"Directory not found: {pdf_directory}")
            return
        
        if output_directory is None:
            output_directory = pdf_directory
        
        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)
        
        # Find all PDF files
        pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print("No PDF files found in the directory")
            return
        
        print(f"Found {len(pdf_files)} PDF files to convert")
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(pdf_directory, pdf_file)
            output_file = os.path.splitext(pdf_file)[0] + '.md'
            output_path = os.path.join(output_directory, output_file)
            
            print(f"\nConverting: {pdf_file}")
            if use_vision:
                self.process_pdf_with_vision(pdf_path, output_path)
            else:
                self.pdf_to_markdown_fallback(pdf_path, output_path)

# Simple function for quick conversion
def convert_pdf_to_md(pdf_path: str, output_path: str = None, use_vision: bool = True, 
                     base_url: str = "http://localhost:11434/v1", model: str = "qwen2.5vl") -> str:
    """
    Simple function to convert PDF to markdown with exact formatting
    
    Args:
        pdf_path (str): Path to PDF file
        output_path (str): Optional output path for markdown file
        use_vision (bool): Whether to use vision model for processing
        base_url (str): Ollama server base URL
        model (str): Ollama model name
    
    Returns:
        str: Markdown content
    """
    converter = OllamaMarkItDown(base_url=base_url, model_name=model)
    
    if output_path is None:
        # Generate output path from PDF path
        output_path = os.path.splitext(pdf_path)[0] + '.md'
    
    if use_vision:
        return converter.process_pdf_with_vision(pdf_path, output_path)
    else:
        return converter.pdf_to_markdown_fallback(pdf_path, output_path)

# Utility function for local file processing
def process_local_pdf(pdf_path: str, output_dir: str = None, use_vision: bool = True,
                     base_url: str = "http://localhost:11434/v1", model: str = "qwen2.5vl"):
    """Process a local PDF file and save markdown with exact formatting"""
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return None
    
    # Set output directory to same as input if not specified
    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename
    pdf_filename = os.path.basename(pdf_path)
    output_filename = os.path.splitext(pdf_filename)[0] + '.md'
    output_path = os.path.join(output_dir, output_filename)
    
    print(f"🔄 Converting {pdf_filename} with {'vision model' if use_vision else 'text extraction'}...")
    
    # Initialize converter
    converter = OllamaMarkItDown(base_url=base_url, model_name=model)
    
    # Test connection if using vision
    if use_vision:
        print("Testing Ollama connection...")
        if not converter.test_ollama_connection():
            print("⚠️  Ollama connection failed, falling back to text extraction")
            use_vision = False
    
    # Convert PDF
    if use_vision:
        markdown_content = converter.process_pdf_with_vision(pdf_path, output_path)
    else:
        markdown_content = converter.pdf_to_markdown_fallback(pdf_path, output_path)
    
    if markdown_content:
        print(f"✅ Conversion completed!")
        print(f"📄 Markdown file saved: {output_path}")
        print(f"📊 Content length: {len(markdown_content)} characters")
        
        # Show preview
        print("\n📖 Preview (first 300 characters):")
        print(markdown_content[:300] + "..." if len(markdown_content) > 300 else markdown_content)
        
        return output_path
    else:
        print("❌ Conversion failed")
        return None

# Example usage and testing
if __name__ == "__main__":
    # Initialize converter with custom Ollama endpoint
    converter = OllamaMarkItDown(
        base_url="http://localhost:11434/v1",  # Your Ollama endpoint
        model_name="qwen2.5vl"          # Your vision model
    )
    
    file_path = Path(__file__).parent

    # Test Ollama connection
    if converter.test_ollama_connection():
        print("✅ Ollama server is accessible")
    else:
        print("⚠️  Ollama server not accessible - will use fallback method")
    
    # Example conversions (uncomment to use)
    process_local_pdf(file_path/"sample.pdf", use_vision=True)
    # converter.batch_convert("pdf_folder", "markdown_folder", use_vision=True)

# For direct execution
print("🚀 Ollama PDF to Markdown Converter Ready!")
print("🔍 Uses vision model for exact formatting preservation")
print("📁 Use process_local_pdf('your_file.pdf') for quick conversion")
print("💻 Or use convert_pdf_to_md('your_file.pdf') for direct conversion")