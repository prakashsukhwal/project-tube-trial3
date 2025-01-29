import streamlit as st
import pandas as pd
from datetime import datetime
from utils import search_videos, get_video_transcript, generate_summary, get_video_metadata
import json
from summary_styles import DEFAULT_STYLES, get_style_prompt, get_style_description
from openai import OpenAI
from config import OPENAI_API_KEY
from languages import SUPPORTED_LANGUAGES, UI_TEXT
from database import DatabaseManager, init_db
from auth import show_login_page, show_signup_page, check_auth, logout as auth_logout
import base64

def handle_search_input():
    """Callback for search input - handles Enter key press"""
    current_input = st.session_state.get(f"search_input_{st.session_state.get('reset_count', 0)}")
    
    if current_input:  # Only trigger search if there's input
        st.session_state.is_searching = True  # Set searching state
        st.session_state.new_search_query = current_input
        st.session_state.start_new_search = True

def setup_page_config():
    st.set_page_config(
        page_title="Video Search & Summary",
        page_icon="🎥",
        layout="wide"
    )
    
    # Modern UI styling with improved colors and mobile responsiveness
    st.markdown("""
        <style>
        /* Mobile-first responsive design */
        :root {
            --primary-color: #7C3AED;
            --primary-light: #DDD6FE;
            --background-color: #F9FAFB;
            --card-background: #FFFFFF;
            --text-color: #1F2937;
            --text-secondary: #6B7280;
            --border-radius: 16px;
        }
        
        @media (max-width: 768px) {
            .main {
                padding: 0.5rem;
            }
            
            .video-card {
                margin: 0.5rem 0;
                padding: 1rem;
            }
            
            .stButton > button {
                width: 100%;
                margin: 0.25rem 0;
            }
            
            /* Stack columns on mobile */
            .row-widget.stHorizontal > div {
                flex: 0 1 100%;
                width: 100%;
            }
            
            /* Adjust text sizes for mobile */
            .main * {
                font-size: 14px;
            }
            
            h1 {
                font-size: 24px;
            }
            
            h2 {
                font-size: 20px;
            }
            
            h3 {
                font-size: 18px;
            }
        }
        
        /* Main container styling */
        .main {
            background-color: var(--background-color);
            font-family: 'Inter', sans-serif;
        }
        
        /* Search bar styling */
        .stTextInput > div > div > input {
            border-radius: var(--border-radius);
            border: 2px solid #E5E7EB;
            padding: 1rem;
            font-size: 1.1rem;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px var(--primary-light);
        }
        
        /* Button styling */
        .stButton > button {
            border-radius: var(--border-radius);
            padding: 0.75rem 1.5rem;
            background: linear-gradient(135deg, var(--primary-color), #6D28D9);
            color: white;
            border: none;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 15px rgba(124, 58, 237, 0.2);
        }
        
        /* Card styling */
        .video-card {
            background: var(--card-background);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            box-shadow: var(--shadow);
            margin-bottom: 2rem;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            border: 1px solid #E5E7EB;
        }
        
        .video-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-radius: var(--border-radius);
            background-color: var(--primary-light);
            padding: 4px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: var(--border-radius);
            padding: 0.5rem 1rem;
            font-weight: 500;
        }
        
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background: var(--primary-color);
            color: white;
        }
        
        /* Selectbox styling */
        .stSelectbox > div > div {
            border-radius: var(--border-radius);
        }
        
        /* Text area styling */
        .stTextArea > div > div > textarea {
            border-radius: var(--border-radius);
            border: 2px solid #E5E7EB;
        }
        
        /* Info boxes */
        .stAlert {
            background-color: var(--primary-light);
            color: var(--primary-color);
            border-radius: var(--border-radius);
            border: none;
            padding: 1rem;
        }
        
        /* Summary container */
        .summary-container {
            background-color: #F3F4F6;
            border-radius: var(--border-radius);
            padding: 1rem;
            margin-top: 1rem;
            border-left: 4px solid var(--primary-color);
        }
        
        /* Video stats */
        .video-stats {
            display: flex;
            gap: 1rem;
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }
        
        .video-stats span {
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }
        </style>
        
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    
    # Update the CSS to support dark mode
    dark_mode = st.session_state.dark_mode
    st.markdown(f"""
        <style>
        /* Modern color scheme and fonts */
        :root {{
            --primary-color: {("#7C3AED", "#9F7AEA")[dark_mode]};
            --primary-light: {("#DDD6FE", "#553C9A")[dark_mode]};
            --background-color: {("#F9FAFB", "#1A202C")[dark_mode]};
            --card-background: {("#FFFFFF", "#2D3748")[dark_mode]};
            --text-color: {("#1F2937", "#F7FAFC")[dark_mode]};
            --text-secondary: {("#6B7280", "#A0AEC0")[dark_mode]};
            --border-radius: 16px;
        }}
        
        /* Rest of your CSS with color variables */
        body {{
            background-color: var(--background-color);
            color: var(--text-color);
        }}
        
        .stApp {{
            background-color: var(--background-color);
        }}
        
        /* Update other CSS rules to use variables */
        ...
        </style>
    """, unsafe_allow_html=True)

    # Add CSS for consistent button styling
    st.markdown("""
        <style>
            /* Make all buttons consistent height */
            [data-testid="stButton"] button {
                height: 42px !important;
                padding: 0 16px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            /* Equal width columns */
            [data-testid="column"] {
                width: 50% !important;
                flex: 1 1 calc(50% - 1rem) !important;
            }
        </style>
    """, unsafe_allow_html=True)

def sort_videos(videos, sort_by):
    """Sort videos based on selected criteria"""
    if not videos:
        return videos
    
    # Define tier order (S is highest)
    tier_order = {'S': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4}
    
    if sort_by == "Date":
        # Sort by date first, then by tier
        videos.sort(key=lambda x: (x['date'], tier_order[x['rating_tier']]), reverse=True)
    elif sort_by == "Views":
        # Sort by views first, then by tier
        videos.sort(key=lambda x: (x['views'], -tier_order[x['rating_tier']]), reverse=True)
    elif sort_by == "Rating":
        # Sort by tier first, then by content score
        videos.sort(key=lambda x: (tier_order[x['rating_tier']], -x['content_score']))
    elif sort_by == "Content Score":
        # Sort by content score first, then by tier
        videos.sort(key=lambda x: (x['content_score'], -tier_order[x['rating_tier']]), reverse=True)
    else:  # "Relevance" or default
        # Sort by tier first, maintain original order within tiers
        videos.sort(key=lambda x: tier_order[x['rating_tier']])
    
    return videos

def create_search_section():
    # Get search state at the start
    is_searching = st.session_state.get('is_searching', False)
    
    # Add welcome message with user info and avatar
    st.markdown(f"""
        <div style="
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        ">
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
            ">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <img src="{get_user_avatar(st.session_state.user['username'])}" 
                         style="width: 48px; height: 48px; border-radius: 50%;" />
                    <div>
                        <h4 style="margin: 0; color: #1f2937;">Welcome, {st.session_state.user['username']}! 👋</h4>
                        <p style="margin: 0; color: #6b7280; font-size: 0.9rem;">
                            {' 🔑 Admin User' if st.session_state.user['is_admin'] else ' 👤 Regular User'}
                        </p>
                    </div>
                </div>
                <div style="color: #6b7280; font-size: 0.9rem;">
                    {datetime.now().strftime('%B %d, %Y')}
                </div>
            </div>
            <div style="
                background-color: #e9ecef;
                padding: 0.5rem;
                border-radius: 0.3rem;
                margin-top: 0.5rem;
                font-size: 0.9rem;
                color: #666;
            ">
                📝 Note: Search results are stored for 2 days for quick access. After that, a new search will be performed.
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.title("Video Search & Summary")
    
    # Search bar and buttons
    search_col, filter_col = st.columns([3, 1])
    with search_col:
        search_input_key = f"search_input_{st.session_state.get('reset_count', 0)}"
        
        search_query = st.text_input(
            "Search videos (press Enter or click Search)", 
            value="",  # Don't restore old query
            placeholder="Enter keywords...",
            key=search_input_key,
            on_change=handle_search_input
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Search", key="search_button", type="primary", use_container_width=True):
                if search_query:
                    # Set searching state immediately
                    st.session_state.is_searching = True
                    st.session_state.new_search_query = search_query
                    st.session_state.start_new_search = True
                    st.rerun()  # Changed from experimental_rerun
        
        with col2:
            # Reset button
            if st.button("🔄 Reset Search", key="reset_search", type="secondary", use_container_width=True):
                # Clear all search-related state
                st.session_state.is_searching = False  # Reset searching state
                st.session_state.reset_count = st.session_state.get('reset_count', 0) + 1
                st.session_state.search_query = ''
                st.session_state.current_videos = None
                st.session_state.last_search_results = None
                st.session_state.last_search_query = ''
                st.session_state.search_history = []
                st.session_state.summaries = {}
                st.session_state.shown_transcripts = {}
                st.session_state.active_tab = {}
                st.session_state.current_sort = 'Relevance'
                st.session_state.rating_filter = ["S", "A", "B", "C", "D"]
                st.session_state.search_count = 0
    
    # Add rating filter with tooltips
    with filter_col:
        # Sort by dropdown - Add proper label
        st.write("Sort by:")
        sort_by = st.selectbox(
            label="Sort videos by",  # Added proper label
            options=["Relevance", "Date", "Views", "Rating", "Content Score"],
            key="sort_selector",
            index=["Relevance", "Date", "Views", "Rating", "Content Score"].index(st.session_state.current_sort),
            disabled=st.session_state.get('is_searching', False),
            label_visibility="collapsed"  # Hide label but keep it for accessibility
        )
        
        # Update current sort in session state when changed
        if sort_by != st.session_state.current_sort:
            st.session_state.current_sort = sort_by
        
        # Rating filter multiselect - Add proper label
        st.markdown("""
            <div style="margin: 1rem 0 0.5rem 0;">
                Filter by Rating:
                <span class="tooltip" title="S: Must Watch - 12+ ideas or strong match&#10;A: Highly Recommended - 9+ ideas or good match&#10;B: Worth Watching - 7+ ideas or moderate match&#10;C: Optional - 5+ ideas or weak match&#10;D: Skip - Few ideas or poor match">ℹ️</span>
            </div>
        """, unsafe_allow_html=True)
        
        # Initialize with all ratings for new searches or reset
        if (search_query and search_query not in st.session_state.search_history) or \
           'rating_filter' not in st.session_state:
            st.session_state.rating_filter = ["S", "A", "B", "C", "D"]
        
        rating_filter = st.multiselect(
            label="Filter videos by rating",  # Added proper label
            options=["S", "A", "B", "C", "D"],
            default=st.session_state.rating_filter,
            key=f"rating_filter_{st.session_state.get('reset_count', 0)}",
            disabled=st.session_state.get('is_searching', False),
            label_visibility="collapsed"  # Hide label but keep it for accessibility
        )
        
        if rating_filter:  # Only update if user has made a selection
            st.session_state.rating_filter = rating_filter
    
    return search_query, sort_by, rating_filter

def get_available_patterns(user_id=None):
    """Get all available patterns including defaults and user patterns"""
    # Get default patterns
    default_patterns = [
        {
            'name': name,
            'description': style.get('description', ''),
            'prompt_template': style.get('prompt', '')
        }
        for name, style in DEFAULT_STYLES.items()
    ]
    
    # Get user patterns from database if user_id is provided
    db_patterns = []
    if user_id:
        db = DatabaseManager()
        patterns = db.get_user_patterns(user_id)
        db_patterns = [
            {
                'name': p[2],
                'description': p[3],
                'prompt_template': p[4]
            }
            for p in patterns
        ]
    
    # Combine both sets of patterns
    return default_patterns + db_patterns

def display_video_grid(videos, rating_filter):
    """Display videos in a grid with sorting and filtering"""
    # Get search state at the start
    is_searching = st.session_state.get('is_searching', False)
    
    # Filter videos
    filtered_videos = [v for v in videos if v['rating_tier'] in rating_filter]
    if not filtered_videos:
        st.info("No videos match the selected filters")
        return
    
    # Sort videos
    sort_by = st.session_state.get('current_sort', 'Relevance')
    sorted_videos = sort_videos(filtered_videos.copy(), sort_by)  # Make a copy to avoid modifying original
    
    # Display videos
    num_videos = len(sorted_videos)
    num_rows = (num_videos + 1) // 2
    
    # Create grid layout
    for row in range(num_rows):
        cols = st.columns(2)
        for col in range(2):
            video_idx = row * 2 + col
            if video_idx < num_videos:  # Only process if we have a video
                with cols[col]:
                    video = sorted_videos[video_idx]
                    
                    # Rating colors
                    rating_colors = {
                        'S': '#FFD700',
                        'A': '#C0C0C0',
                        'B': '#CD7F32',
                        'C': '#808080',
                        'D': '#A52A2A'
                    }
                    
                    # Video card container
                    st.markdown("""
                        <div style="
                            background: white;
                            border-radius: 10px;
                            padding: 1.5rem;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                            margin-bottom: 2rem;
                        ">
                    """, unsafe_allow_html=True)
                    
                    # Rating badge
                    st.markdown(f"""
                        <div style="
                            background-color: {rating_colors[video['rating_tier']]};
                            color: white;
                            padding: 4px 8px;
                            border-radius: 4px;
                            display: inline-block;
                            margin-bottom: 1rem;
                        ">
                            {video['rating_tier']} Tier (Score: {video['content_score']})
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Rest of your video card content...
                    with st.expander("Rating Explanation"):
                        st.write(video['rating_explanation'])
                    
                    st.video(f"https://youtu.be/{video['id']}")
                    
                    st.markdown(f"""
                        <div style="margin: 1rem 0;">
                            <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">
                                {video['title']}
                            </div>
                            <div style="display: flex; gap: 1rem; color: #666;">
                                <span>👁️ {video['views']:,}</span>
                                <span>👍 {video['likes']:,}</span>
                                <span>📅 {video['date'][:10]}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Tabs for transcript and summary
                    if video['has_transcript']:
                        tab_id = f"tabs_{video['id']}"
                        if tab_id not in st.session_state.active_tab:
                            st.session_state.active_tab[tab_id] = "Video"
                        
                        tabs = st.tabs(["Video", "Transcript"])
                        
                        with tabs[0]:
                            pass  # Video is already shown above
                        
                        with tabs[1]:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                transcript_key = f"transcript_{video['id']}"
                                if st.button("View Transcript", 
                                           key=f"btn_transcript_{video['id']}"):
                                    st.session_state.shown_transcripts[transcript_key] = True
                                
                                if st.session_state.shown_transcripts.get(transcript_key, False):
                                    transcript = get_video_transcript(video['id'])
                                    
                                    st.text_area("Transcript", transcript, height=200)
                                    
                                    st.download_button(
                                        label="Download Transcript",
                                        data=transcript,
                                        file_name=f"transcript_{video['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                        mime="text/plain"
                                    )
                            
                            with col2:
                                # Get all available patterns
                                all_patterns = get_available_patterns(st.session_state.user['user_id'])
                                pattern_names = [p['name'] for p in all_patterns]
                                
                                if pattern_names:  # Only show if there are patterns
                                    selected_style = st.selectbox(
                                        label="Select summary style",
                                        options=pattern_names,
                                        key=f"style_{video['id']}",
                                        disabled=is_searching
                                    )
                                    
                                    # Summarize button - disabled during search
                                    if st.button(
                                        "Summarize", 
                                        key=f"summarize_{video['id']}", 
                                        disabled=is_searching,
                                        use_container_width=True
                                    ):
                                        with st.spinner("Generating summary..."):
                                            transcript = get_video_transcript(video['id'])
                                            selected_pattern = next(p for p in all_patterns if p['name'] == selected_style)
                                            summary = generate_summary_with_style(transcript, selected_pattern['prompt_template'])
                                            st.session_state.summaries[f"summary_{video['id']}"] = summary
                                            st.rerun()
                                
                                # Display summary if it exists
                                if f"summary_{video['id']}" in st.session_state.summaries:
                                    summary = st.session_state.summaries[f"summary_{video['id']}"]
                                    st.markdown('<div class="summary-container">', unsafe_allow_html=True)
                                    st.info(summary)
                                    st.markdown('</div>', unsafe_allow_html=True)
                                    
                                    st.download_button(
                                        label="Download Summary",
                                        data=summary,
                                        file_name=f"summary_{video['id']}_{selected_style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                        mime="text/plain",
                                        key=f"download_summary_{video['id']}"
                                    )
                    
                    st.markdown("</div>", unsafe_allow_html=True)

def logout():
    """Clear all session state and redirect to login page"""
    st.session_state.clear()
    st.rerun()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def cache_search_results(search_query, videos):
    """Cache search results with query as key"""
    return videos

def init_session_state():
    """Initialize session state with persistence"""
    # Get existing state
    existing_state = dict(st.session_state)
    
    # If authenticated, restore complete state from database
    if existing_state.get('authenticated') and existing_state.get('user'):
        db = DatabaseManager()
        saved_state = db.get_search_state(existing_state['user']['user_id'])
        if saved_state:
            existing_state.update(saved_state)
    
    # Define defaults while preserving existing values
    defaults = {
        'initialized': True,
        'authenticated': existing_state.get('authenticated', False),
        'user': existing_state.get('user'),
        'auth_data': existing_state.get('auth_data'),
        'search_history': existing_state.get('search_history', []),
        'current_videos': existing_state.get('current_videos'),
        'last_search_results': existing_state.get('last_search_results'),
        'last_search_query': existing_state.get('last_search_query', ''),
        'summaries': existing_state.get('summaries', {}),
        'shown_transcripts': existing_state.get('shown_transcripts', {}),
        'active_tab': existing_state.get('active_tab', {}),
        'language': existing_state.get('language', "English"),
        'is_searching': False,
        'search_count': existing_state.get('search_count', 0),
        'reset_count': existing_state.get('reset_count', 0),
        'search_query': existing_state.get('search_query', ''),
        'current_sort': existing_state.get('current_sort', 'Relevance'),
        'rating_filter': existing_state.get('rating_filter', ["S", "A", "B", "C", "D"]),
        'enter_pressed': False,
        'pattern_form_state': existing_state.get('pattern_form_state', {
            'show_form': False,
            'name': '',
            'description': '',
            'prompt': '',
            'is_public': False
        })
    }
    
    # Update session state
    st.session_state.update(defaults)

def add_sidebar_features():
    # Get search state at the start
    is_searching = st.session_state.get('is_searching', False)
    
    with st.sidebar:
        # Logout button at the top - always enabled
        if st.button("🚪 Logout", type="primary", use_container_width=True):
            auth_logout()
            st.rerun()
        
        st.divider()
        
        # Patterns section
        st.markdown("## Patterns")
        
        # Add Pattern button - disabled during search
        if st.button("Add Your Pattern", type="primary", disabled=is_searching, use_container_width=True):
            st.session_state.show_pattern_form = True
        
        # Pattern form - disabled during search
        if st.session_state.get('show_pattern_form', False) and not is_searching:
            with st.form("new_pattern_form"):
                pattern_name = st.text_input("Pattern Name")
                pattern_description = st.text_input("Description")
                pattern_prompt = st.text_area("Prompt Template", height=150)
                is_public = st.checkbox("Make Public")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Save", disabled=is_searching):
                        try:
                            db = DatabaseManager()
                            db.add_pattern(
                                user_id=st.session_state.user['user_id'],
                                name=pattern_name,
                                description=pattern_description,
                                prompt_template=pattern_prompt,
                                is_public=is_public
                            )
                            st.success(f"Pattern '{pattern_name}' added successfully!")
                            st.session_state.show_pattern_form = False
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                with col2:
                    if st.form_submit_button("Cancel", disabled=is_searching):
                        st.session_state.show_pattern_form = False
        
        # Default Patterns section - disabled during search
        st.markdown("### Available Patterns:")
        st.markdown("#### Default Patterns:")
        default_pattern = st.selectbox(
            "Select Default Pattern",
            options=list(DEFAULT_STYLES.keys()),
            key="default_pattern",
            disabled=is_searching
        )
        
        # User Patterns section - disabled during search
        st.markdown("#### Your Patterns:")
        db = DatabaseManager()
        patterns = db.get_user_patterns(st.session_state.user['user_id'])
        
        if patterns:
            selected_pattern = st.selectbox(
                "Select Your Pattern",
                options=[p[2] for p in patterns],
                key="user_pattern",
                disabled=is_searching
            )
            
            if selected_pattern:
                pattern = next(p for p in patterns if p[2] == selected_pattern)
                # Delete button - disabled during search
                if st.button("🗑 Delete Pattern", 
                            key=f"delete_{pattern[0]}", 
                            disabled=is_searching):
                    db.delete_pattern(pattern[0])
                    st.success("Pattern deleted!")

def generate_summary_with_style(transcript: str, prompt_template: str) -> str:
    """Generate summary using provided prompt template."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="gpt-4",  # Using GPT-4 for styled summaries
            messages=[
                {"role": "system", "content": prompt_template},
                {"role": "user", "content": transcript}
            ],
            temperature=0.7
        )
        summary = response.choices[0].message.content
        return summary
    except Exception as e:
        print(f"Error generating summary: {e}")
        current_lang = st.session_state.get('language', 'en')
        error_msg = "Error generating summary. Please try again later."
        return error_msg

def show_patterns_section():
    st.subheader("Patterns")
    
    db = DatabaseManager()
    user_id = st.session_state.user['user_id']
    is_admin = st.session_state.user['is_admin']
    
    # Add new pattern button
    if st.button("Add New Pattern"):
        st.session_state.show_pattern_form = True
    
    # Form to add new pattern
    if st.session_state.get('show_pattern_form', False):
        with st.form("new_pattern_form"):
            pattern_name = st.text_input("Pattern Name")
            pattern_description = st.text_input("Description")
            pattern_prompt = st.text_area("Prompt Template")
            is_public = st.checkbox("Make Public")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Save", disabled=is_searching):
                    try:
                        db.add_pattern(
                            user_id=user_id,
                            name=pattern_name,
                            description=pattern_description,
                            prompt_template=pattern_prompt,
                            is_public=is_public
                        )
                        st.session_state.show_pattern_form = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            with col2:
                if st.form_submit_button("Cancel", disabled=is_searching):
                    st.session_state.show_pattern_form = False
                    st.rerun()
    
    # Display patterns
    if is_admin:
        patterns = db.get_all_patterns()
        # Add download button for all patterns
        if st.button("📥 Download All Users' Patterns"):
            patterns_data = []
            for p in patterns:
                patterns_data.append({
                    'pattern_id': p[0],
                    'user_id': p[1],
                    'name': p[2],
                    'description': p[3],
                    'prompt_template': p[4],
                    'is_public': p[5],
                    'created_at': p[6],
                    'username': p[7]  # From the JOIN in get_all_patterns
                })
            df = pd.DataFrame(patterns_data)
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"all_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    else:
        patterns = db.get_user_patterns(user_id)
    
    # Add download button for user's patterns
    if patterns:
        user_patterns_data = []
        for p in patterns:
            user_patterns_data.append({
                'name': p[2],
                'description': p[3],
                'prompt_template': p[4],
                'is_public': p[5],
                'created_at': p[6]
            })
        df = pd.DataFrame(user_patterns_data)
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download My Patterns",
            data=csv,
            file_name=f"my_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Display patterns in a modern card layout
    st.write("Available Patterns:")
    for pattern in patterns:
        with st.expander(pattern[2]):  # pattern name
            st.write(f"Description: {pattern[3]}")
            st.text_area("Prompt Template", pattern[4], disabled=True)
            if is_admin:
                st.write(f"Created by: {pattern[7]}")  # Username from JOIN
            if pattern[1] == user_id or is_admin:  # user_id or admin
                if st.button("🗑️ Delete", key=f"delete_{pattern[0]}"):
                    db.delete_pattern(pattern[0])
                    st.rerun()

def get_user_avatar(username: str) -> str:
    """Generate a consistent avatar URL for a user based on their username"""
    # Using DiceBear API for consistent avatars
    avatar_styles = ['adventurer', 'avataaars', 'bottts', 'fun-emoji', 'personas']
    # Use hash of username to consistently select same style for same user
    style = avatar_styles[hash(username) % len(avatar_styles)]
    return f"https://api.dicebear.com/7.x/{style}/svg?seed={username}"

def main():
    # Initialize session state
    init_session_state()
    
    # Set search state at the very start
    if st.session_state.get('start_new_search'):
        st.session_state.is_searching = True
    
    # Check authentication
    if not st.session_state.get('authenticated'):
        if check_auth():
            st.rerun()
        else:
            if st.session_state.get('show_signup', False):
                show_signup_page()
            else:
                show_login_page()
            return
    
    # User is authenticated, show main app
    setup_page_config()
    add_sidebar_features()  # This will now see the updated is_searching state
    
    # Get database instance
    db = DatabaseManager()
    user_id = st.session_state.user['user_id']
    
    # Create search interface
    search_query, sort_by, rating_filter = create_search_section()
    
    # Handle new search request
    if st.session_state.get('start_new_search'):
        st.session_state.is_searching = True  # Set this at the very start
        try:
            # Show search progress
            st.warning("⚠️ Please do not refresh the page while search is in progress.", icon="⚠️")
            status = st.status("🔍 Searching videos...", expanded=True)
            
            # Perform search
            videos = search_videos(
                st.session_state.new_search_query,
                progress_callback=lambda msg: status.update(
                    label=f"🔍 {msg}" if msg else "Processing...",
                    expanded=True
                )
            )
            
            if videos:
                # Save complete state to database
                db.save_search_state(user_id, {
                    'query': st.session_state.new_search_query,
                    'results': videos,
                    'last_search_query': st.session_state.new_search_query,
                    'current_sort': st.session_state.current_sort,
                    'rating_filter': st.session_state.rating_filter,
                    'search_history': st.session_state.search_history
                })
                
                # Update session state
                st.session_state.update({
                    'current_videos': videos,
                    'last_search_query': st.session_state.new_search_query,
                    'last_search_results': videos,
                    'start_new_search': False,
                    'new_search_query': None
                })
                
                if st.session_state.new_search_query not in st.session_state.search_history:
                    st.session_state.search_history.append(st.session_state.new_search_query)
                
                status.update(label="✅ Search completed!", state="complete")
                st.session_state.is_searching = False  # Reset after success
                st.rerun()
            else:
                st.session_state.is_searching = False  # Reset after no results
                status.update(label="❌ No results found", state="error")
        
        except Exception as e:
            st.error(f"Search failed: {str(e)}")
            status.update(label="❌ Search interrupted", state="error")
        
        finally:
            st.session_state.is_searching = False
            st.session_state.start_new_search = False
    
    # Always try to show results
    if st.session_state.get('current_videos'):
        display_video_grid(st.session_state.current_videos, rating_filter)
    # If no current results but we have a last query, try to restore from database
    elif st.session_state.get('last_search_query'):
        saved_results = db.get_search_results(user_id, st.session_state.last_search_query)
        if saved_results:
            st.session_state.current_videos = saved_results
            display_video_grid(saved_results, rating_filter)

if __name__ == "__main__":
    # Initialize the database when the app starts
    init_db()
    main() 