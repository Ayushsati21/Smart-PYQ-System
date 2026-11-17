 Smart PYQ System

Previous Year Question Paper Management and Repeated Question Analysis

 Project Overview

Smart PYQ System is a web-based platform designed to simplify examination preparation by providing a centralized system to upload, organize, retrieve, and analyze Previous Year Question Papers (PYQs).

The system extracts questions from PDF documents, manages question data, and identifies repeated or similar questions across different examination papers.

 Live Demo

Frontend: https://smart-pyq-system-frontend.vercel.app/

Login: https://smart-pyq-system-frontend.vercel.app/login.html

Backend: https://smart-pyq-system.onrender.com/

Backend Health: https://smart-pyq-system.onrender.com/health

 Features

1. PDF Upload and Management
2. Organized Question Paper Retrieval
3. Automated PDF Text Extraction
4. OCR Support for Scanned PDFs
5. Question Number and Subpart Identification
6. Repeated Question Analysis
7. Question Data Management
8. Search and Filtering
9. Cloud-Based Deployment

 Technology Stack

Frontend:
- HTML
- CSS
- JavaScript
- Vercel

Backend:
- Python
- Flask
- REST APIs
- Gunicorn
- Docker
- Render

C++ Processing:
- C++
- Data Structures and Algorithms
- Object-Oriented Programming
- Question Processing
- Repeated Question Analysis

Database and Storage:
- TiDB Cloud
- Supabase Storage

PDF Processing:
- PyMuPDF
- Tesseract OCR
- Pytesseract

Communication:
- HTTP/HTTPS
- JSON
- REST APIs

 System Architecture

The project follows a client-server architecture.

The frontend is deployed on Vercel and communicates with the Python Flask backend hosted on Render through REST APIs.

The backend manages application requests, PDF processing, question management, and database operations.

TiDB Cloud stores structured information such as question-paper metadata and extracted question data.

Supabase Storage stores the original PDF documents.

Docker provides a consistent deployment environment, while Gunicorn runs the Flask application in production.

 Project Workflow

1. The user uploads a question-paper PDF through the frontend.
2. The frontend sends the request to the Flask backend.
3. The original PDF is stored in Supabase Storage.
4. PyMuPDF extracts text from digital PDF documents.
5. Tesseract OCR processes scanned PDFs when required.
6. Extracted text is processed to identify questions and subparts.
7. Structured question data and paper metadata are stored in TiDB Cloud.
8. The C++ processing engine supports question processing and repeated-question analysis.
9. The backend returns the results to the frontend.
10. Users can search, retrieve, and analyze question papers.

 Installation and Setup

Step 1: Clone the repository

git clone https://github.com/Ayushsati21/Smart-PYQ-System.git

Step 2: Navigate to the project directory

cd Smart-PYQ-System

Step 3: Create a Python virtual environment

python -m venv .venv

Step 4: Activate the environment

Windows:

.venv\Scripts\activate

Linux or macOS:

source .venv/bin/activate

Step 5: Install dependencies

pip install -r backend/requirements.txt

Step 6: Configure environment variables

Configure the required database credentials, Supabase settings, and application environment variables.

Do not upload secret keys or passwords to GitHub.

Step 7: Run the Flask backend

python -m flask --app backend.app run

Step 8: Open the frontend using your configured local development setup.

 Deployment

Frontend Hosting: Vercel

Backend Hosting: Render

Containerization: Docker

Production Server: Gunicorn

Database: TiDB Cloud

PDF Storage: Supabase Storage

 Future Improvements

1. Improve OCR accuracy for scanned PDFs.
2. Integrate AI and LLM technologies for better question identification.
3. Improve question parsing and subpart detection.
4. Enhance repeated-question similarity detection.
5. Expand the question-paper library.
6. Optimize application performance.
7. Improve system testing and error handling.

 Project Objective

The main objective of Smart PYQ System is to make examination preparation more organized and efficient by reducing the manual effort required to manage previous year question papers and identify frequently repeated questions.

 Repository

GitHub: https://github.com/Ayushsati21/Smart-PYQ-System

Smart PYQ System - Making Previous Year Question Papers Smarter and More Accessible.
