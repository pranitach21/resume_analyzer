#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# resume_analyzer.py
import streamlit as st
import pandas as pd
import pdfplumber
import docx
import nltk
import io
import random
import hashlib
import requests
import re
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from Courses import (
    ds_course, web_course, android_course, 
    ios_course, uiux_course, resume_videos, interview_videos
)

# Configuration
SERPAPI_KEY = "your_api_key_here"  # Get from https://serpapi.com/
nltk.download('punkt_tab')
nltk.download('stopwords')
nltk.download('punkt')

COURSE_CATEGORIES = {
    'Data Science': {'courses': ds_course, 'keywords': ['data', 'python', 'machine learning']},
    'Web Development': {'courses': web_course, 'keywords': ['web', 'javascript', 'react']},
    'Android Development': {'courses': android_course, 'keywords': ['android', 'kotlin', 'mobile']},
    'iOS Development': {'courses': ios_course, 'keywords': ['ios', 'swift', 'xcode']},
    'UI/UX Design': {'courses': uiux_course, 'keywords': ['ui', 'ux', 'adobe', 'figma']}
}

def extract_text(file):
    try:
        if not file: return None
        if file.name.endswith('.pdf'):
            with pdfplumber.open(io.BytesIO(file.read())) as pdf:
                return "\n".join([page.extract_text() for page in pdf.pages])
        elif file.name.endswith('.docx'):
            doc = docx.Document(io.BytesIO(file.read()))
            return "\n".join([para.text for para in doc.paragraphs])
        return None
    except Exception as e:
        st.error(f"File error: {str(e)}")
        return None

def analyze_resume(jd_text, resume_text):
    if not resume_text: return None
    try:
        stop_words = set(nltk.corpus.stopwords.words('english'))
        vectorizer = TfidfVectorizer()
        similarity_score = 0  # Initialize similarity score
        
        # Extract position and skills using regex
        position_match = re.search(r'(?i)\b(?:Senior|Junior)?\s*(.*?Developer|Data Scientist|UI Designer|Engineer)\b', resume_text)
        skills_match = re.search(r'(?i)Skills:?\s*([\w\s,]+)(?:\n|$)', resume_text)
        
        custom_keywords = []
        position = "Professional"
        if position_match:
            position = position_match.group(1).strip()
            custom_keywords.extend(position.lower().split())
        
        if skills_match:
            skills = skills_match.group(1).replace(',', ' ').split()
            custom_keywords.extend([s.lower() for s in skills if len(s) > 2])

        # Extract TF-IDF keywords and calculate similarity
        documents = []
        if jd_text:
            documents.append(' '.join([w for w in nltk.word_tokenize(jd_text.lower()) 
                                     if w.isalpha() and w not in stop_words]))
        
        documents.append(' '.join([w for w in nltk.word_tokenize(resume_text.lower()) 
                                 if w.isalpha() and w not in stop_words]))
        
        vectors = vectorizer.fit_transform(documents)
        
        # Calculate similarity score if JD exists
        if jd_text:
            similarity_score = round(cosine_similarity(vectors[0], vectors[1])[0][0] * 100, 2)

        tfidf_keywords = list(vectorizer.get_feature_names_out())
        
        # Combine and prioritize keywords
        combined_keywords = list(set(custom_keywords + tfidf_keywords))
        priority_terms = ['developer', 'scientist', 'engineer', 'designer', 'android', 
                         'ios', 'data', 'machine', 'ux', 'ui', 'mobile']
        
        sorted_keywords = sorted(combined_keywords,
                               key=lambda x: (x in priority_terms, x in custom_keywords),
                               reverse=True)[:15]

        return {
            'similarity_score': similarity_score,  # Now included in response
            'position': position,
            'keywords': sorted_keywords,
            'skills': custom_keywords,
            'unique_id': hashlib.sha256(resume_text.encode()).hexdigest()
        }
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        return None
        
def get_linkedin_jobs(position, keywords, upload_date):
    try:
        if not position or not keywords:
            return []
        
        # Clean and format position title
        clean_position = re.sub(r'[^a-zA-Z\s]', '', position).strip().title()
        
        # Calculate exact 7-day window
        end_date = upload_date.strftime("%Y%m%d")
        start_date = (upload_date - timedelta(days=7)).strftime("%Y%m%d")
        
        # Build position-specific query
        params = {
            "engine": "linkedin_jobs",
            "q": f'"{clean_position}"',
            "keywords": " ".join(keywords[:5]),
            "location": "worldwide",
            "sort_by": "date",
            "api_key": SERPAPI_KEY,
            "date_posted": f"{start_date}-{end_date}",
            "chips": f"date_posted_range:{start_date}-{end_date}"
        }

        response = requests.get("https://serpapi.com/search", params=params)
        jobs = response.json().get("jobs", [])[:5]
        
        return [{
            "title": job.get("title"),
            "company": job.get("company"),
            "url": job.get("link"),
            "posted_date": job.get("posted_date"),
        } for job in jobs if job.get("posted_date")]
    except Exception as e:
        st.error(f"Failed to fetch jobs: {str(e)}")
        return []

def show_job_recommendations(position, keywords, upload_date):
    with st.expander("🔍 Searchh Job Openings ", expanded=True):
        if not position or not keywords:
            st.warning("No position or keywords extracted from resume")
            return
            
        jobs = get_linkedin_jobs(position, keywords, upload_date)
        
        if not jobs:
            #st.info("No recent job openings matching your profile")
            st.markdown(
                f"""<a href="https://www.linkedin.com/jobs/search/?keywords={position}" 
                target="_blank" style="color: #0077b5; text-decoration: none;">
                ➤ Search {position} jobs on LinkedIn </a>""",
                unsafe_allow_html=True
            )
            return
        
        for job in jobs:
            try:
                post_date = datetime.strptime(job['posted_date'], "%Y-%m-%d")
                days_old = (upload_date - post_date).days
                
                st.markdown(f"""
                <div style="padding:10px; margin:10px 0; border:1px solid #e0e0e0; border-radius:5px;">
                    <h4 style="margin:0; color:#1a0dab;">{job['title']}</h4>
                    <p style="margin:0.5em 0; color:#666; font-size:0.9em;">
                        {job['company']}
                    </p>
                    <p style="margin:0.5em 0; font-size:0.9em;">
                        <a href="{job['url']}" target="_blank" 
                        style="color:#0077b5; text-decoration:none;">
                            ➤ View on LinkedIn • Posted {days_old} days ago
                        </a>
                    </p>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error showing job: {str(e)}")
                
def hr_dashboard():
    st.title("HR Resume Analyzer")
    uploaded_file = st.file_uploader("Upload Candidate Resume", type=["pdf", "docx"])
    jd_text = st.text_area("Paste Job Description", height=200)
    
    if st.button("Analyze Resume"):
        if not uploaded_file or not jd_text:
            st.error("Please upload resume and enter job description")
            return
            
        resume_text = extract_text(uploaded_file)
        if resume_text:
            analysis = analyze_resume(jd_text, resume_text)
            if analysis:
                st.subheader("Analysis Results")
                
                # Check if similarity_score exists before displaying
                if 'similarity_score' in analysis:
                    st.metric("JD Match Score", f"{analysis['similarity_score']}%")
                else:
                    st.warning("Similarity score not available")
                
                with st.expander("🔍 Key Insights", expanded=True):
                    st.metric("Position Match", analysis.get('position', 'Not detected'))
                    st.write("**Top Keywords:**", ", ".join(analysis.get('keywords', [])[:10]))
                
                with st.expander("📊 Detailed Analysis"):
                    st.write("**All Identified Skills:**", ", ".join(analysis.get('skills', [])))

def user_dashboard():
    st.title("Job Seeker Dashboard")
    uploaded_file = st.file_uploader("Upload Your Resume", type=["pdf", "docx"])
    
    if uploaded_file:
        upload_date = datetime.now()
        resume_text = extract_text(uploaded_file)
        if resume_text:
            analysis = analyze_resume("", resume_text)
            if analysis:
                with st.expander("📊 Resume Analysis", expanded=True):
                    st.markdown(f"**Current Position:** {analysis['position']}")
                    st.write("**Key Skills:**", ", ".join(analysis['skills'][:10]))
                
                show_job_recommendations(analysis['position'], analysis['keywords'], upload_date)
                
                with st.expander("🎓 Recommended Courses", expanded=True):
                    categories_shown = 0
                    for category, data in COURSE_CATEGORIES.items():
                        if set(analysis['keywords']).intersection(data['keywords']):
                            st.markdown(f"**{category}**")
                            for course in random.sample(data['courses'], 3):
                                st.markdown(f"- [{course[0]}]({course[1]})")
                            categories_shown += 1
                    
                    if categories_shown == 0:
                        st.markdown("**General Career Development**")
                        for course in random.sample(web_course + ds_course, 5):
                            st.markdown(f"- [{course[0]}]({course[1]})")
                
                with st.expander("📝 Interview Preparation", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("#### Resume Building")
                        st.video(random.choice(resume_videos))
                    with col2:
                        st.markdown("#### Interview Techniques")
                        st.video(random.choice(interview_videos))

def main():
    st.set_page_config(page_title="Resume Analyzer", layout="wide")
    
    if 'logged_in' not in st.session_state:
        st.session_state.update(logged_in=False, role=None)
    
    if not st.session_state.logged_in:
        st.title("Career Portal Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                try:
                    df = pd.read_excel('users.xlsx')
                    valid_user = not df[(df['Username'] == username) & (df['Password'] == password)].empty
                    
                    if valid_user:
                        if username.startswith("hr_"):
                            st.session_state.update(logged_in=True, role="hr")
                        elif username.startswith("user_"):
                            st.session_state.update(logged_in=True, role="user")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                except FileNotFoundError:
                    st.error("User database not found")
    else:
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.rerun()
        
        if st.session_state.role == "hr":
            hr_dashboard()
        else:
            user_dashboard()

if __name__ == "__main__":
    main()

