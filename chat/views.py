"""
API Views for AI Health Coach Chat

Provides RESTful endpoints for:
- Sending messages (regular and streaming)
- Loading message history with pagination
- Getting typing indicators
- User profile management
"""

from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from chat.services.chat_service import ChatService
from chat.services.protocol_service import ProtocolService
from chat.services.voice_service import VoiceService
from chat.models import Message, User
import json
import logging
import uuid
import tempfile
import os

logger = logging.getLogger(__name__)

# Initialize services
chat_service = ChatService()
protocol_service = ProtocolService()
voice_service = VoiceService()


def get_user_id_from_request(request):
    """Extract or create user ID from request."""
    # Try to get username from header (sent by frontend)
    username = request.headers.get('X-Username')
    
    if username:
        # Use username as user_id for isolated chat history
        return username.lower().strip()  # Normalize
    
    # Fallback to session-based ID if no username
    if 'user_id' not in request.session:
        request.session['user_id'] = str(uuid.uuid4())
        request.session.save()
    
    return request.session['user_id']


@require_http_methods(["GET"])
def index(request):
    """Serve the main chat interface."""
    from django.shortcuts import render
    return render(request, 'chat.html')


@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """
    Send a message and get AI response.
    
    Request body:
        {
            "content": "User message text"
        }
    
    Response:
        {
            "success": true,
            "data": {
                "user_message": {...},
                "assistant_message": {...}
            }
        }
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({
                'success': False,
                'error': 'Message content is required'
            }, status=400)
        
        # Get user ID
        user_id = get_user_id_from_request(request)
        
        # Process message
        result = chat_service.send_message(user_id, content)
        
        return JsonResponse({
            'success': True,
            'data': result
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error in send_message: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your message'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def stream_message(request):
    """
    Send a message and get a streaming response.
    
    Uses Server-Sent Events (SSE) to stream the AI response in real-time.
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({
                'success': False,
                'error': 'Message content is required'
            }, status=400)
        
        # Get user ID
        user_id = get_user_id_from_request(request)
        
        def event_stream():
            try:
                # Get or create user
                user = chat_service.get_or_create_user(user_id)
                
                # Save user message
                user_message = Message.create(
                    user_id=user_id,
                    role='user',
                    content=content.strip(),
                    tokens=chat_service.llm_service.count_tokens(content)
                )
                
                # Skip user info extraction for speed - do it asynchronously later
                # This removes ~1-2 seconds of latency
                
                # Get context - minimal for fastest response
                recent_messages = chat_service.get_recent_context(user_id, limit=5)
                
                # Prepare user data (minimal)
                user_data = {
                    'name': user.get('name'),
                    'age': user.get('age'),
                }
                
                # Stream response immediately
                full_content = ""
                for chunk in chat_service.llm_service.stream_response(
                    messages=recent_messages,
                    user_data=user_data,
                    memories=[],  # Skip for speed
                    protocols=[]  # Skip for speed
                ):
                    full_content += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                
                # Save assistant message
                assistant_message = Message.create(
                    user_id=user_id,
                    role='assistant',
                    content=full_content,
                    tokens=chat_service.llm_service.count_tokens(full_content)
                )
                
                # Send done event
                yield f"data: {json.dumps({'type': 'done', 'message_id': str(assistant_message['message_id']), 'created_at': assistant_message['created_at'].isoformat()})}\n\n"
                
            except Exception as e:
                logger.error(f"Error in stream: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
        
    except Exception as e:
        logger.error(f"Error in stream_message: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred'
        }, status=500)

@require_http_methods(["GET"])
def get_messages(request):
    """
    Get message history with pagination.
    
    Query parameters:
        - limit: Number of messages to return (default: 50)
        - before_id: Get messages before this message ID (for loading older messages)
    
    Response:
        {
            "success": true,
            "data": {
                "messages": [...],
                "has_more": true/false
            }
        }
    """
    try:
        # Get user ID
        user_id = get_user_id_from_request(request)
        
        # Get query parameters
        limit = int(request.GET.get('limit', 50))
        before_id = request.GET.get('before_id')
        
        # Validate limit
        if limit < 1 or limit > 100:
            limit = 50
        
        # Get messages
        messages = chat_service.get_messages(user_id, limit + 1, before_id)
        
        # Check if there are more messages
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]
        
        return JsonResponse({
            'success': True,
            'data': {
                'messages': messages,
                'has_more': has_more
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_messages: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while loading messages'
        }, status=500)


@require_http_methods(["GET"])
def get_typing_status(request):
    """
    Get typing indicator status.
    
    Response:
        {
            "success": true,
            "data": {
                "is_typing": true/false
            }
        }
    """
    try:
        user_id = get_user_id_from_request(request)
        is_typing = chat_service.get_typing_indicator(user_id)
        
        return JsonResponse({
            'success': True,
            'data': {
                'is_typing': is_typing
            }
        })
        
    except Exception as e:
        logger.error(f"Error in get_typing_status: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred'
        }, status=500)


@require_http_methods(["GET"])
def get_user_profile(request):
    """
    Get user profile information.
    
    Response:
        {
            "success": true,
            "data": {
                "user_id": "...",
                "name": "...",
                ...
            }
        }
    """
    try:
        user_id = get_user_id_from_request(request)
        profile = chat_service.get_user_profile(user_id)
        
        if profile:
            return JsonResponse({
                'success': True,
                'data': profile
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'User not found'
            }, status=404)
        
    except Exception as e:
        logger.error(f"Error in get_user_profile: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def set_username(request):
    """
    Set username for the current user.
    
    Request body:
        {
            "username": "User's name"
        }
    
    Response:
        {
            "success": true
        }
    """
    try:
        import re
        
        data = json.loads(request.body)
        username = data.get('username', '').strip().lower()
        
        # Validate username
        if not username:
            return JsonResponse({
                'success': False,
                'error': 'Username is required'
            }, status=400)
        
        if len(username) < 3:
            return JsonResponse({
                'success': False,
                'error': 'Username must be at least 3 characters long'
            }, status=400)
        
        if len(username) > 50:
            return JsonResponse({
                'success': False,
                'error': 'Username must be at most 50 characters long'
            }, status=400)
        
        # Check if username contains only allowed characters (alphanumeric, hyphens, underscores)
        if not re.match(r'^[a-z0-9_-]+$', username):
            return JsonResponse({
                'success': False,
                'error': 'Username can only contain letters, numbers, hyphens and underscores'
            }, status=400)
        
        user_id = get_user_id_from_request(request)
        
        # Update user with username
        User.update(user_id, name=username)
        
        return JsonResponse({
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in set_username: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def onboard_user(request):
    """
    Onboard a new user with initial health information.
    
    Request body:
        {
            "username": "unique_username",
            "name": "User's full name",
            "age": 25,
            "gender": "male/female/other",
            "health_goals": ["lose weight", "improve fitness"]
        }
    
    Response:
        {
            "success": true
        }
    """
    try:
        import re
        
        data = json.loads(request.body)
        username = data.get('username', '').strip().lower()
        name = data.get('name', '').strip()
        age = data.get('age')
        gender = data.get('gender', '').strip().lower()
        health_goals = data.get('health_goals', [])
        
        # Validate username
        if not username:
            return JsonResponse({
                'success': False,
                'error': 'Username is required'
            }, status=400)
        
        if len(username) < 3:
            return JsonResponse({
                'success': False,
                'error': 'Username must be at least 3 characters long'
            }, status=400)
        
        if not re.match(r'^[a-z0-9_-]+$', username):
            return JsonResponse({
                'success': False,
                'error': 'Username can only contain letters, numbers, hyphens and underscores'
            }, status=400)
        
        # Validate name
        if not name:
            return JsonResponse({
                'success': False,
                'error': 'Name is required'
            }, status=400)
        
        # Validate age
        if not age or not isinstance(age, int) or age < 1 or age > 120:
            return JsonResponse({
                'success': False,
                'error': 'Please enter a valid age between 1 and 120'
            }, status=400)
        
        # Create or update user with onboarding data
        user_data = {
            'name': name,
            'age': age,
            'onboarding_completed': True
        }
        
        if gender:
            user_data['gender'] = gender
        
        if health_goals:
            user_data['health_goals'] = health_goals
        
        User.update(username, **user_data)
        
        return JsonResponse({
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in onboard_user: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred during onboarding'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def seed_protocols(request):
    """
    Seed default medical protocols.
    
    This endpoint should be called once during initial setup.
    In production, this should be protected or removed.
    """
    try:
        count = protocol_service.seed_default_protocols()
        return JsonResponse({
            'success': True,
            'message': f'Successfully seeded {count} protocols'
        })
    except Exception as e:
        logger.error(f"Error seeding protocols: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for monitoring.
    
    Response:
        {
            "status": "healthy",
            "timestamp": "..."
        }
    """
    from django.utils import timezone
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat()
    })


@csrf_exempt
@require_http_methods(["POST"])
def transcribe_audio(request):
    """
    Transcribe audio to text using OpenAI Whisper.
    
    Request:
        Multipart form data with 'audio' file
    
    Response:
        {
            "success": true,
            "text": "transcribed text",
            "language": "en"
        }
    """
    try:
        # Get audio file from request
        if 'audio' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No audio file provided'
            }, status=400)
        
        audio_file = request.FILES['audio']
        
        # Validate file size (max 25MB for Whisper)
        if audio_file.size > 25 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'error': 'Audio file too large (max 25MB)'
            }, status=400)
        
        # Transcribe using Whisper
        result = voice_service.transcribe_audio(audio_file)
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)
        
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred during transcription'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_speech(request):
    """
    Generate speech from text using OpenAI TTS.
    
    Request body:
        {
            "text": "Text to convert to speech",
            "speed": 1.0  // Optional, default 1.0
        }
    
    Response:
        Audio file (MP3 format)
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        speed = float(data.get('speed', 1.0))
        
        if not text:
            return JsonResponse({
                'success': False,
                'error': 'Text is required'
            }, status=400)
        
        # Validate speed
        if speed < 0.25 or speed > 4.0:
            speed = 1.0
        
        # Generate speech
        audio_data = voice_service.generate_speech(text, speed)
        
        # Return audio file
        response = HttpResponse(audio_data, content_type='audio/mpeg')
        response['Content-Disposition'] = 'inline; filename="speech.mp3"'
        response['Cache-Control'] = 'no-cache'
        return response
        
    except Exception as e:
        logger.error(f"Error in generate_speech: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred during speech generation'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def voice_chat(request):
    """
    Combined endpoint: transcribe audio, get AI response, and return speech.
    Optimized for lowest latency voice conversations.
    
    Request:
        Multipart form data with 'audio' file
    
    Response:
        Audio file (MP3 format) with AI response
    """
    try:
        # Get audio file from request
        if 'audio' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No audio file provided'
            }, status=400)
        
        audio_file = request.FILES['audio']
        user_id = get_user_id_from_request(request)
        
        # Step 1: Transcribe audio (Whisper)
        transcription = voice_service.transcribe_audio(audio_file)
        
        if not transcription['success']:
            return JsonResponse(transcription, status=500)
        
        user_text = transcription['text']
        
        # Step 2: Save user message
        user_message = Message.create(
            user_id=user_id,
            role='user',
            content=user_text,
            tokens=chat_service.llm_service.count_tokens(user_text)
        )
        
        # Step 3: Get AI response - optimized for lowest latency
        user = chat_service.get_or_create_user(user_id)
        recent_messages = chat_service.get_recent_context(user_id, limit=6)  # Further reduced for speed
        
        # Skip memory/protocol lookup for faster response (can be added back if needed)
        memories = []
        protocols = []
        
        user_data = {
            'name': user.get('name'),
            'age': user.get('age'),
            'gender': user.get('gender'),
            'health_conditions': user.get('health_conditions', []),
            'medications': user.get('medications', []),
            'allergies': user.get('allergies', [])
        }
        
        # Generate AI response with optimized settings for voice
        ai_response = chat_service.llm_service.generate_response(
            messages=recent_messages,
            user_data=user_data,
            memories=memories,
            protocols=protocols,
            temperature=0.7,
            max_tokens=200  # Shorter responses for faster voice output
        )
        
        ai_text = ai_response['content']
        
        # Step 4: Save assistant message
        Message.create(
            user_id=user_id,
            role='assistant',
            content=ai_text,
            tokens=ai_response.get('tokens', 0)
        )
        
        # Step 5: Generate speech from AI response
        audio_data = voice_service.generate_speech(ai_text, speed=1.1)  # Slightly faster
        
        # Return audio response
        response = HttpResponse(audio_data, content_type='audio/mpeg')
        response['Content-Disposition'] = 'inline; filename="response.mp3"'
        response['Cache-Control'] = 'no-cache'
        # Encode text for headers (remove newlines and limit length)
        response['X-Transcript'] = user_text.replace('\n', ' ').replace('\r', ' ')[:500]
        response['X-Response-Text'] = ai_text.replace('\n', ' ').replace('\r', ' ')[:500]
        return response
        
    except Exception as e:
        logger.error(f"Error in voice_chat: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred during voice chat'
        }, status=500)
