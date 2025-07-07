# poppler
You need to install Poppler, which is required for PDF to image conversion. Here's how to install it based on your operating system:

## Installation Instructions:

### Windows:
1. Download Poppler for Windows from: https://github.com/oschwartz10612/poppler-windows/releases/
2. Extract the zip file to a folder (e.g., `C:\poppler`)
3. Add the `bin` folder to your PATH environment variable:
   - Add `C:\poppler\Library\bin` to your system PATH
   - Or use conda: `conda install -c conda-forge poppler`

### macOS:
```bash
# Using Homebrew
brew install poppler

# Using MacPorts
sudo port install poppler
```

### Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

### Linux (CentOS/RHEL/Fedora):
```bash
# CentOS/RHEL
sudo yum install poppler-utils

# Fedora
sudo dnf install poppler-utils
```

### Alternative: Use Docker
If you're having trouble with local installation, you can also use a Docker container with Poppler pre-installed.

## Verify Installation:
After installation, verify that Poppler is working:

```bash
# Check if pdftoppm is available
pdftoppm -h

# Or check if pdfinfo works
pdfinfo -h
```
