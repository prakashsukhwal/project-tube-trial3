from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from config import YOUTUBE_API_KEY, OPENAI_API_KEY, YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION
import re
import json

def get_youtube_service():
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)

def build_youtube_client():
    """Build and return a YouTube API client"""
    try:
        print(f"Building YouTube client with key: {YOUTUBE_API_KEY[:10]}...")
        client = build(
            YOUTUBE_API_SERVICE_NAME,
            YOUTUBE_API_VERSION,
            developerKey=YOUTUBE_API_KEY
        )
        print("YouTube client built successfully")
        return client
    except Exception as e:
        print(f"Error building YouTube client: {str(e)}")
        raise e

def search_videos(query, progress_callback=None):
    """Search YouTube videos and return processed results"""
    try:
        # Initialize YouTube API client
        youtube = build_youtube_client()
        
        # Debug logging
        print(f"Searching for query: {query}")
        print(f"YouTube API Key: {YOUTUBE_API_KEY[:10]}...")  # Show first 10 chars
        
        if progress_callback:
            progress_callback("Searching YouTube...")
        
        try:
            # Perform the search with increased maxResults
            request = youtube.search().list(
                q=query,
                part="id,snippet",
                type="video",
                maxResults=6,
                relevanceLanguage="en"
            )
            
            # Debug logging
            print("Making YouTube API request...")
            search_response = request.execute()
            print(f"Search Response: {json.dumps(search_response, indent=2)}")  # Log full response
            print(f"Got {len(search_response.get('items', []))} results")
            
        except HttpError as e:
            print(f"YouTube API Error: {str(e)}")
            print(f"Error details: {e.error_details if hasattr(e, 'error_details') else 'No details'}")
            raise e
        
        # Process videos
        videos = []
        for item in search_response.get("items", []):
            try:
                if item["id"]["kind"] == "youtube#video":
                    video_id = item["id"]["videoId"]
                    print(f"Processing video: {video_id}")
                    
                    # Get video details
                    video_data = get_video_metadata(video_id)
                    if video_data:
                        videos.append(video_data)
                        
                        if progress_callback:
                            progress_callback(f"Processed {len(videos)} of 6 videos...")
            except Exception as e:
                print(f"Error processing video: {str(e)}")
                continue
        
        if progress_callback:
            progress_callback("Ranking videos...")
        
        # Rank and return videos
        return rank_videos(videos)
    except Exception as e:
        print(f"Error in search_videos: {str(e)}")
        raise e

def get_content_rating(transcript: str, query: str) -> dict:
    """Rate content using OpenAI based on comprehensive content analysis"""
    client = OpenAI()
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """You are a content rating assistant. Analyze the content and return a JSON object.
                    Always respond with a valid JSON object in this exact format:
                    {
                        "rating": "[S/A/B/C/D]",
                        "score": number between 1-100,
                        "explanation": {
                            "main_reason": "Primary reason for the rating",
                            "strengths": ["List of content strengths"],
                            "weaknesses": ["List of content weaknesses"],
                            "relevance": "How well it matches the search query",
                            "idea_count": "Number of valuable ideas found",
                            "recommendation": "Brief recommendation for viewers"
                        }
                    }
                    
                    Criteria:
                    S Tier (Must Watch): 
                    - Contains 8+ unique, valuable ideas
                    - Strong match with search query
                    - High-quality, well-structured content
                    - Provides unique insights or expert knowledge
                    - Comprehensive coverage of the topic
                    
                    A Tier (Highly Recommended):
                    - Contains 6+ valuable ideas
                    - Good match with search query
                    - Clear and well-presented content
                    - Good depth of information
                    - Practical examples or demonstrations
                    
                    B Tier (Worth Watching):
                    - Contains 4+ useful ideas
                    - Moderate match with search query
                    - Decent content organization
                    - Basic but solid information
                    - Some practical value
                    
                    C Tier (Optional):
                    - Contains 2+ basic ideas
                    - Partial match with search query
                    - Basic or surface-level content
                    - Limited practical value
                    - May have some redundant information
                    
                    D Tier (Skip):
                    - Few meaningful ideas
                    - Poor match with search query
                    - Unclear or disorganized content
                    - Very basic or redundant information
                    - Little to no practical value"""},
                {"role": "user", "content": f"Query: {query}\n\nTranscript: {transcript}"}
            ],
            temperature=0.7
        )
        content = json.loads(response.choices[0].message.content)
        
        # Format the explanation in a user-friendly way
        explanation = f"""
Rating: {content['rating']} ({content['score']}/100)

Main Reason: {content['explanation']['main_reason']}

Strengths:
{chr(10).join('• ' + s for s in content['explanation']['strengths'])}

Weaknesses:
{chr(10).join('• ' + w for w in content['explanation']['weaknesses'])}

Relevance: {content['explanation']['relevance']}
Ideas Found: {content['explanation']['idea_count']}

Recommendation: {content['explanation']['recommendation']}
        """.strip()
        
        return {
            'rating': content['rating'],
            'score': content['score'],
            'explanation': explanation,
            'detailed_analysis': content['explanation']  # Keep raw data for potential use
        }
    
    except Exception as e:
        print(f"Error in content rating: {e}")
        return {
            'rating': 'D',
            'score': 0,
            'explanation': f'Error generating rating: {str(e)}',
            'detailed_analysis': None
        }

def check_transcript_availability(video_id):
    try:
        YouTubeTranscriptApi.get_transcript(video_id)
        return True
    except:
        return False

def get_video_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([entry['text'] for entry in transcript])
    except:
        return None

def generate_summary(transcript):
    if not transcript:
        return "No transcript available for summarization."
    
    client = OpenAI()
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes YouTube video transcripts."},
                {"role": "user", "content": f"Please summarize this transcript:\n\n{transcript}"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Error generating summary. Please try again later."

def get_video_metadata(video_id):
    """Fetch fresh metadata for a video"""
    try:
        print(f"Fetching metadata for video: {video_id}")
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        video_request = youtube.videos().list(
            part='snippet,statistics',
            id=video_id
        )
        video_response = video_request.execute()
        print(f"Got metadata response for {video_id}")
        
        if video_response['items']:
            video = video_response['items'][0]
            return {
                'id': video_id,
                'title': video['snippet']['title'],
                'description': video['snippet']['description'],
                'date': video['snippet']['publishedAt'],
                'views': int(video['statistics'].get('viewCount', 0)),
                'likes': int(video['statistics'].get('likeCount', 0)),
                'has_transcript': True
            }
        else:
            print(f"No items found in response for video {video_id}")
    except Exception as e:
        print(f"Error fetching video metadata: {str(e)}")
    return None

def rank_videos(videos):
    """Rank and rate videos based on their content"""
    try:
        ranked_videos = []
        for video in videos:
            # Get transcript
            transcript = get_video_transcript(video['id'])
            if not transcript:
                continue
            
            # Get content rating
            rating = get_content_rating(transcript, video.get('search_query', ''))
            
            # Extract rating tier and score
            if isinstance(rating, dict):
                video['rating_tier'] = rating.get('rating', 'D')
                video['content_score'] = rating.get('score', 0)
                video['rating_explanation'] = rating.get('explanation', 'No explanation provided')
            else:
                # Default values if rating is not in expected format
                video['rating_tier'] = 'D'
                video['content_score'] = 0
                video['rating_explanation'] = 'Rating unavailable'
            
            ranked_videos.append(video)
        
        # Sort by rating tier and content score
        tier_order = {'S': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4}
        ranked_videos.sort(key=lambda x: (tier_order[x['rating_tier']], -x['content_score']))
        
        return ranked_videos
    
    except Exception as e:
        print(f"Error in rank_videos: {e}")
        raise e 

def generate_summary_with_style(transcript: str, prompt_template: str) -> str:
    client = OpenAI()
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt_template},
                {"role": "user", "content": transcript}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Error generating summary. Please try again later." 