import subprocess
import sys

# Ensure NumPy 1.26.4 is installed
try:
    import numpy as np
    if np.__version__ != "1.26.4":
        raise ImportError
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy==1.26.4"])
    import numpy as np  # Reload after installation

import streamlit as st
import nltk
import spacy
import pandas as pd
import base64
import random
import time
import datetime
import io

# Required pdfminer imports
from pdfminer.high_level import extract_text
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage

# Download required nltk data
nltk.download('stopwords')

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

# Resume Parsing
from pyresparser import ResumeParser

# Streamlit UI Components
from streamlit_tags import st_tags
from PIL import Image

# Database Connection
import pymysql

# Course Data Imports
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos

# Data Visualization
import plotly.express as px

# YouTube Downloading (yt-dlp instead of youtube_dl)
import pafy
import yt_dlp as youtube_dl

# Ensure pafy uses yt-dlp as backend
pafy.set_api_key(None)


def fetch_yt_video(link):
    video = pafy.new(link)
    return video.title


def get_table_download_link(df, filename, text):
    """Generates a download link for a Pandas dataframe"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href


def pdf_reader(file):
    """Extract text from PDF file"""
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)

    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)

    text = fake_file_handle.getvalue()
    converter.close()
    fake_file_handle.close()
    return text


def show_pdf(file_path):
    """Display PDF in Streamlit"""
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


def course_recommender(course_list):
    """Recommend courses"""
    st.subheader("**Courses & Certificates🎓 Recommendations**")
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 4)
    random.shuffle(course_list)

    for i, (c_name, c_link) in enumerate(course_list[:no_of_reco]):
        st.markdown(f"({i + 1}) [{c_name}]({c_link})")


# Database Connection
connection = pymysql.connect(host='localhost', user='root', password='')
cursor = connection.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS SRA;")
connection.select_db("sra")

# Create table
table_sql = """CREATE TABLE IF NOT EXISTS user_data (
                ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                Name VARCHAR(100) NOT NULL,
                Email_ID VARCHAR(50) NOT NULL,
                resume_score VARCHAR(8) NOT NULL,
                Timestamp VARCHAR(50) NOT NULL,
                Page_no VARCHAR(5) NOT NULL,
                Predicted_Field VARCHAR(25) NOT NULL,
                User_level VARCHAR(30) NOT NULL,
                Actual_skills VARCHAR(300) NOT NULL,
                Recommended_skills VARCHAR(300) NOT NULL,
                Recommended_courses VARCHAR(600) NOT NULL
              );"""
cursor.execute(table_sql)


def run():
    st.title("Smart Resume Analyser")
    st.sidebar.markdown("# Choose User")
    choice = st.sidebar.selectbox("Choose User Type", ["Normal User", "Admin"])
    img = Image.open('./Logo/SRA_Logo.jpg').resize((250, 250))
    st.image(img)

    if choice == 'Normal User':
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])

        if pdf_file:
            save_image_path = f'./Uploaded_Resumes/{pdf_file.name}'
            with open(save_image_path, "wb") as f:
                f.write(pdf_file.getbuffer())

            show_pdf(save_image_path)

            try:
                resume_data = ResumeParser(save_image_path).get_extracted_data()
                if resume_data:
                    resume_text = pdf_reader(save_image_path)

                    st.header("**Resume Analysis**")
                    st.success(f"Hello {resume_data.get('name', 'Candidate')}")
                    st.subheader("**Your Basic info**")
                    st.text(f"Name: {resume_data.get('name', 'N/A')}")
                    st.text(f"Email: {resume_data.get('email', 'N/A')}")
                    st.text(f"Contact: {resume_data.get('mobile_number', 'N/A')}")
                    st.text(f"Resume pages: {resume_data.get('no_of_pages', 'N/A')}")

                    st.subheader("**Skills Recommendation💡**")
                    keywords = st_tags(label='### Skills you have', value=resume_data.get('skills', []), key='1')

                    recommended_skills = []
                    reco_field = ''
                    for skill in resume_data.get('skills', []):
                        if skill.lower() in ['tensorflow', 'pytorch', 'flask']:
                            reco_field = 'Data Science'
                            st.success("** You are likely looking for Data Science jobs. **")
                            recommended_skills = ['Machine Learning', 'Deep Learning', 'Data Analysis']
                            st_tags(label='### Recommended skills', value=recommended_skills, key='2')
                            course_recommender(ds_course)
                            break

                    st.subheader("**Resume Score📝**")
                    resume_score = sum(20 for section in ['Objective', 'Declaration', 'Hobbies', 'Achievements', 'Projects'] if section in resume_text)
                    st.progress(resume_score / 100)

            except Exception as e:
                st.error(f"Error processing resume: {str(e)}")


if __name__ == '__main__':
    run()
