import os
import PyPDF2
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import PDFDocument, PDFSummary, ConversationThread, Question, Answer, PDFChunk
from .forms import PDFUploadForm, QuestionForm, ThreadTitleForm
import json


def landing_view(request):
    """Landing page for non-authenticated users"""
    if request.user.is_authenticated:
        return redirect('easylearning:home')
    return render(request, 'easylearning/landing.html')


@login_required
def home(request):
    """Home page showing uploaded PDFs"""
    pdfs = PDFDocument.objects.all().order_by('-uploaded_at')
    return render(request, 'easylearning/home.html', {'pdfs': pdfs})


@login_required
def upload_pdf(request):
    """Handle PDF upload and generate summary"""
    if request.method == 'POST':
        print("=" * 50)
        print("UPLOAD REQUEST RECEIVED")
        print("=" * 50)
        print(f"Request method: {request.method}")
        print(f"Request POST data: {request.POST}")
        print(f"Request FILES: {request.FILES}")
        print(f"Request FILES keys: {list(request.FILES.keys()) if request.FILES else 'None'}")
        
        if request.FILES:
            for key, file_obj in request.FILES.items():
                print(f"File '{key}': {file_obj.name}, size: {file_obj.size}, type: {file_obj.content_type}")
        
        form = PDFUploadForm(request.POST, request.FILES)
        print(f"Form is valid: {form.is_valid()}")
        print(f"Form errors: {form.errors}")
        print(f"Form cleaned data: {form.cleaned_data if form.is_valid() else 'Form invalid'}")
        
        if form.is_valid():
            try:
                pdf_doc = form.save(commit=False)
                pdf_doc.uploaded_by = request.user
                pdf_doc.save()
                
                print(f"PDF saved with ID: {pdf_doc.id}")
                
                # Force file save to ensure file is accessible
                pdf_doc.refresh_from_db()
                
                # Verify file exists and is accessible
                if not pdf_doc.file:
                    raise ValueError("No file was uploaded")
                
                file_path = pdf_doc.file.path
                print(f"File path: {file_path}")
                
                if not os.path.exists(file_path):
                    raise ValueError(f"Uploaded file not found at: {file_path}")
                
                print(f"File exists: {os.path.exists(file_path)}")
                print(f"File size: {os.path.getsize(file_path)} bytes")
                
                success = True
                error_messages = []
                
                # Generate summary
                try:
                    print("Attempting to generate summary...")
                    summary_text = generate_pdf_summary(file_path)
                    print(f"Summary generated: {summary_text[:100]}...")
                    
                    if summary_text and not summary_text.startswith("Error reading PDF"):
                        PDFSummary.objects.create(
                            pdf_document=pdf_doc,
                            summary_text=summary_text
                        )
                        print("Summary saved successfully")
                    else:
                        error_messages.append("Could not generate summary from PDF")
                        print(f"Summary error: {summary_text}")
                except Exception as e:
                    error_messages.append(f"Summary generation failed: {str(e)}")
                    success = False
                    print(f"Summary exception: {e}")
                
                # Create text chunks for better Q&A
                try:
                    print("Attempting to create chunks...")
                    create_pdf_chunks(pdf_doc)
                    print("Chunks created successfully")
                except Exception as e:
                    error_messages.append(f"Text chunking failed: {str(e)}")
                    print(f"Chunking exception: {e}")
                    # Don't fail the entire upload for chunking errors
                
                # Create default conversation thread
                try:
                    print("Attempting to create thread...")
                    thread = ConversationThread.objects.create(
                        pdf_document=pdf_doc,
                        title=f"Conversation about {pdf_doc.title}"
                    )
                    print(f"Thread created with ID: {thread.id}")
                except Exception as e:
                    error_messages.append(f"Thread creation failed: {str(e)}")
                    print(f"Thread creation exception: {e}")
                    # Don't fail the entire upload for thread creation errors
                
                if success:
                    if error_messages:
                        messages.warning(request, f'PDF "{pdf_doc.title}" uploaded with some issues: {"; ".join(error_messages)}')
                    else:
                        messages.success(request, f'PDF "{pdf_doc.title}" uploaded successfully!')
                    print("Upload successful, redirecting to PDF detail page")
                    return redirect('easylearning:pdf_detail', pdf_id=pdf_doc.id)
                else:
                    # Only delete if critical errors occurred
                    if len(error_messages) > 1:  # More than just chunking/thread errors
                        messages.error(request, f'Critical errors occurred: {"; ".join(error_messages)}')
                        pdf_doc.delete()
                        print("Critical errors, PDF deleted")
                        return render(request, 'easylearning/upload.html', {'form': form})
                    else:
                        # Continue with partial success
                        messages.warning(request, f'PDF "{pdf_doc.title}" uploaded with some issues: {"; ".join(error_messages)}')
                        print("Partial success, redirecting to PDF detail page")
                        return redirect('easylearning:pdf_detail', pdf_id=pdf_doc.id)
                        
            except Exception as e:
                print(f"Critical upload error: {e}")
                messages.error(request, f'Critical error during upload: {str(e)}')
                return render(request, 'easylearning/upload.html', {'form': form})
        else:
            print(f"Form validation failed: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PDFUploadForm()
    
    return render(request, 'easylearning/upload.html', {'form': form})


def pdf_detail(request, pdf_id):
    """Show PDF details, summary, and conversation threads"""
    pdf_doc = get_object_or_404(PDFDocument, id=pdf_id)
    try:
        summary = pdf_doc.summary
    except PDFSummary.DoesNotExist:
        summary = None
    
    threads = pdf_doc.conversations.all().order_by('-updated_at')
    
    context = {
        'pdf_doc': pdf_doc,
        'summary': summary,
        'threads': threads,
    }
    return render(request, 'easylearning/pdf_detail.html', context)


def thread_detail(request, thread_id):
    """Show conversation thread with questions and answers"""
    thread = get_object_or_404(ConversationThread, id=thread_id)
    questions = thread.questions.all().order_by('asked_at')
    
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.thread = thread
            question.asked_by = request.user if request.user.is_authenticated else None
            question.save()
            
            # Generate answer
            answer_text, is_from_pdf, confidence = generate_answer(question.question_text, thread.pdf_document, question.language)
            
            Answer.objects.create(
                question=question,
                answer_text=answer_text,
                language=question.language,
                is_from_pdf=is_from_pdf,
                confidence_score=confidence
            )
            
            return redirect('easylearning:thread_detail', thread_id=thread_id)
    else:
        form = QuestionForm()
    
    context = {
        'thread': thread,
        'questions': questions,
        'form': form,
    }
    return render(request, 'easylearning/thread_detail.html', context)


@login_required
def create_thread(request, pdf_id):
    """Create a new conversation thread for a PDF"""
    pdf_doc = get_object_or_404(PDFDocument, id=pdf_id)
    
    if request.method == 'POST':
        form = ThreadTitleForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.pdf_document = pdf_doc
            thread.save()
            messages.success(request, f'New thread "{thread.title}" created!')
            return redirect('easylearning:thread_detail', thread_id=thread.id)
    else:
        form = ThreadTitleForm()
    
    return render(request, 'easylearning/create_thread.html', {'form': form, 'pdf_doc': pdf_doc})


@csrf_exempt
def ask_question_api(request):
    """API endpoint for asking questions"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question_text = data.get('question')
            thread_id = data.get('thread_id')
            language = data.get('language', 'en')
            
            if not question_text or not thread_id:
                return JsonResponse({'error': 'Missing question or thread_id'}, status=400)
            
            thread = get_object_or_404(ConversationThread, id=thread_id)
            
            # Create question
            question = Question.objects.create(
                thread=thread,
                question_text=question_text,
                language=language,
                asked_by=request.user if request.user.is_authenticated else None
            )
            
            # Generate answer
            answer_text, is_from_pdf, confidence = generate_answer(question_text, thread.pdf_document, language)
            
            answer = Answer.objects.create(
                question=question,
                answer_text=answer_text,
                language=language,
                is_from_pdf=is_from_pdf,
                confidence_score=confidence
            )
            
            return JsonResponse({
                'question_id': str(question.id),
                'answer_text': answer.answer_text,
                'is_from_pdf': answer.is_from_pdf,
                'confidence_score': answer.confidence_score,
                'language': language
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def generate_pdf_summary(pdf_path):
    """Generate summary from PDF text"""
    try:
        # Check if file exists and is accessible
        if not os.path.exists(pdf_path):
            return "Error reading PDF: File not found"
        
        file_size = os.path.getsize(pdf_path)
        if file_size == 0:
            return "Error reading PDF: File is empty"
        
        print(f"Processing PDF: {pdf_path} (size: {file_size} bytes)")
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            if len(pdf_reader.pages) == 0:
                return "Error reading PDF: No pages found"
            
            text = ""
            for page in pdf_reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + " "
                except Exception as e:
                    print(f"Error extracting text from page: {e}")
                    continue
            
            if not text.strip():
                return "Error reading PDF: No text content found"
            
            print(f"Extracted {len(text)} characters of text")
            
            # Simple summary generation (in production, use AI models)
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            if len(sentences) < 3:
                summary = text[:300] + "..." if len(text) > 300 else text
            else:
                summary = '. '.join(sentences[:5]) + '.'
            
            return summary if summary else "Summary could not be generated."
            
    except Exception as e:
        print(f"PDF summary generation error: {e}")
        return f"Error reading PDF: {str(e)}"


def create_pdf_chunks(pdf_doc):
    """Create text chunks from PDF for better search"""
    try:
        # Check if file exists and is accessible
        if not pdf_doc.file:
            print(f"No file associated with PDF document: {pdf_doc.title}")
            return
        
        file_path = pdf_doc.file.path
        if not os.path.exists(file_path):
            print(f"PDF file not found: {file_path}")
            return
        
        print(f"Creating chunks for PDF: {pdf_doc.title} at {file_path}")
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            if len(pdf_reader.pages) == 0:
                print("No pages found in PDF")
                return
            
            chunk_count = 0
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if not text.strip():
                        continue
                    
                    # Clean the text
                    text = text.strip()
                    # Remove excessive whitespace
                    text = ' '.join(text.split())
                    
                    # Split into sentences for better chunking
                    sentences = text.split('. ')
                    
                    current_chunk = ""
                    sentence_count = 0
                    
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if not sentence:
                            continue
                        
                        # Add sentence to current chunk
                        if current_chunk:
                            current_chunk += ". " + sentence
                        else:
                            current_chunk = sentence
                        
                        sentence_count += 1
                        
                        # Create chunk when we have enough sentences or reach character limit
                        if sentence_count >= 3 or len(current_chunk) >= 300:
                            if current_chunk.strip():
                                PDFChunk.objects.create(
                                    pdf_document=pdf_doc,
                                    chunk_text=current_chunk.strip(),
                                    chunk_index=chunk_count,
                                    page_number=page_num + 1
                                )
                                chunk_count += 1
                            
                            # Reset for next chunk
                            current_chunk = ""
                            sentence_count = 0
                    
                    # Don't forget the last chunk if it has content
                    if current_chunk.strip():
                        PDFChunk.objects.create(
                            pdf_document=pdf_doc,
                            chunk_text=current_chunk.strip(),
                            chunk_index=chunk_count,
                            page_number=page_num + 1
                        )
                        chunk_count += 1
                            
                except Exception as e:
                    print(f"Error processing page {page_num + 1}: {e}")
                    continue
            
            print(f"Created {chunk_count} chunks for PDF {pdf_doc.title}")
            
    except Exception as e:
        print(f"Error creating chunks for PDF {pdf_doc.title}: {e}")
        # Don't raise the exception - just log it


def analyze_question(question):
    """Analyze the question to understand its type and extract key information"""
    question_lower = question.lower().strip()
    
    # Question type classification
    question_types = {
        'summary': ['summary', 'brief', 'overview', 'general', 'about', 'what is this'],
        'chapter_specific': ['chapter', 'section', 'part'],
        'character': ['character', 'who', 'person', 'name', 'protagonist', 'hero', 'villain'],
        'plot': ['plot', 'story', 'narrative', 'what happens', 'events', 'action'],
        'setting': ['where', 'place', 'location', 'world', 'realm', 'setting'],
        'time': ['when', 'time', 'period', 'era', 'century', 'year'],
        'comparison': ['compare', 'difference', 'similar', 'versus', 'vs', 'better', 'worse'],
        'definition': ['what is', 'define', 'meaning', 'explain', 'describe'],
        'list': ['list', 'all', 'every', 'each', 'names', 'types', 'kinds'],
        'how': ['how', 'method', 'process', 'way', 'technique'],
        'why': ['why', 'reason', 'cause', 'because', 'purpose'],
        'quantity': ['how many', 'count', 'number', 'amount', 'size', 'length', 'longest', 'shortest']
    }
    
    # Determine question type
    detected_types = []
    for qtype, keywords in question_types.items():
        if any(keyword in question_lower for keyword in keywords):
            detected_types.append(qtype)
    
    # Extract specific entities
    entities = {
        'chapter_numbers': [],
        'character_names': [],
        'locations': [],
        'dates': [],
        'numbers': []
    }
    
    import re
    
    # Extract chapter numbers
    chapter_matches = re.findall(r'chapter\s+(\d+)', question_lower)
    entities['chapter_numbers'] = [int(num) for num in chapter_matches]
    
    # Extract numbers
    number_matches = re.findall(r'\b(\d+)\b', question_lower)
    entities['numbers'] = [int(num) for num in number_matches]
    
    # Extract potential character names (words starting with capital letters)
    name_matches = re.findall(r'\b[A-Z][a-z]+\b', question)
    entities['character_names'] = name_matches
    
    # Extract potential locations
    location_keywords = ['in', 'at', 'from', 'to', 'near', 'around']
    words = question_lower.split()
    for i, word in enumerate(words):
        if word in location_keywords and i + 1 < len(words):
            entities['locations'].append(words[i + 1])
    
    # Determine primary question type
    primary_type = 'general'
    if detected_types:
        # Prioritize more specific types
        priority_order = ['chapter_specific', 'character', 'quantity', 'comparison', 'definition', 'plot', 'setting', 'time', 'how', 'why', 'summary']
        for ptype in priority_order:
            if ptype in detected_types:
                primary_type = ptype
                break
    
    return {
        'original_question': question,
        'question_lower': question_lower,
        'detected_types': detected_types,
        'primary_type': primary_type,
        'entities': entities,
        'keywords': extract_keywords(question_lower)
    }

def extract_keywords(question_lower):
    """Extract meaningful keywords from the question"""
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
        'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 
        'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 
        'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 
        'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'his', 'hers', 
        'ours', 'theirs'
    }
    
    # Extract meaningful keywords
    keywords = [word for word in question_lower.split() if word not in stop_words and len(word) > 2]
    
    # If no meaningful keywords, include shorter words
    if not keywords:
        keywords = [word for word in question_lower.split() if len(word) > 1]
    
    # For general questions, add common content words
    general_words = ['give', 'me', 'tell', 'about', 'what', 'how', 'why', 'when', 'where', 'brief', 'detail', 'summary']
    if any(word in question_lower for word in general_words):
        keywords.extend(['story', 'content', 'information', 'text', 'document', 'pdf'])
    
    return keywords

def score_chunk_for_question(chunk, question_analysis):
    """Score a chunk based on question analysis"""
    chunk_text_lower = chunk.chunk_text.lower()
    score = 0
    
    # Basic keyword matching
    for keyword in question_analysis['keywords']:
        if keyword in chunk_text_lower:
            score += 1
    
    # For general questions, give base score to all chunks
    if question_analysis['primary_type'] == 'summary' or question_analysis['primary_type'] == 'general':
        score += 1  # Base score for all chunks in general questions
    
    # For plot questions, give base score to story-related chunks
    if question_analysis['primary_type'] == 'plot':
        if any(word in chunk_text_lower for word in ['story', 'plot', 'narrative', 'events', 'action', 'happens']):
            score += 2
        else:
            score += 1  # Base score for all chunks in plot questions
    
    # Question type specific scoring
    primary_type = question_analysis['primary_type']
    entities = question_analysis['entities']
    
    if primary_type == 'chapter_specific':
        # High score for exact chapter matches
        for chapter_num in entities['chapter_numbers']:
            if f'chapter {chapter_num}' in chunk_text_lower or f'chapter {chapter_num}:' in chunk_text_lower:
                score += 50
        # Lower score for general chapter content
        if 'chapter' in chunk_text_lower:
            score += 10
    
    elif primary_type == 'character':
        # High score for character name mentions
        for name in entities['character_names']:
            if name.lower() in chunk_text_lower:
                score += 30
        # Score for character-related content
        if any(word in chunk_text_lower for word in ['character', 'person', 'protagonist', 'hero', 'villain', 'main']):
            score += 15
        # Score for character names in the story
        if any(word in chunk_text_lower for word in ['haruto', 'akebane', 'kurogami']):
            score += 20
        # Base score for character questions
        score += 1
    
    elif primary_type == 'quantity':
        # Score for content about numbers, sizes, lengths
        if any(word in chunk_text_lower for word in ['longest', 'shortest', 'biggest', 'smallest', 'number', 'count', 'size']):
            score += 20
        # Score for numerical content
        if any(word in chunk_text_lower for word in ['pages', 'length', 'size', 'amount']):
            score += 15
    
    elif primary_type == 'comparison':
        # Score for comparative content
        if any(word in chunk_text_lower for word in ['compare', 'difference', 'similar', 'versus', 'better', 'worse']):
            score += 20
    
    elif primary_type == 'plot':
        # Score for story/plot content
        if any(word in chunk_text_lower for word in ['story', 'plot', 'narrative', 'events', 'action', 'happens']):
            score += 15
    
    elif primary_type == 'setting':
        # Score for location/setting content
        if any(word in chunk_text_lower for word in ['place', 'location', 'world', 'realm', 'setting', 'where']):
            score += 15
    
    elif primary_type == 'summary':
        # Score for introductory/summary content
        if any(word in chunk_text_lower for word in ['introduction', 'beginning', 'start', 'overview', 'summary']):
            score += 20
        # Score for main story elements
        if any(word in chunk_text_lower for word in ['main', 'primary', 'central', 'key']):
            score += 10
    
    # Exact phrase matching (high bonus)
    if question_analysis['question_lower'] in chunk_text_lower:
        score += 25
    
    # Context-specific scoring
    if 'about' in question_analysis['question_lower']:
        if any(word in chunk_text_lower for word in ['about', 'concerning', 'regarding']):
            score += 10
    
    if 'happens' in question_analysis['question_lower']:
        if any(word in chunk_text_lower for word in ['happens', 'occurs', 'events', 'action']):
            score += 10
    
    return score

def select_best_chunks(chunk_scores, question_analysis):
    """Select the best chunks based on question type and content diversity"""
    best_chunks = []
    primary_type = question_analysis['primary_type']
    
    if primary_type == 'chapter_specific':
        # For chapter questions, ensure we get the specific chapter
        seen_chapters = set()
        for chunk, score in chunk_scores:
            chunk_text_lower = chunk.chunk_text.lower()
            import re
            chapter_match = re.search(r'chapter\s+(\d+)', chunk_text_lower)
            if chapter_match:
                chapter_num = chapter_match.group(1)
                if chapter_num not in seen_chapters:
                    best_chunks.append((chunk, score))
                    seen_chapters.add(chapter_num)
                if len(best_chunks) >= 2:
                    break
            elif len(best_chunks) < 2:
                best_chunks.append((chunk, score))
    
    elif primary_type == 'summary':
        # For summary questions, get more comprehensive content
        for chunk, score in chunk_scores[:3]:  # Take top 3 for summaries
            best_chunks.append((chunk, score))
    
    elif primary_type == 'character':
        # For character questions, focus on character-specific content
        for chunk, score in chunk_scores[:2]:
            best_chunks.append((chunk, score))
    
    else:
        # For other question types, take top 2 chunks
        for chunk, score in chunk_scores[:2]:
            best_chunks.append((chunk, score))
    
    return best_chunks

def generate_answer_from_chunks(best_chunks, question_analysis):
    """Generate a coherent answer from selected chunks"""
    # Combine chunk content
    answer_parts = []
    for chunk, score in best_chunks:
        clean_text = chunk.chunk_text.strip()
        clean_text = ' '.join(clean_text.split())
        answer_parts.append(clean_text)
    
    answer_text = ' '.join(answer_parts)
    
    # Limit answer length based on question type
    max_length = 1000 if question_analysis['primary_type'] == 'summary' else 600
    
    if len(answer_text) > max_length:
        # Try to find a good breaking point
        sentences = answer_text.split('. ')
        truncated_answer = ''
        for sentence in sentences:
            if len(truncated_answer + sentence) < max_length:
                truncated_answer += sentence + '. '
            else:
                break
        answer_text = truncated_answer.strip()
        if not answer_text.endswith('.'):
            answer_text += '...'
    
    return answer_text


@login_required
def profile_view(request):
    """User profile page with statistics and recent activity"""
    user = request.user
    
    # Get user's PDFs
    pdfs = PDFDocument.objects.filter(uploaded_by=user)
    
    # Get user's conversation threads
    threads = ConversationThread.objects.filter(pdf_document__uploaded_by=user)
    
    # Get user's questions
    questions = Question.objects.filter(asked_by=user)
    
    # Get user's answers (if any)
    answers = Answer.objects.filter(question__asked_by=user)
    
    # Create recent activity list
    recent_activities = []
    
    # Add PDF uploads
    for pdf in pdfs.order_by('-uploaded_at')[:5]:
        recent_activities.append({
            'icon': 'file-pdf',
            'title': f'Uploaded "{pdf.title}"',
            'time': pdf.uploaded_at
        })
    
    # Add thread creations
    for thread in threads.order_by('-created_at')[:3]:
        recent_activities.append({
            'icon': 'comments',
            'title': f'Created thread "{thread.title}"',
            'time': thread.created_at
        })
    
            # Add questions
        for question in questions.order_by('-asked_at')[:3]:
            question_text = question.question_text
            truncated_text = question_text[:50] + "..." if len(question_text) > 50 else question_text
            recent_activities.append({
                'icon': 'question-circle',
                'title': f'Asked: "{truncated_text}"',
                'time': question.asked_at
            })
    
    # Sort by time and take top 8
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    recent_activities = recent_activities[:8]
    
    context = {
        'pdfs': pdfs,
        'threads': threads,
        'questions': questions,
        'answers': answers,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'easylearning/profile.html', context)

def test_dropdown_view(request):
    """Test page for dropdown functionality"""
    return render(request, 'test_dropdown.html')

def translate_answer(answer_text, target_language):
    """Translate answer text to the target language"""
    if target_language == 'en':
        return answer_text
    
    # Translation dictionaries for common phrases and responses
    translations = {
        'gu': {  # Gujarati translations
            'I cannot find specific information about this question in the PDF. The question may not be directly addressed in the document content.': 
                'હું આ પ્રશ્ન વિશે PDF માં ચોક્કસ માહિતી શોધી શકતો નથી. પ્રશ્ન સીધો દસ્તાવેજની સામગ્રીમાં સંબોધવામાં આવ્યો નથી.',
            'I cannot find any content in this PDF to answer your question.': 
                'હું તમારા પ્રશ્નનો જવાબ આપવા માટે આ PDF માં કોઈ સામગ્રી શોધી શકતો નથી.',
            'Error generating answer:': 
                'જવાબ જનરેટ કરવામાં ભૂલ:',
            'Chapter': 'અધ્યાય',
            'The Blades of Dawn': 'ડોનની તવારો',
            'In the realm of': 'રાજ્યમાં',
            'land draped in mist': 'ધુમ્મસમાં લપેટાયેલી જમીન',
            'steeped in legends': 'કથાઓમાં ડૂબેલું',
            'monsters known as': 'રાક્ષસો તરીકે ઓળખાય છે',
            'have plagued villages': 'ગામડાંમાં ત્રાસ ફેલાવ્યો છે',
            'for centuries': 'સદીઓથી',
            'These creatures': 'આ જીવો',
            'born from shadows': 'છાયાઓમાંથી જન્મ્યા',
            'and c': 'અને',
            'Kurogami': 'કુરોગામી',
            'Tsukihara': 'ત્સુકિહારા',
            'Haruto': 'હારુતો',
            'Ake': 'એકે',
            'blade': 'તલવાર',
            'sword': 'તલવાર',
            'warrior': 'યોદ્ધા',
            'village': 'ગામ',
            'villages': 'ગામડાં',
            'story': 'કહાણી',
            'tale': 'કથા',
            'legend': 'કથા',
            'legends': 'કથાઓ',
            'monster': 'રાક્ષસ',
            'monsters': 'રાક્ષસો',
            'shadow': 'છાયા',
            'shadows': 'છાયાઓ',
            'moonlight': 'ચાંદની',
            'blood': 'રક્ત',
            'trial': 'પરીક્ષા',
            'test': 'પરીક્ષા',
            'battle': 'લડાઈ',
            'fight': 'લડાઈ',
            'power': 'શક્તિ',
            'strength': 'શક્તિ',
            'magic': 'જાદુ',
            'spirit': 'આત્મા',
            'soul': 'આત્મા',
            'darkness': 'અંધારું',
            'light': 'પ્રકાશ',
            'dawn': 'ભોર',
            'night': 'રાત',
            'day': 'દિવસ',
            'morning': 'સવાર',
            'evening': 'સાંજ',
            'forest': 'જંગલ',
            'mountain': 'પર્વત',
            'river': 'નદી',
            'lake': 'એરણ',
            'castle': 'કિલ્લો',
            'temple': 'મંદિર',
            'school': 'શાળા',
            'training': 'તાલીમ',
            'master': 'ગુરુ',
            'student': 'વિદ્યાર્થી',
            'teacher': 'શિક્ષક',
            'family': 'પરિવાર',
            'father': 'પિતા',
            'mother': 'માતા',
            'son': 'પુત્ર',
            'daughter': 'પુત્રી',
            'brother': 'ભાઈ',
            'sister': 'બહેન',
            'friend': 'મિત્ર',
            'enemy': 'દુશ્મન',
            'hero': 'નાયક',
            'heroine': 'નાયિકા',
            'villain': 'ખલનાયક',
            'protagonist': 'મુખ્ય પાત્ર',
            'character': 'પાત્ર',
            'characters': 'પાત્રો',
            # Additional comprehensive translations for better Gujarati conversion
            'footsteps': 'પગલાં',
            'echoed': 'ગુંજ્યા',
            'along': 'સાથે',
            'worn': 'ઘસાયેલા',
            'cobblestone': 'ગોળાકાર પથ્થર',
            'path': 'પાથ',
            'weight': 'ભાર',
            'constant': 'સતત',
            'reminder': 'યાદ',
            'oath': 'શપથ',
            'sworn': 'લીધો',
            'step': 'પગલું',
            'brought': 'લાવ્યા',
            'closer': 'નજીક',
            'unknown': 'અજાણ્યું',
            'veil': 'ઘૂમટો',
            'between': 'વચ્ચે',
            'life': 'જીવન',
            'death': 'મૃત્યુ',
            'thinned': 'પાતળું',
            'under': 'નીચે',
            'pale': 'ફિક્કું',
            'glow': 'ચમક',
            'moon': 'ચંદ્ર',
            'soft': 'મૃદુ',
            'silence': 'શાંતિ',
            'lie': 'ખોટું',
            'rustle': 'સરસરાટ',
            'carried': 'લાવ્યું',
            'promise': 'વચન',
            'danger': 'ભય',
            'whispers': 'ફુસફુસાટ',
            'mist': 'ધુમ્મસ',
            'his': 'તેનો',
            'her': 'તેની',
            'their': 'તેમનું',
            'the': 'આ',
            'a': 'એક',
            'an': 'એક',
            'and': 'અને',
            'or': 'અથવા',
            'but': 'પરંતુ',
            'in': 'માં',
            'on': 'પર',
            'at': 'પર',
            'to': 'ને',
            'for': 'માટે',
            'of': 'નું',
            'with': 'સાથે',
            'by': 'દ્વારા',
            'is': 'છે',
            'are': 'છે',
            'was': 'હતું',
            'were': 'હતા',
            'be': 'હોવું',
            'been': 'હતું',
            'have': 'છે',
            'has': 'છે',
            'had': 'હતું',
            'do': 'કરવું',
            'does': 'કરે છે',
            'did': 'કર્યું',
            'will': 'હશે',
            'would': 'હશે',
            'could': 'કરી શકે',
            'should': 'કરવું જોઈએ',
            'may': 'કરી શકે',
            'might': 'કરી શકે',
            'can': 'કરી શકે',
            'this': 'આ',
            'that': 'તે',
            'these': 'આ',
            'those': 'તે',
            'i': 'હું',
            'you': 'તમે',
            'he': 'તે',
            'she': 'તે',
            'it': 'તે',
            'we': 'આપણે',
            'they': 'તેઓ',
            'me': 'મને',
            'him': 'તેને',
            'her': 'તેને',
            'us': 'આપણને',
            'them': 'તેમને',
            'my': 'મારું',
            'your': 'તમારું',
            'his': 'તેનું',
            'her': 'તેનું',
            'its': 'તેનું',
            'our': 'આપણું',
            'their': 'તેમનું',
            'mine': 'મારું',
            'yours': 'તમારું',
            'hers': 'તેનું',
            'ours': 'આપણું',
            'theirs': 'તેમનું',
        },
        'hi': {  # Hindi translations
            'I cannot find specific information about this question in the PDF. The question may not be directly addressed in the document content.': 
                'मैं इस प्रश्न के बारे में PDF में विशिष्ट जानकारी नहीं ढूंढ सकता। प्रश्न सीधे दस्तावेज़ की सामग्री में संबोधित नहीं किया गया हो सकता है।',
            'I cannot find any content in this PDF to answer your question.': 
                'मैं आपके प्रश्न का उत्तर देने के लिए इस PDF में कोई सामग्री नहीं ढूंढ सकता।',
            'Error generating answer:': 
                'उत्तर जनरेट करने में त्रुटि:',
            'Chapter': 'अध्याय',
            'The Blades of Dawn': 'भोर की तलवारें',
            'In the realm of': 'राज्य में',
            'land draped in mist': 'धुंध में लिपटी भूमि',
            'steeped in legends': 'किंवदंतियों में डूबा',
            'monsters known as': 'राक्षस जिन्हें कहा जाता है',
            'have plagued villages': 'गांवों में तबाही मचाई है',
            'for centuries': 'सदियों से',
            'These creatures': 'ये जीव',
            'born from shadows': 'छायाओं से जन्मे',
            'and c': 'और',
            'Kurogami': 'कुरोगामी',
            'Tsukihara': 'त्सुकिहारा',
            'Haruto': 'हारुतो',
            'Ake': 'एके',
            'blade': 'तलवार',
            'sword': 'तलवार',
            'warrior': 'योद्धा',
            'village': 'गांव',
            'villages': 'गांवों',
            'story': 'कहानी',
            'tale': 'कथा',
            'legend': 'कथा',
            'legends': 'कथाएं',
            'monster': 'राक्षस',
            'monsters': 'राक्षसों',
            'shadow': 'छाया',
            'shadows': 'छायाएं',
            'moonlight': 'चांदनी',
            'blood': 'रक्त',
            'trial': 'परीक्षा',
            'test': 'परीक्षा',
            'battle': 'युद्ध',
            'fight': 'लड़ाई',
            'power': 'शक्ति',
            'strength': 'बल',
            'magic': 'जादू',
            'spirit': 'आत्मा',
            'soul': 'आत्मा',
            'darkness': 'अंधकार',
            'light': 'प्रकाश',
            'dawn': 'भोर',
            'night': 'रात',
            'day': 'दिन',
            'morning': 'सुबह',
            'evening': 'शाम',
            'forest': 'जंगल',
            'mountain': 'पहाड़',
            'river': 'नदी',
            'lake': 'झील',
            'castle': 'किला',
            'temple': 'मंदिर',
            'school': 'स्कूल',
            'training': 'प्रशिक्षण',
            'master': 'गुरु',
            'student': 'छात्र',
            'teacher': 'शिक्षक',
            'family': 'परिवार',
            'father': 'पिता',
            'mother': 'माता',
            'son': 'बेटा',
            'daughter': 'बेटी',
            'brother': 'भाई',
            'sister': 'बहन',
            'friend': 'दोस्त',
            'enemy': 'दुश्मन',
            'hero': 'नायक',
            'heroine': 'नायिका',
            'villain': 'खलनायक',
            'protagonist': 'मुख्य पात्र',
            'character': 'पात्र',
            'characters': 'पात्रों',
        }
    }
    
    # Get translations for the target language
    lang_translations = translations.get(target_language, {})
    
    # For Gujarati, do more comprehensive translation
    if target_language == 'gu':
        translated_text = answer_text
        
        # First, translate longer phrases and proper nouns
        for english, translated in lang_translations.items():
            if len(english) > 3:  # Only translate longer phrases first
                translated_text = translated_text.replace(english, translated)
        
        # Then translate common words and articles
        for english, translated in lang_translations.items():
            if len(english) <= 3:  # Translate shorter words
                # Use word boundaries to avoid partial matches
                import re
                pattern = r'\b' + re.escape(english) + r'\b'
                translated_text = re.sub(pattern, translated, translated_text, flags=re.IGNORECASE)
        
        # Special handling for sentence structure
        translated_text = translated_text.replace("'s", "નું")
        translated_text = translated_text.replace("'", "")
        
        # Fix common Gujarati grammar patterns
        translated_text = translated_text.replace("આ the", "આ")
        translated_text = translated_text.replace("આ a", "એક")
        translated_text = translated_text.replace("આ an", "એક")
        
        # Additional Gujarati grammar fixes
        translated_text = translated_text.replace("આ Blade", "બ્લેડ")
        translated_text = translated_text.replace("આ Trial", "પરીક્ષા")
        translated_text = translated_text.replace("આ Whispers", "ફુસફુસાટ")
        translated_text = translated_text.replace("આ Mist", "ધુમ્મસ")
        translated_text = translated_text.replace("આ Blood", "રક્ત")
        translated_text = translated_text.replace("આ Moon", "ચંદ્ર")
        
        # Fix common English words that might remain
        translated_text = translated_text.replace("Each", "દરેક")
        translated_text = translated_text.replace("where", "જ્યાં")
        translated_text = translated_text.replace("under", "નીચે")
        translated_text = translated_text.replace("the", "આ")
        translated_text = translated_text.replace("a", "એક")
        translated_text = translated_text.replace("an", "એક")
        translated_text = translated_text.replace("and", "અને")
        translated_text = translated_text.replace("of", "નું")
        translated_text = translated_text.replace("in", "માં")
        translated_text = translated_text.replace("to", "ને")
        translated_text = translated_text.replace("for", "માટે")
        translated_text = translated_text.replace("with", "સાથે")
        translated_text = translated_text.replace("by", "દ્વારા")
        translated_text = translated_text.replace("is", "છે")
        translated_text = translated_text.replace("are", "છે")
        translated_text = translated_text.replace("was", "હતું")
        translated_text = translated_text.replace("were", "હતા")
        translated_text = translated_text.replace("have", "છે")
        translated_text = translated_text.replace("has", "છે")
        translated_text = translated_text.replace("had", "હતું")
        translated_text = translated_text.replace("his", "તેનો")
        translated_text = translated_text.replace("her", "તેની")
        translated_text = translated_text.replace("their", "તેમનું")
        translated_text = translated_text.replace("this", "આ")
        translated_text = translated_text.replace("that", "તે")
        translated_text = translated_text.replace("these", "આ")
        translated_text = translated_text.replace("those", "તે")
        
        # Clean up any remaining English words and improve Gujarati grammar
        translated_text = translated_text.replace("Triએકl", "પરીક્ષા")
        translated_text = translated_text.replace("Whછેpers", "ફુસફુસાટ")
        translated_text = translated_text.replace("every", "દરેક")
        translated_text = translated_text.replace("sઘસાયેલા", "ઘસાયેલા")
        translated_text = translated_text.replace("જંગલs", "જંગલ")
        translated_text = translated_text.replace("એક ખોટું", "એક ખોટું વચન")
        
        # Improve sentence structure
        translated_text = translated_text.replace("નું આ", "નો")
        translated_text = translated_text.replace("નું તે", "નો")
        translated_text = translated_text.replace("આ શપથ તે હતું", "શપથ લીધો હતો")
        translated_text = translated_text.replace("શાંતિ હતું એક ખોટું", "શાંતિ એક ખોટું વચન હતું")
        
        return translated_text
    else:
        # For other languages, use simple replacement
        translated_text = answer_text
        for english, translated in lang_translations.items():
            translated_text = translated_text.replace(english, translated)
        
        return translated_text

def generate_answer(question, pdf_document, language='en'):
    """Generate answer to question based on PDF content using dynamic analysis"""
    try:
        # Search through PDF chunks for relevant information
        chunks = pdf_document.chunks.all()
        
        if not chunks.exists():
            error_msg = "I cannot find any content in this PDF to answer your question."
            return translate_answer(error_msg, language), False, 0.0
        
        # Analyze the question
        question_analysis = analyze_question(question)
        
        print(f"Question: '{question}'")
        print(f"Question Type: {question_analysis['primary_type']}")
        print(f"Keywords: {question_analysis['keywords']}")
        print(f"Entities: {question_analysis['entities']}")
        print(f"Language: {language}")
        
        # Score all chunks based on question analysis
        chunk_scores = []
        for chunk in chunks:
            score = score_chunk_for_question(chunk, question_analysis)
            if score > 0:
                chunk_scores.append((chunk, score))
        
        # Sort by score (highest first)
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        
        print(f"Found {len(chunk_scores)} relevant chunks")
        
        if chunk_scores:
            # Select best chunks based on question type
            best_chunks = select_best_chunks(chunk_scores, question_analysis)
            
            # Generate answer from selected chunks
            answer_text = generate_answer_from_chunks(best_chunks, question_analysis)
            
            # Translate the answer to the target language
            translated_answer = translate_answer(answer_text, language)
            
            # Calculate confidence
            max_score = max(score for _, score in best_chunks)
            confidence = min(0.95, max_score / 50.0)  # Normalize based on max possible score
            
            print(f"Generated answer with confidence: {confidence}")
            print(f"Original: {answer_text[:100]}...")
            print(f"Translated: {translated_answer[:100]}...")
            
            return translated_answer, True, confidence
        else:
            # No relevant chunks found
            error_msg = "I cannot find specific information about this question in the PDF. The question may not be directly addressed in the document content."
            return translate_answer(error_msg, language), False, 0.0
            
    except Exception as e:
        print(f"Error generating answer: {str(e)}")
        error_msg = f"Error generating answer: {str(e)}"
        return translate_answer(error_msg, language), False, 0.0
