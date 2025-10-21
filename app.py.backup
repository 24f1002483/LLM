import os
import json
import subprocess
import time
import requests
import base64
import shutil
import re
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
app = Flask(__name__)

import os
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

STUDENT_SECRET = "secretsecretsecretsecretsecretse"
GITHUB_USER = "24f1002483"

# Configure Groq client
client = Groq(api_key=GROQ_API_KEY)

def sanitize_repo_name(name):
    """Convert task name to valid GitHub repository name"""
    # Replace spaces and special characters with hyphens
    sanitized = re.sub(r'[^\w\-_.]', '-', name)
    # Remove multiple consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    # Ensure it's not empty
    if not sanitized:
        sanitized = "auto-generated-repo"
    # Ensure it starts with a letter or number
    if not sanitized[0].isalnum():
        sanitized = "repo-" + sanitized
    # Limit length to 100 characters
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    
    return sanitized.lower()

def run_command(cmd, check=True, shell=True):
    """Run shell command with better error handling"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, check=check)
        if result.returncode != 0:
            print(f"Command may have failed: {cmd}")
            print(f"Stderr: {result.stderr}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {cmd}")
        print(f"Error: {e.stderr}")
        raise e

def create_github_repo(repo_name):
    """Create GitHub repository with proper error handling"""
    try:
        # Check if repo already exists
        check_cmd = f"gh repo view {GITHUB_USER}/{repo_name}"
        result = run_command(check_cmd, check=False)
        
        if result.returncode == 0:
            print(f"Repository {repo_name} already exists")
            return True
            
        # Create new repository - CORRECTED COMMAND
        create_cmd = f"gh repo create {repo_name} --public --confirm"
        result = run_command(create_cmd)
        
        if result.returncode == 0:
            print(f"Repository {repo_name} created successfully")
            return True
        else:
            print(f"Failed to create repository. Error: {result.stderr}")
            return False
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to create repository: {e}")
        print(f"Error details: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error creating repository: {e}")
        return False
        
   

def setup_local_repo(repo_name):
    """Set up local git repository"""
    try:
        # Clone or initialize repo
        if not os.path.exists(repo_name):
            clone_cmd = f"git clone https://github.com/{GITHUB_USER}/{repo_name}.git"
            run_command(clone_cmd)
            print(f"Cloned repository {repo_name}")
        else:
            print(f"Directory {repo_name} already exists")
            
        os.chdir(repo_name)
        print(f"Changed to directory: {os.getcwd()}")
        return True
        
    except Exception as e:
        print(f"Failed to setup local repo: {e}")
        return False

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
        
        original_dir = os.getcwd()  # Save original directory
        
        print(f"Starting processing for repo: {repo_name}, round: {round_num}")
        
        try:
            if round_num == 1:
                # Build Phase: Create new repo and generate app
                # Parse attachments
                attachment_files = {}
                for att in attachments:
                    if att['url'].startswith('data:image/png;base64,'):
                        img_data = base64.b64decode(att['url'].split(',')[1])
                        filename = att['name']
                        # Save in original directory first
                        with open(os.path.join(original_dir, filename), 'wb') as f:
                            f.write(img_data)
                        attachment_files[filename] = filename
                        print(f"Saved attachment: {filename}")
                
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
                # Groq API call with current model
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
                
                # Setup local repository
                print("Setting up local repository...")
                if not setup_local_repo(repo_name):
                    return jsonify({"error": "Failed to setup local repository"}), 500
                
                # Add MIT license
                print("Creating LICENSE file...")
                with open('LICENSE', 'w') as f:
                    f.write("""MIT License

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
SOFTWARE.""")
                
                # Write README.md
                print("Creating README.md...")
                with open('README.md', 'w') as f:
                    f.write(f"""# {repo_name}

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
""")
                
                # Write app HTML
                print("Creating index.html...")
                with open('index.html', 'w') as f:
                    f.write(app_html)
                
                # Copy attachments using shutil (Windows compatible)
                print("Copying attachments...")
                for filename in attachment_files.values():
                    source_path = os.path.join(original_dir, filename)
                    if os.path.exists(source_path):
                        shutil.copy2(source_path, '.')
                        print(f"Copied {filename} to repository")
                    else:
                        print(f"Attachment file not found: {source_path}")
                
                # Configure git user if not configured
                print("Configuring git...")
                run_command('git config user.email "student@example.com"', check=False)
                run_command('git config user.name "Student"', check=False)
                
                # Commit and push
                print("Committing and pushing...")
                run_command("git add .")
                run_command('git commit -m "Initial commit"', check=False)  # Allow empty commit
                run_command("git push origin main")
                
                print("GitHub Pages should be available automatically for public repositories")
            
            else:
                # Revise Phase: Modify existing repo
                print(f"Round {round_num}: Updating existing repository...")
                if not setup_local_repo(repo_name):
                    return jsonify({"error": "Failed to setup local repository"}), 500
                
                # Pull latest changes
                run_command("git pull origin main")
                
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
                
                # Overwrite app HTML
                with open('index.html', 'w') as f:
                    f.write(updated_app_html)
                
                # Update README.md
                with open('README.md', 'a') as f:
                    f.write(f"\n\n## Updates (Round {round_num})\n{brief}")
                
                # Commit and push changes
                run_command("git add .")
                run_command(f'git commit -m "Update for round {round_num}"')
                run_command("git push origin main")
            
            # Get commit SHA
            result = run_command("git rev-parse HEAD")
            commit_sha = result.stdout.strip()
            
            pages_url = f'https://{GITHUB_USER}.github.io/{repo_name}/'
            
            print(f"Repository setup complete. Pages URL: {pages_url}")
            
            # POST to evaluation URL with exact JSON structure and retry logic
            payload = {
                "email": email,
                "task": task,  # Use original task name
                "round": round_num,
                "nonce": nonce,
                "repo_url": f'https://github.com/{GITHUB_USER}/{repo_name}',
                "commit_sha": commit_sha,
                "pages_url": pages_url
            }
            
            print(f"Sending to evaluation URL: {evaluation_url}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            # Retry logic with exponential backoff (1, 2, 4, 8... seconds)
            delay = 8
            max_delay = 600  # 10 minutes maximum
            success = False
            
            while delay <= max_delay and not success:
                try:
                    response = requests.post(
                        evaluation_url, 
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
                    delay *= 2  # Exponential backoff
            
            if success:
                return jsonify({"status": "success", "pages_url": pages_url}), 200
            else:
                return jsonify({"error": "Failed to submit to evaluation URL after retries"}), 500
            
        finally:
            # Always return to original directory
            os.chdir(original_dir)
            print(f"Returned to original directory: {original_dir}")
    
    except Exception as e:
        print(f"Error in handle_request: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Server is running"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)