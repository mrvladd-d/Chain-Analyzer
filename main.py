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
    .search-box {
        margin-bottom: 10px;
        padding: 10px;
        border-radius: 5px;
        background-color: rgba(0,0,0,0.05);
    }
    .metrics-container {
        padding: 10px;
        margin-bottom: 15px;
        border-radius: 5px;
        background-color: rgba(0,0,0,0.02);
    }
    .workflow-section {
        margin-top: 20px;
        padding: 15px;
        border-radius: 8px;
        background-color: rgba(0,0,0,0.02);
    }
    .dark-mode .detail-container {
        background-color: #2d2d2d;
    }
    .dark-mode .search-box {
        background-color: rgba(255,255,255,0.05);
    }
    .dark-mode .metrics-container, .dark-mode .workflow-section {
        background-color: rgba(255,255,255,0.02);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def get_document_list(doc_dir=DOCUMENT_DIR):
    md_files = glob.glob(os.path.join(doc_dir, "*.md"))
    return {os.path.basename(f).replace(".md", ""): f for f in md_files}

@st.cache_data
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
    
    search_query = st.text_input("Search within document pages:", key=f"page_search_{doc_name}")
    
    num_pages = len(pages_dict)
    cols_per_row = 15
    
    st.write("Click on a page number to view its content:")
    st.write("- 🟢 : Pages used in the final answer")
    st.write("- 🔵 : Pages analyzed but not in final answer")
    st.write("- Unmarked: Pages not analyzed")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        jump_page = st.number_input("Jump to page:", min_value=1, max_value=max(pages_dict.keys()), step=1)
    with col2:
        if st.button("Go to page", key=f"jump_{doc_name}"):
            st.session_state.selected_page = {
                'doc': doc_name,
                'num': jump_page,
                'content': pages_dict.get(jump_page, "Page not found")
            }
    
    filtered_pages = list(sorted(pages_dict.keys()))
    if search_query:
        filtered_pages = [
            page_num for page_num in filtered_pages 
            if search_query.lower() in pages_dict[page_num].lower()
        ]
        if filtered_pages:
            st.success(f"Found {len(filtered_pages)} pages containing '{search_query}'")
        else:
            st.warning(f"No pages found containing '{search_query}'")
    
    for i in range(0, len(filtered_pages), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            page_idx = i + j
            if page_idx < len(filtered_pages):
                page_num = filtered_pages[page_idx]
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
  
            prev_page = selected['num'] - 1
            next_page = selected['num'] + 1
            col1, col2, col3 = st.columns([1, 6, 1])
            with col1:
                if prev_page in pages_dict:
                    if st.button("◀ Previous", key=f"prev_{doc_name}_{selected['num']}"):
                        st.session_state.selected_page = {
                            'doc': doc_name,
                            'num': prev_page,
                            'content': pages_dict[prev_page]
                        }
                        st.rerun()
            with col3:
                if next_page in pages_dict:
                    if st.button("Next ▶", key=f"next_{doc_name}_{selected['num']}"):
                        st.session_state.selected_page = {
                            'doc': doc_name,
                            'num': next_page,
                            'content': pages_dict[next_page]
                        }
                        st.rerun()
            
            with st.container():
                content = selected['content']
                if search_query:
                    content = content.replace(
                        search_query, 
                        f"<mark>{search_query}</mark>"
                    )
                st.markdown(content, unsafe_allow_html=True)

@st.cache_data
def process_file(file_content, max_items=None, skip_xml=True):
    data = []
    line_counter = 0
    in_tag = False
    json_str = ""
    bracket_count = 0
    
    for line in file_content:
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

@st.cache_data
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
    response_type = step.get('response_type', 'unknown')
    
    colors = {
        'question_classifier': '#f9d5e5',
        'company_identifier': '#eeeeee',
        'financial_data': '#e3f2fd',
        'corporate_actions': '#e8f5e9',
        'business_operations': '#fff8e1',
        'answer': '#fff9c4',
    }
    
    color = colors.get(response_type, '#f5f5f5')
    
    with st.expander(f"Step {index + 1}: {get_step_name(step)}", expanded=False):
        st.markdown(f"<div style='background-color: {color}; padding: 5px; border-radius: 5px;'>Step type: {response_type}</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if 'company_name' in step and step['company_name']:
                st.info(f"Company: {step['company_name']}")
            if 'page_num' in step and step['page_num'] is not None:
                st.info(f"Page: {step['page_num']}")
        
        with col2:
            if 'timestamp' in step:
                st.info(f"Timestamp: {step['timestamp']}")
            if 'start_time' in step and 'end_time' in step:
                duration = step['end_time'] - step['start_time']
                st.info(f"Duration: {duration:.2f}s")
        
        prompt_tab, response_tab, raw_tab = st.tabs(["User Prompt", "Response", "Raw JSON"])
        
        with prompt_tab:
            if 'user_prompt' in step:
                st.markdown(f"<div class='user-prompt'>{step['user_prompt']}</div>", unsafe_allow_html=True)
            else:
                st.write("No user prompt available")
        
        with response_tab:
            if 'response' in step and 'choices' in step['response'] and len(step['response']['choices']) > 0:
                content = step['response']['choices'][0].get('message', {}).get('content', 'No content')
                
                try:
                    parsed = json.loads(content)
                    st.code(json.dumps(parsed, indent=2), language="json")
                except:
                    st.markdown(f"<div class='response-content'>{content}</div>", unsafe_allow_html=True)
            else:
                st.write("No response available")
        
        with raw_tab:
            st.code(json.dumps(step, indent=2), language="json")

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
            min-width: 220px;
            text-align: center;
            position: relative;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .step:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
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
        .metadata {
            font-size: 0.8em;
            color: #555;
            margin-top: 5px;
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
            label = f"Financial Data"
        elif response_type == 'corporate_actions':
            class_name = 'corporate-actions'
            label = f"Corporate Actions"
        elif response_type == 'business_operations':
            class_name = 'business-operations'
            label = f"Business Operations"
        elif response_type == 'answer':
            class_name = 'answer'
            label = "Final Answer"
        else:
            class_name = 'other'
            label = response_type.replace('_', ' ').title()
        
        metadata = ""
        if company_name:
            metadata += f"<div class='metadata'>{company_name}</div>"
        if page_num is not None:
            metadata += f"<div class='metadata'>Page {page_num}</div>"
        
        html += f'<div class="step {class_name}">{label}{metadata}</div>\n'
    
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
    
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    
    st.title("🔍 LLM Chain Analysis Tool")
    
    st.write("""
    This tool helps you analyze the workflow of a question-answering service from JSONL debug files.
    Upload your file to see how questions are processed through various steps.
    """)
    
    st.sidebar.header("⚙️ Settings")
    
    dark_mode = st.sidebar.checkbox("Dark Mode", value=st.session_state.dark_mode)
    if dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode
        if dark_mode:
            st.markdown("<style>body { color: white; background-color: #121212; }</style>", unsafe_allow_html=True)
            st.markdown('<div class="dark-mode">', unsafe_allow_html=True)
        else:
            st.markdown("<style>body { color: black; background-color: white; }</style>", unsafe_allow_html=True)
    
    with st.sidebar.expander("Document Settings", expanded=False):
        doc_dir = st.text_input(
            "Document Directory", 
            value=DOCUMENT_DIR,
            help="Directory containing markdown files of documents"
        )
        
        if st.button("Refresh Document List"):
            st.cache_data.clear()
            st.success("Document list refreshed!")
    
    uploaded_file = st.file_uploader("Upload JSONL file", type=["jsonl", "json", "txt"])
    
    if uploaded_file is not None:
        st.sidebar.header("🔄 Processing Options")
        
        with st.sidebar.expander("File Processing Options", expanded=True):
            skip_xml = st.checkbox("Skip XML-like tags", value=True)
            limit_items = st.checkbox("Limit number of items", value=False)
            
            max_items = None
            if limit_items:
                max_items = st.number_input("Maximum items to process", min_value=10, value=1000, step=100)
        
        progress_bar = st.progress(0)
        
        with st.spinner("Processing file..."):
            file_content = uploaded_file.getvalue()
            uploaded_file.seek(0)
            
            for i in range(10):
                progress_bar.progress((i + 1) * 10)
                time.sleep(0.05)
            
            data, line_count = process_file(uploaded_file, max_items, skip_xml)
            progress_bar.progress(100)
        
        if data:
            st.success(f"Successfully processed {len(data)} items from {line_count} lines")
            
            questions = extract_questions(data)
            
            st.subheader("📊 Questions Analyzed")
            if not questions:
                st.warning("No questions found in the data")
                return
            
            with st.container():
                st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Items", len(data))
                col2.metric("Questions Found", len(questions))
                col3.metric("Total Question Steps", sum(len(steps) for steps in questions.values()))
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="search-box">', unsafe_allow_html=True)
            search_term = st.text_input("Search questions:", placeholder="Type to filter questions...")
            st.markdown('</div>', unsafe_allow_html=True)
            
            filtered_questions = question_list = list(questions.keys())
            if search_term:
                filtered_questions = [q for q in question_list if search_term.lower() in q.lower()]
                if filtered_questions:
                    st.success(f"Found {len(filtered_questions)} matching questions")
                else:
                    st.warning(f"No questions found containing '{search_term}'")
                    filtered_questions = question_list
            
            selected_question = st.selectbox(
                "Select a question to analyze:", 
                filtered_questions,
                format_func=lambda x: f"{x[:80]}..." if len(x) > 80 else x
            )
            
            if selected_question:
                steps = questions[selected_question]
                st.markdown(f"## Analysis for: {selected_question}")
                st.markdown(f"**Number of steps:** {len(steps)}")
                
                response_types = pd.Series([step.get('response_type') for step in steps if 'response_type' in step]).value_counts()
                
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "Step Details", 
                    "Workflow Visualization", 
                    "Document Pages", 
                    "Statistics",
                    "Raw Data"
                ])
                
                with tab1:
                    step_types = list(set([step.get('response_type') for step in steps if 'response_type' in step]))
                    selected_types = st.multiselect(
                        "Filter by step type:",
                        options=step_types,
                        default=step_types,
                        format_func=lambda x: x.replace('_', ' ').title()
                    )
                    
                    filtered_steps = steps
                    if selected_types and len(selected_types) < len(step_types):
                        filtered_steps = [step for step in steps if step.get('response_type') in selected_types]
                        st.info(f"Showing {len(filtered_steps)} of {len(steps)} steps")
                    
                    expand_all = st.checkbox("Expand all steps", value=False)
                    
                    for i, step in enumerate(filtered_steps):
                        display_step(step, i)
                
                with tab2:
                    with st.container():
                        st.markdown('<div class="workflow-section">', unsafe_allow_html=True)
                        st.subheader("Workflow Visualization")
                        
                        data_uri = create_workflow_image(steps)
                        height = min(100 + (80 * len(steps)), 600)
                        st.markdown(f'<iframe src="{data_uri}" width="100%" height="{height}" frameBorder="0"></iframe>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
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
                    st.subheader("Step Type Distribution")
                    st.bar_chart(response_types)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Step Timing")
                        has_timing = any(['start_time' in step and 'end_time' in step for step in steps])
                        
                        if has_timing:
                            timing_data = {}
                            for step in steps:
                                if 'start_time' in step and 'end_time' in step:
                                    response_type = step.get('response_type', 'unknown')
                                    duration = step['end_time'] - step['start_time']
                                    if response_type not in timing_data:
                                        timing_data[response_type] = []
                                    timing_data[response_type].append(duration)
                            
                            avg_durations = {k: sum(v)/len(v) for k, v in timing_data.items()}
                            df = pd.DataFrame({'Average Duration (s)': avg_durations})
                            st.bar_chart(df)
                        else:
                            st.info("No timing data available in this trace")
                    
                    with col2:
                        st.subheader("Document Pages Usage")
                        if analyzed_pages:
                            st.write(f"Total pages analyzed: {len(analyzed_pages)}")
                            st.write(f"Pages used in answer: {len(answer_pages)}")
                            
                            if answer_pages:
                                usage_ratio = len(answer_pages) / len(analyzed_pages) * 100
                                st.metric("Page Usage Efficiency", f"{usage_ratio:.1f}%")
                
                with tab5:
                    st.subheader("Raw Data")
                    
                    download_options = st.radio(
                        "Download format:",
                        ["JSON", "CSV (if possible)"]
                    )
                    
                    if download_options == "JSON":
                        if st.button("Download JSON"):
                            json_str = json.dumps(steps, indent=2)
                            st.download_button(
                                "Download JSON file",
                                json_str,
                                file_name=f"{selected_question[:50].replace('?', '')}.json",
                                mime="application/json"
                            )
                    else:
                        try:
                            flat_data = []
                            for step in steps:
                                flat_step = {
                                    'response_type': step.get('response_type', ''),
                                    'company_name': step.get('company_name', ''),
                                    'page_num': step.get('page_num', ''),
                                }
                                flat_data.append(flat_step)
                            
                            df = pd.DataFrame(flat_data)
                            csv = df.to_csv(index=False)
                            
                            st.download_button(
                                "Download CSV file",
                                csv,
                                file_name=f"{selected_question[:50].replace('?', '')}.csv",
                                mime="text/csv"
                            )
                        except Exception as e:
                            st.error(f"Could not convert to CSV: {e}")
                            st.info("Try downloading as JSON instead")
                    
                    with st.expander("View Raw JSON"):
                        st.code(json.dumps(steps, indent=2), language="json")
        else:
            st.error("No valid JSON objects found in the file")

if __name__ == "__main__":
    main()
    
 