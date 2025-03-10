# Chain Analyzer

A Streamlit application for visualizing and analyzing the processing workflow of Large Language Model chains through JSONL debug files.

## Features

- **JSONL Processing** : Efficiently parse and process JSONL debug files containing LLM chain data
- **Question Extraction** : Automatically identify and categorize questions processed by the LLM
- **Workflow Visualization** : View a graphical representation of the entire processing chain
- **Step-by-Step Analysis** : Examine each stage of the workflow, including:
- Question classification
- Company identification
- Financial data analysis
- Corporate actions analysis
- Business operations analysis
- Final answer generation
- **Document Page Viewer** : See which document pages were analyzed and which were used in the final response
- **Raw Data Access** : Download the raw JSON data for further analysis

## Configuration

The application can be configured by modifying the following variables:

- `DOCUMENT_DIR`: Path to the directory containing markdown files of documents referenced in the analysis

## Document Directory Configuration

Before running the application, you must configure the path to your document directory:

1. Open `main.py` in a text editor
2. Locate the `DOCUMENT_DIR` variable at the top of the file
3. Replace it with the path to your markdown files folder using one of these formats:
   <pre><div class="relative flex flex-col rounded-lg"><div class="text-text-300 absolute pl-3 pt-2.5 text-xs">python</div><div class="pointer-events-none sticky my-0.5 ml-0.5 flex items-center justify-end px-1.5 py-1 mix-blend-luminosity top-0"><div class="from-bg-300/90 to-bg-300/70 pointer-events-auto rounded-md bg-gradient-to-b p-0.5 backdrop-blur-md"><button class="flex flex-row items-center gap-1 rounded-md p-1 py-0.5 text-xs transition-opacity delay-100 text-text-300 hover:bg-bg-200 opacity-60 hover:opacity-100" data-state="closed"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 256 256" class="text-text-500 mr-px -translate-y-[0.5px]"><path d="M200,32H163.74a47.92,47.92,0,0,0-71.48,0H56A16,16,0,0,0,40,48V216a16,16,0,0,0,16,16H200a16,16,0,0,0,16-16V48A16,16,0,0,0,200,32Zm-72,0a32,32,0,0,1,32,32H96A32,32,0,0,1,128,32Zm72,184H56V48H82.75A47.93,47.93,0,0,0,80,64v8a8,8,0,0,0,8,8h80a8,8,0,0,0,8-8V64a47.93,47.93,0,0,0-2.75-16H200Z"></path></svg><span class="text-text-200 pr-0.5">Copy</span></button></div></div><div><div class="prismjs code-block__code !my-0 !rounded-lg !text-sm !leading-relaxed"><code class="language-python"><span class=""><span class="token comment"># Option 1: Use raw string (recommended for Windows paths)</span><span class="">
   </span></span><span class=""><span class="">DOCUMENT_DIR </span><span class="token operator">=</span><span class=""></span><span class="token string">r"C:\Path\To\Your\Markdown\Files"</span><span class="">
   </span></span><span class="">
   </span><span class=""><span class=""></span><span class="token comment"># Option 2: Use double backslashes</span><span class="">
   </span></span><span class=""><span class="">DOCUMENT_DIR </span><span class="token operator">=</span><span class=""></span><span class="token string">"C:\\Path\\To\\Your\\Markdown\\Files"</span><span class="">
   </span></span><span class="">
   </span><span class=""><span class=""></span><span class="token comment"># Option 3: Use forward slashes (works on all operating systems)</span><span class="">
   </span></span><span class=""><span class="">DOCUMENT_DIR </span><span class="token operator">=</span><span class=""></span><span class="token string">"C:/Path/To/Your/Markdown/Files"</span></span></code></div></div></div></pre>

**Important Notes:**

- The directory should contain unpacked markdown (.md) files
- Each markdown file should contain document content with pages formatted as "Page X" headers
- The filename (without .md extension) should match the company name referenced in the JSONL file
- If you encounter a "unicodeescape" error, make sure you're using one of the path formats above

You can also change the document directory through the application's sidebar after launching.
