# EasyLearning - PDF Summary & Q&A System

EasyLearning is a Django-based web application that transforms PDF documents into interactive learning experiences. Users can upload PDFs, get AI-powered summaries, ask questions, and engage in threaded conversations about the document content.

## Features

- **PDF Upload & Processing**: Drag-and-drop PDF upload with automatic text extraction
- **Smart Summaries**: Generate intelligent summaries of uploaded documents
- **AI-Powered Q&A**: Ask questions about PDF content and get relevant answers
- **Conversation Threads**: Organize discussions with threaded conversations for each PDF
- **Content Verification**: System indicates whether answers are derived from PDF content
- **Modern UI**: Beautiful, responsive interface built with Bootstrap 5

## Technology Stack

- **Backend**: Django 5.2.5
- **Database**: SQLite (configurable for production)
- **PDF Processing**: PyPDF2
- **Frontend**: Bootstrap 5, Font Awesome, Vanilla JavaScript
- **File Storage**: Django's built-in file handling

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd extaractsummary
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 6. Run the Development Server

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`

## Usage

### 1. Upload PDF Documents

- Navigate to the upload page
- Drag and drop or browse for PDF files
- Provide a descriptive title
- The system will automatically process the PDF and generate a summary

### 2. View Document Details

- Access uploaded PDFs from the home page
- View generated summaries and document information
- See existing conversation threads

### 3. Create Conversation Threads

- Each PDF can have multiple conversation threads
- Create threads for different topics or discussions
- Give threads descriptive titles for easy identification

### 4. Ask Questions

- Within any thread, ask questions about the PDF content
- The system will search through the document and provide relevant answers
- Answers are marked as "From PDF" or "Not from PDF" for transparency

### 5. Manage Conversations

- View all questions and answers in chronological order
- Navigate between different threads
- Access the original PDF when needed

## Project Structure

```
extaractsummary/
├── easylearning/           # Main Django app
│   ├── models.py          # Database models
│   ├── views.py           # View logic
│   ├── forms.py           # Form definitions
│   ├── admin.py           # Admin interface
│   ├── urls.py            # URL routing
│   └── templates/         # HTML templates
├── extaractsummary/        # Django project settings
│   ├── settings.py        # Project configuration
│   ├── urls.py            # Main URL configuration
│   └── wsgi.py            # WSGI configuration
├── templates/              # Base templates
├── media/                  # Uploaded files (created automatically)
├── static/                 # Static files (CSS, JS, images)
├── requirements.txt        # Python dependencies
└── manage.py              # Django management script
```

## Models

- **PDFDocument**: Stores uploaded PDF files and metadata
- **PDFSummary**: Contains generated summaries for each document
- **ConversationThread**: Manages conversation threads for each PDF
- **Question**: Stores user questions within threads
- **Answer**: Contains AI-generated answers with source verification
- **PDFChunk**: Stores text chunks for better content search

## API Endpoints

- `POST /api/ask-question/`: Ask questions and get answers programmatically
- All other functionality is available through the web interface

## Configuration

### Environment Variables

The application uses Django's default settings. For production, consider:

- Setting `DEBUG = False`
- Configuring a production database (PostgreSQL, MySQL)
- Setting up proper `SECRET_KEY`
- Configuring `ALLOWED_HOSTS`
- Setting up static file serving

### File Upload Settings

- Maximum file size: 10MB
- Supported formats: PDF only
- File storage: Local filesystem (configurable for cloud storage)

## Customization

### Adding New PDF Processors

Extend the `generate_pdf_summary()` function in `views.py` to integrate with:

- OpenAI GPT models
- Hugging Face transformers
- Other AI summarization services

### Enhancing Q&A

Improve the `generate_answer()` function with:

- Semantic search algorithms
- Vector embeddings
- Advanced NLP techniques

### UI Customization

- Modify Bootstrap theme in `templates/base.html`
- Add custom CSS in template `<style>` blocks
- Extend JavaScript functionality in template `<script>` blocks

## Troubleshooting

### Common Issues

1. **PDF Upload Fails**
   - Ensure file is under 10MB
   - Verify file is a valid PDF
   - Check file permissions

2. **Summary Generation Issues**
   - PDFs with images may not extract text properly
   - Ensure PDF contains searchable text
   - Check PyPDF2 installation

3. **Database Errors**
   - Run `python manage.py migrate`
   - Check database permissions
   - Verify model changes

### Performance Optimization

- For large PDFs, consider chunking text into smaller pieces
- Implement caching for frequently accessed summaries
- Use database indexing for better query performance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue in the repository
- Check the Django documentation
- Review the code comments for implementation details

## Future Enhancements

- **Multi-language Support**: Process PDFs in different languages
- **Advanced AI Integration**: Connect with GPT-4, Claude, or other AI models
- **Collaborative Features**: Allow multiple users to contribute to threads
- **Export Functionality**: Export conversations and summaries
- **Mobile App**: Native mobile applications
- **API Rate Limiting**: Implement proper API throttling
- **User Authentication**: Enhanced user management and permissions # pdf-backend
