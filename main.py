import streamlit as st
import json
import pandas as pd
import re
from collections import defaultdict
import time
import io
import base64
import os
import glob
from pathlib import Path

DOCUMENT_DIR = r"\Chain-Analyzer\reports"

st.set_page_config(
    page_title="LLM Chain Analysis Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .step-container {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 15px;
    }
    .response-content {
        border-left: 3px solid #0068c9;
        padding-left: 10px;
        font-size: 0.9em;
        overflow-x: auto;
    }
    .user-prompt {
        border-left: 3px solid #ff4b4b;
        padding-left: 10px;
    }
    .step-header {
        font-weight: bold;
        margin-bottom: 10px;
    }
    .expander-header {
        font-size: 1.1em;
    }
    .detail-container {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        margin-top: 5px;
    }
    .page-icon {
        display: inline-block;
        width: 40px;
        height: 40px;
        line-height: 40px;
        text-align: center;
        border-radius: 5px;
        margin: 3px;
        cursor: pointer;
    }
    .page-icon-container {
        text-align: center;
    }
    .stButton button[data-baseweb="button"] {
        width: 100%;
        min-width: 30px;
        padding: 2px;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

def get_document_list(doc_dir=DOCUMENT_DIR):
    md_files = glob.glob(os.path.join(doc_dir, "*.md"))
    return {os.path.basename(f).replace(".md", ""): f for f in md_files}

def read_markdown_document(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        page_matches = list(re.finditer(r'(?:^|\n)(?:# )?Page (\d+)', content, re.IGNORECASE))
        
        if page_matches:
            pages = {}
            for i, match in enumerate(page_matches):
                start_pos = match.end()
                end_pos = page_matches[i+1].start() if i < len(page_matches)-1 else len(content)
                page_content = content[start_pos:end_pos].strip()
                page_num = int(match.group(1))
                pages[page_num] = page_content
            return pages
        
        return {1: content}
            
    except Exception as e:
        st.error(f"Error reading document: {e}")
        return {}

def display_document_pages(doc_name, pages_dict, analyzed_pages, answer_pages):
    st.subheader(f"Document Pages for {doc_name}")
    
    num_pages = len(pages_dict)
    cols_per_row = 15
    
    st.write("Click on a page number to view its content:")
    st.write("- 🟢 : Pages used in the final answer")
    st.write("- 🔵 : Pages analyzed but not in final answer")
    st.write("- Unmarked: Pages not analyzed")
    
    for i in range(0, num_pages, cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            page_idx = i + j
            if page_idx < num_pages:
                page_num = list(sorted(pages_dict.keys()))[page_idx]
                with cols[j]:
                    if page_num in answer_pages:
                        label = f"🟢 {page_num}"
                        btn_type = "primary"
                    elif page_num in analyzed_pages:
                        label = f"🔵 {page_num}"
                        btn_type = "primary"
                    else:
                        label = f"{page_num}"
                        btn_type = "secondary"
                    
                    if st.button(label, key=f"page_{doc_name}_{page_num}", type=btn_type):
                        st.session_state.selected_page = {
                            'doc': doc_name,
                            'num': page_num,
                            'content': pages_dict[page_num]
                        }
    
    if 'selected_page' in st.session_state and st.session_state.selected_page:
        selected = st.session_state.selected_page
        if selected['doc'] == doc_name:
            st.markdown("---")
            st.subheader(f"Page {selected['num']} Content")
            with st.container():
                st.markdown(selected['content'])

def process_file(file, max_items=None, skip_xml=True):
    data = []
    line_counter = 0
    in_tag = False
    json_str = ""
    bracket_count = 0
    
    for line in file:
        line_counter += 1
        
        try:
            line_str = line.decode('utf-8')
        except UnicodeDecodeError:
            try:
                line_str = line.decode('latin-1')
            except:
                continue
        
        if skip_xml:
            if "<" in line_str and ">" in line_str:
                if any(tag in line_str for tag in ["<userStyle>", "<documents>", "<document"]):
                    in_tag = True
                    continue
            
            if "</" in line_str and ">" in line_str:
                if any(tag in line_str for tag in ["</userStyle>", "</documents>", "</document>"]):
                    in_tag = False
                    continue
            
            if in_tag:
                continue
        
        line_str = line_str.strip()
        if not line_str:
            continue
        
        if line_str.startswith('{') and line_str.endswith('}'):
            try:
                obj = json.loads(line_str)
                data.append(obj)
                
                if max_items and len(data) >= max_items:
                    break
                    
                continue
            except:
                pass
        
        json_str += line_str
        bracket_count += line_str.count('{') - line_str.count('}')
        
        if bracket_count == 0 and json_str:
            try:
                obj = json.loads(json_str)
                data.append(obj)
                json_str = ""
                
                if max_items and len(data) >= max_items:
                    break
            except:
                pass
    
    return data, line_counter

def extract_questions(data):
    questions = defaultdict(list)
    current_question = None
    
    for item in data:
        if 'response_type' not in item:
            continue
            
        if item['response_type'] == 'question_classifier':
            if 'user_prompt' in item:
                match = re.search(r'Question:\s*(.*?)(?=\s*\n\s*Provide detailed reasoning|$)', item['user_prompt'], re.DOTALL)
                if match:
                    current_question = match.group(1).strip()
                else:
                    match = re.search(r'Analyze the following question.*?:\s*\n\s*Question:\s*(.*?)(?=\s*\n|$)', item['user_prompt'], re.DOTALL)
                    if match:
                        current_question = match.group(1).strip()
                    else:
                        current_question = f"Unknown Question #{len(questions) + 1}"
        
        if current_question:
            questions[current_question].append(item)
        else:
            questions["Unclassified Steps"].append(item)
    
    if "Unclassified Steps" in questions and not questions["Unclassified Steps"]:
        questions.pop("Unclassified Steps")
        
    return questions

def get_step_name(step):
    response_type = step.get('response_type', 'unknown')
    company_name = step.get('company_name', None)
    page_num = step.get('page_num', None)
    
    if response_type == 'question_classifier':
        return "Question Classification"
    elif response_type == 'company_identifier':
        return "Company Identification"
    elif response_type == 'financial_data' and company_name and page_num:
        return f"Financial Data - {company_name} (Page {page_num})"
    elif response_type == 'corporate_actions' and company_name and page_num:
        return f"Corporate Actions - {company_name} (Page {page_num})"
    elif response_type == 'answer':
        return f"Final Answer - {company_name if company_name else ''}"
    else:
        return f"{response_type.replace('_', ' ').title()}"

def display_step(step, index):
    with st.expander(f"Step {index + 1}: {get_step_name(step)}"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### User Prompt")
            if 'user_prompt' in step:
                st.markdown(f"<div class='user-prompt'>{step['user_prompt']}</div>", unsafe_allow_html=True)
            else:
                st.write("No user prompt available")
        
        with col2:
            st.markdown("#### Response")
            if 'response' in step and 'choices' in step['response'] and len(step['response']['choices']) > 0:
                content = step['response']['choices'][0].get('message', {}).get('content', 'No content')
                
                try:
                    parsed = json.loads(content)
                    st.json(parsed)
                except:
                    st.markdown(f"<div class='response-content'>{content}</div>", unsafe_allow_html=True)
            else:
                st.write("No response available")

def create_workflow_image(steps):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        .container {
            font-family: Arial, sans-serif;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        .workflow {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .step {
            margin: 10px;
            padding: 15px;
            border-radius: 8px;
            min-width: 200px;
            text-align: center;
            position: relative;
        }
        .step:not(:last-child):after {
            content: "";
            position: absolute;
            bottom: -20px;
            left: 50%;
            transform: translateX(-50%);
            width: 0;
            height: 0;
            border-left: 10px solid transparent;
            border-right: 10px solid transparent;
            border-top: 10px solid #333;
        }
        .question-classifier {
            background-color: #f9d5e5;
            border: 1px solid #333;
        }
        .company-identifier {
            background-color: #eeeeee;
            border: 1px solid #333;
        }
        .financial-data {
            background-color: #e3f2fd;
            border: 1px solid #333;
        }
        .corporate-actions {
            background-color: #e8f5e9;
            border: 1px solid #333;
        }
        .answer {
            background-color: #fff9c4;
            border: 1px solid #333;
        }
        .business-operations {
            background-color: #fff8e1;
            border: 1px solid #333;
        }
        .other {
            background-color: #f5f5f5;
            border: 1px solid #333;
        }
    </style>
    </head>
    <body>
    <div class="container">
        <div class="workflow">
    """
    
    for step in steps:
        response_type = step.get('response_type', 'unknown')
        company_name = step.get('company_name', None)
        page_num = step.get('page_num', None)
        
        if response_type == 'question_classifier':
            class_name = 'question-classifier'
            label = "Question Classification"
        elif response_type == 'company_identifier':
            class_name = 'company-identifier'
            label = "Company Identification"
        elif response_type == 'financial_data':
            class_name = 'financial-data'
            label = f"Financial Data<br>{company_name or ''} (Page {page_num or 'N/A'})"
        elif response_type == 'corporate_actions':
            class_name = 'corporate-actions'
            label = f"Corporate Actions<br>{company_name or ''} (Page {page_num or 'N/A'})"
        elif response_type == 'business_operations':
            class_name = 'business-operations'
            label = f"Business Operations<br>{company_name or ''} (Page {page_num or 'N/A'})"
        elif response_type == 'answer':
            class_name = 'answer'
            label = "Final Answer"
        else:
            class_name = 'other'
            label = response_type.replace('_', ' ').title()
        
        html += f'<div class="step {class_name}">{label}</div>\n'
    
    html += """
        </div>
    </div>
    </body>
    </html>
    """
    
    html_bytes = html.encode('utf-8')
    encoded = base64.b64encode(html_bytes).decode('utf-8')
    data_uri = f"data:text/html;base64,{encoded}"
    
    return data_uri

def main():
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = None
    
    st.title("🔍 Simplified LLM Chain Analysis Tool")
    
    st.write("""
    This tool helps you analyze the workflow of a question-answering service from JSONL debug files.
    Upload your file to see how questions are processed through various steps.
    """)
    
    st.sidebar.header("Settings")
    
    doc_dir = st.sidebar.text_input(
        "Document Directory", 
        value=DOCUMENT_DIR,
        help="Directory containing markdown files of documents"
    )
    
    uploaded_file = st.file_uploader("Upload JSONL file", type=["jsonl", "json", "txt"])
    
    if uploaded_file is not None:
        st.sidebar.header("Processing Options")
        skip_xml = st.sidebar.checkbox("Skip XML-like tags", value=True)
        limit_items = st.sidebar.checkbox("Limit number of items", value=False)
        
        max_items = None
        if limit_items:
            max_items = st.sidebar.number_input("Maximum items to process", min_value=10, value=1000, step=100)
        
        with st.spinner("Processing file..."):
            data, line_count = process_file(uploaded_file, max_items, skip_xml)
        
        if data:
            st.success(f"Successfully processed {len(data)} items from {line_count} lines")
            
            questions = extract_questions(data)
            
            st.subheader("Questions Analyzed")
            if not questions:
                st.warning("No questions found in the data")
                return
                
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Items", len(data))
            col2.metric("Questions Found", len(questions))
            col3.metric("Total Question Steps", sum(len(steps) for steps in questions.values()))
            
            question_list = list(questions.keys())
            selected_question = st.selectbox("Select a question to analyze:", question_list)
            
            if selected_question:
                steps = questions[selected_question]
                st.markdown(f"## Analysis for: {selected_question}")
                st.markdown(f"**Number of steps:** {len(steps)}")
                
                response_types = pd.Series([step.get('response_type') for step in steps if 'response_type' in step]).value_counts()
                st.subheader("Step Types")
                st.bar_chart(response_types)
                
                tab1, tab2, tab3, tab4 = st.tabs(["Step Details", "Workflow Visualization", "Document Pages", "Raw Data"])
                
                with tab1:
                    for i, step in enumerate(steps):
                        display_step(step, i)
                
                with tab2:
                    st.subheader("Workflow Visualization")
                    
                    data_uri = create_workflow_image(steps)
                    height = min(150 * len(steps), 800)
                    st.markdown(f'<iframe src="{data_uri}" width="100%" height="{height}" frameBorder="0"></iframe>', unsafe_allow_html=True)
                    
                    st.subheader("Company Analysis")
                    companies = set([step.get('company_name') for step in steps if step.get('company_name')])
                    
                    if companies:
                        for company in companies:
                            company_steps = [step for step in steps if step.get('company_name') == company]
                            st.write(f"**{company}**: {len(company_steps)} steps")
                            
                            pages = [step.get('page_num') for step in company_steps if step.get('page_num') is not None]
                            if pages:
                                st.write(f"Pages analyzed: {', '.join([str(p) for p in sorted(pages)])}")
                
                with tab3:
                    company_name = None
                    analyzed_pages = set()
                    answer_pages = set()
                    
                    for step in steps:
                        if 'company_name' in step and step['company_name']:
                            company_name = step['company_name']
                        
                        if 'page_num' in step and step['page_num'] is not None:
                            analyzed_pages.add(step['page_num'])
                    
                    for step in steps:
                        if step.get('response_type') == 'answer' and 'response' in step:
                            try:
                                sources = step['response']['choices'][0]['message']['parsed'].get('sources', [])
                                for source in sources:
                                    if 'page_number' in source:
                                        page_num = source['page_number']
                                        answer_pages.add(page_num)
                            except (KeyError, IndexError, AttributeError):
                                pass
                    
                    if company_name:
                        documents = get_document_list(doc_dir)
                        
                        doc_path = None
                        doc_name = None
                        
                        if company_name in documents:
                            doc_path = documents[company_name]
                            doc_name = company_name
                        else:
                            for name, path in documents.items():
                                if company_name.lower() in name.lower():
                                    doc_path = path
                                    doc_name = name
                                    break
                        
                        if not doc_path:
                            st.warning(f"No document found for {company_name}. Please select one manually:")
                            doc_options = list(documents.keys())
                            if doc_options:
                                doc_name = st.selectbox(
                                    "Select a document:", 
                                    options=doc_options
                                )
                                if doc_name:
                                    doc_path = documents[doc_name]
                            else:
                                st.error(f"No documents found in directory: {doc_dir}")
                        
                        if doc_path:
                            pages_dict = read_markdown_document(doc_path)
                            
                            if pages_dict:
                                display_document_pages(doc_name, pages_dict, analyzed_pages, answer_pages)
                            else:
                                st.error(f"No pages found in document: {doc_name}")
                        else:
                            st.error("No document selected")
                    else:
                        st.info("No company identified in the analysis")
                
                with tab4:
                    st.subheader("Raw Data")
                    if st.button("Download JSON"):
                        json_str = json.dumps(steps, indent=2)
                        st.download_button(
                            "Download JSON file",
                            json_str,
                            file_name=f"{selected_question[:50].replace('?', '')}.json",
                            mime="application/json"
                        )
                    
                    with st.expander("View Raw JSON"):
                        st.json(steps)
        else:
            st.error("No valid JSON objects found in the file")

if __name__ == "__main__":
    main()
    
 