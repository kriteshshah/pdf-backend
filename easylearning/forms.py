from django import forms
from .models import PDFDocument, Question, ConversationThread


class PDFUploadForm(forms.ModelForm):
    """Form for uploading PDF documents"""
    class Meta:
        model = PDFDocument
        fields = ['title', 'file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter PDF title'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'
            })
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        print(f"Form clean_file called with: {file}")
        
        if not file:
            print("No file provided in form")
            raise forms.ValidationError("Please select a PDF file to upload.")
        
        if not file.name:
            print("File has no name")
            raise forms.ValidationError("Invalid file selected.")
        
        if not file.name.endswith('.pdf'):
            print(f"File type not PDF: {file.name}")
            raise forms.ValidationError("Only PDF files are allowed.")
        
        if file.size == 0:
            print("File is empty")
            raise forms.ValidationError("The selected file is empty.")
        
        if file.size > 10 * 1024 * 1024:  # 10MB limit
            print(f"File too large: {file.size} bytes")
            raise forms.ValidationError("File size must be under 10MB.")
        
        print(f"File validation passed: {file.name}, size: {file.size} bytes")
        return file
    
    def clean(self):
        cleaned_data = super().clean()
        print(f"Form clean method - cleaned_data: {cleaned_data}")
        return cleaned_data


class QuestionForm(forms.ModelForm):
    """Form for asking questions"""
    class Meta:
        model = Question
        fields = ['question_text', 'language']
        widgets = {
            'question_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ask a question about this PDF... (English, Gujarati, or Hindi)'
            }),
            'language': forms.Select(attrs={
                'class': 'form-select',
                'id': 'language-select'
            })
        }


class ThreadTitleForm(forms.ModelForm):
    """Form for updating thread title"""
    class Meta:
        model = ConversationThread
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter thread title'
            })
        } 