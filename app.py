import os
import json
import time
import requests
import base64
import re
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
app = Flask(__name__)

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

STUDENT_SECRET = "secretsecretsecretsecretsecretse"
GITHUB_USER = "24f1002483"

# Configure Groq client
client = Groq(api_key=GROQ_API_KEY)

def sanitize_repo_name(name):
    """Convert task name to valid GitHub repository name"""
    sanitized = re.sub(r'[^\w\-_.]', '-', name)
    sanitized = re.sub(r'-+', '-', sanitized)
    sanitized = sanitized.strip('-')
    if not sanitized:
        sanitized = "auto-generated-repo"
    if not sanitized[0].isalnum():
        sanitized = "repo-" + sanitized
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized.lower()

def create_github_repo(repo_name):
    """Create GitHub repository using GitHub API"""
    try:
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
        }
        
        # Check if repo exists
        check_url = f'https://api.github.com/repos/{GITHUB_USER}/{repo_name}'
        response = requests.get(check_url, headers=headers)
        
        if response.status_code == 200:
            print(f"Repository {repo_name} already exists")
            return True
        
        # Create new repository
        create_url = 'https://api.github.com/user/repos'
        data = {
            'name': repo_name,
            'description': f'Auto-generated repository for {repo_name}',
            'private': False,
            'auto_init': False,
            'has_projects': False,
            'has_wiki': False
        }
        
        response = requests.post(create_url, headers=headers, json=data)
        
        if response.status_code == 201:
            print(f"Repository {repo_name} created successfully")
            return True
        else:
            print(f"Failed to create repository: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Failed to create repository: {e}")
        return False

def create_file_in_repo(repo_name, file_path, content, commit_message, is_binary=False):
    """Create or update file in repository using GitHub API"""
    try:
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
        }
        
        url = f'https://api.github.com/repos/{GITHUB_USER}/{repo_name}/contents/{file_path}'
        
        # Check if file exists to get SHA for update
        response = requests.get(url, headers=headers)
        sha = None
        if response.status_code == 200:
            sha = response.json().get('sha')
        
        # Encode content to base64
        if is_binary:
            # For binary content, it's already bytes
            content_b64 = base64.b64encode(content).decode()
        else:
            # For text content
            content_b64 = base64.b64encode(content.encode()).decode()
        
        data = {
            'message': commit_message,
            'content': content_b64,
            'branch': 'main'
        }
        
        if sha:
            data['sha'] = sha
        
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code in [200, 201]:
            print(f"Successfully created/updated {file_path}")
            return True
        else:
            print(f"Failed to create {file_path}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error creating file {file_path}: {e}")
        return False

def get_latest_commit_sha(repo_name):
    """Get the latest commit SHA using GitHub API"""
    try:
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
        }
        
        url = f'https://api.github.com/repos/{GITHUB_USER}/{repo_name}/commits/main'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()['sha']
        else:
            print(f"Failed to get commit SHA: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting commit SHA: {e}")
        return None

@app.route('/api/task', methods=['POST'])
def handle_request():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # Verify secret
        if data.get('secret') != STUDENT_SECRET:
            return jsonify({"error": "Invalid secret"}), 403
        
        email = data['email']
        task = data['task']
        round_num = data['round']
        nonce = data['nonce']
        brief = data['brief']
        checks = data['checks']
        evaluation_url = data['evaluation_url']
        attachments = data.get('attachments', [])
        
        # Sanitize the repository name
        repo_name = sanitize_repo_name(task)
        print(f"Original task: '{task}' -> Sanitized repo name: '{repo_name}'")
        
        print(f"Starting processing for repo: {repo_name}, round: {round_num}")
        
        try:
            if round_num == 1:
                # Build Phase: Create new repo and generate app
                
                # Use Groq to generate minimal app code
                prompt = f"""
                Generate a complete, single HTML file for a minimal web app based on this brief: {brief}.
                
                Requirements:
                - Single HTML file with embedded CSS and JavaScript
                - Handle URL parameters like ?url=https://.../image.png and display the captcha image
                - Default to using a sample image if no URL is provided
                - Solve the captcha and display the text within 15 seconds (use a simple OCR or mock solver)
                - Include basic styling and error handling
                
                Output ONLY the complete HTML code without any explanations or markdown formatting.
                """
                
                print("Calling Groq API to generate app code...")
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a expert web developer. Always output complete, working HTML files with embedded CSS and JavaScript. Never include explanations or markdown code blocks."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )
                
                app_html = response.choices[0].message.content.strip()
                print("Received response from Groq API")
                
                # Clean up the response
                if app_html.startswith('```html'):
                    app_html = app_html[7:]
                if app_html.startswith('```'):
                    app_html = app_html[3:]
                if app_html.endswith('```'):
                    app_html = app_html[:-3]
                app_html = app_html.strip()
                
                # Create GitHub repository
                print("Creating GitHub repository...")
                if not create_github_repo(repo_name):
                    return jsonify({"error": "Failed to create GitHub repository"}), 500
                
                # Add MIT license
                print("Creating LICENSE file...")
                license_content = """MIT License

Copyright (c) 2023 Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
                
                if not create_file_in_repo(repo_name, 'LICENSE', license_content, "Add MIT license"):
                    return jsonify({"error": "Failed to create LICENSE file"}), 500
                
                # Write README.md
                print("Creating README.md...")
                readme_content = f"""# {repo_name}

## Summary
{brief}

## Setup
Clone the repo and open index.html in a browser.

## Usage
Access the app via GitHub Pages at: https://{GITHUB_USER}.github.io/{repo_name}/

Pass ?url=https://.../image.png to load a captcha image.

## Code Explanation
The app uses HTML/JS to display and solve captchas. It defaults to the sample image.

## License
MIT
"""
                if not create_file_in_repo(repo_name, 'README.md', readme_content, "Add README"):
                    return jsonify({"error": "Failed to create README.md"}), 500
                
                # Write app HTML
                print("Creating index.html...")
                if not create_file_in_repo(repo_name, 'index.html', app_html, "Add web application"):
                    return jsonify({"error": "Failed to create index.html"}), 500
                
                # Handle attachments via GitHub API ONLY - NO FILE SYSTEM
                for att in attachments:
                    if att['url'].startswith('data:image/png;base64,'):
                        filename = att['name']
                        print(f"Creating attachment via GitHub API: {filename}")
                        # Extract base64 data and decode to binary
                        base64_data = att['url'].split(',')[1]
                        binary_data = base64.b64decode(base64_data)
                        # Create image file directly via GitHub API
                        if not create_file_in_repo(repo_name, filename, binary_data, f"Add {filename}", is_binary=True):
                            print(f"Warning: Failed to create {filename} via GitHub API")
                
                print("GitHub Pages should be available automatically for public repositories")
            
            else:
                # Revise Phase: Modify existing repo
                print(f"Round {round_num}: Updating existing repository...")
                
                # Use Groq to generate updated app code based on new brief
                prompt = f"""
                Update the existing web app (HTML, CSS, JS) based on this new brief: {brief}.
                The app should now handle the additional requirements (e.g., SVG images if mentioned).
                Output ONLY the complete updated HTML file content without any explanations.
                """
                
                print("Calling Groq API for update...")
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a expert web developer. Always output complete, working HTML files with embedded CSS and JavaScript. Never include explanations or markdown code blocks."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )
                
                updated_app_html = response.choices[0].message.content.strip()
                
                # Clean up the response
                if updated_app_html.startswith('```html'):
                    updated_app_html = updated_app_html[7:]
                if updated_app_html.startswith('```'):
                    updated_app_html = updated_app_html[3:]
                if updated_app_html.endswith('```'):
                    updated_app_html = updated_app_html[:-3]
                updated_app_html = updated_app_html.strip()
                
                # Update app HTML
                if not create_file_in_repo(repo_name, 'index.html', updated_app_html, f"Update for round {round_num}"):
                    return jsonify({"error": "Failed to update index.html"}), 500
            
            # Get commit SHA
            commit_sha = get_latest_commit_sha(repo_name)
            if not commit_sha:
                return jsonify({"error": "Failed to get commit SHA"}), 500
            
            pages_url = f'https://{GITHUB_USER}.github.io/{repo_name}/'
            
            print(f"Repository setup complete. Pages URL: {pages_url}")
            
            # POST to evaluation URL
            payload = {
                "email": email,
                "task": task,
                "round": round_num,
                "nonce": nonce,
                "repo_url": f'https://github.com/{GITHUB_USER}/{repo_name}',
                "commit_sha": commit_sha,
                "pages_url": pages_url
            }
            
            print(f"Sending to evaluation URL: {evaluation_url}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            # Retry logic
            delay = 8
            max_delay = 600
            success = False
            
            while delay <= max_delay and not success:
                try:
                    response = requests.post(
                        evaluation_url.strip(),  # Remove any whitespace
                        json=payload, 
                        headers={'Content-Type': 'application/json'},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        print(f"Successfully posted to evaluation URL")
                        success = True
                        break
                    else:
                        print(f"Failed to post to evaluation URL: {response.status_code} - {response.text}")
                        
                except Exception as e:
                    print(f"Error posting to evaluation URL: {e}")
                
                if not success:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2
            
            if success:
                return jsonify({"status": "success", "pages_url": pages_url}), 200
            else:
                return jsonify({"error": "Failed to submit to evaluation URL after retries"}), 500
            
        except Exception as e:
            print(f"Error in processing: {e}")
            return jsonify({"error": str(e)}), 500
    
    except Exception as e:
        print(f"Error in handle_request: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Server is running"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)