import streamlit as st
from werkzeug.security import check_password_hash
from database import DatabaseManager
import json
import base64

def encode_auth_data(data):
    """Encode auth data to base64 string"""
    return base64.b64encode(json.dumps(data).encode()).decode()

def decode_auth_data(encoded_data):
    """Decode auth data from base64 string"""
    try:
        return json.loads(base64.b64decode(encoded_data).decode())
    except:
        return None

def show_login_page():
    """Display the login page"""
    st.title("Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Login"):
                db = DatabaseManager()
                user = db.authenticate_user(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        with col2:
            if st.form_submit_button("Sign Up"):
                st.session_state.show_signup = True
                st.rerun()

def show_signup_page():
    """Display the signup page"""
    st.title("Sign Up")
    
    with st.form("signup_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Create Account"):
                if password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    db = DatabaseManager()
                    if db.create_user(username, password, None):
                        st.success("Account created! Please login.")
                        st.session_state.show_signup = False
                        st.rerun()
                    else:
                        st.error("Username already exists")
        
        with col2:
            if st.form_submit_button("Back to Login"):
                st.session_state.show_signup = False
                st.rerun()

def check_auth():
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)

def logout():
    """Log out the user"""
    for key in ['authenticated', 'user', 'show_signup']:
        if key in st.session_state:
            del st.session_state[key]

def store_auth_cookie():
    """Store authentication data in browser localStorage"""
    st.markdown("""
        <script>
            const auth = {
                'username': '%s',
                'password': '%s'
            };
            localStorage.setItem('auth_data', JSON.stringify(auth));
        </script>
    """ % (st.session_state.username, st.session_state.password), unsafe_allow_html=True) 