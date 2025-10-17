import { Octokit } from '@octokit/rest';

// Initialize Octokit with authentication
const octokit = new Octokit({ 
  auth: process.env.GITHUB_TOKEN,
  userAgent: 'Student-Deployment-System/1.0'
});

const username = process.env.GITHUB_USERNAME;

if (!username || !process.env.GITHUB_TOKEN) {
  throw new Error('❌ GITHUB_USERNAME and GITHUB_TOKEN are required');
}

/**
 * Create a new GitHub repository
 */
export async function createRepository(taskId) {
  const repoName = `app-${taskId}`.toLowerCase().replace(/[^a-z0-9-_]/g, '-');
  
  console.log(`📦 Creating repository: ${repoName}`);
  
  try {
    const { data } = await octokit.repos.createForAuthenticatedUser({
      name: repoName,
      description: `Auto-generated application for task: ${taskId}`,
      private: false,
      auto_init: false,
      has_projects: false,
      has_wiki: false,
      has_downloads: false
    });
    
    console.log(`✅ Repository created: ${data.html_url}`);
    return data;
    
  } catch (error) {
    if (error.status === 422) {
      console.log('📦 Repository already exists, using existing one');
      const { data } = await octokit.repos.get({
        owner: username,
        repo: repoName
      });
      return data;
    }
    console.error('❌ Failed to create repository:', error.message);
    throw error;
  }
}

/**
 * Create or update a file in repository
 */
export async function createFile(repo, path, content, message) {
  try {
    await octokit.repos.createOrUpdateFileContents({
      owner: repo.owner.login,
      repo: repo.name,
      path,
      message,
      content: Buffer.from(content).toString('base64'),
      committer: {
        name: 'Student Deployment System',
        email: 'system@student-deployment.com'
      }
    });
    
    console.log(`✅ File created: ${path}`);
    
  } catch (error) {
    console.error(`❌ Failed to create ${path}:`, error.message);
    throw error;
  }
}

/**
 * Update existing file
 */
export async function updateFile(repo, path, content, message) {
  try {
    // Get current file SHA
    const { data: currentFile } = await octokit.repos.getContent({
      owner: repo.owner.login,
      repo: repo.name,
      path
    });
    
    await octokit.repos.createOrUpdateFileContents({
      owner: repo.owner.login,
      repo: repo.name,
      path,
      message,
      content: Buffer.from(content).toString('base64'),
      sha: currentFile.sha,
      committer: {
        name: 'Student Deployment System',
        email: 'system@student-deployment.com'
      }
    });
    
    console.log(`✅ File updated: ${path}`);
    
  } catch (error) {
    console.error(`❌ Failed to update ${path}:`, error.message);
    throw error;
  }
}

/**
 * Enable GitHub Pages
 */
export async function enableGitHubPages(repo) {
  try {
    await octokit.repos.createPagesSite({
      owner: repo.owner.login,
      repo: repo.name,
      source: {
        branch: 'main',
        path: '/'
      }
    });
    
    console.log('🌐 GitHub Pages enabled');
    
    // Wait a bit for Pages to initialize
    await new Promise(resolve => setTimeout(resolve, 5000));
    
  } catch (error) {
    if (error.status === 409) {
      console.log('🌐 GitHub Pages already enabled');
    } else {
      console.error('❌ Failed to enable GitHub Pages:', error.message);
      throw error;
    }
  }
}

/**
 * Get latest commit SHA
 */
export async function getLatestCommitSha(repo) {
  try {
    const { data } = await octokit.repos.getCommit({
      owner: repo.owner.login,
      repo: repo.name,
      ref: 'main'
    });
    
    return data.sha;
    
  } catch (error) {
    console.error('❌ Failed to get commit SHA:', error.message);
    return 'unknown';
  }
}

/**
 * Get repository URL
 */
export function getRepoUrl(repoName) {
  return `https://github.com/${username}/${repoName}`;
}

/**
 * Get Pages URL
 */
export function getPagesUrl(repoName) {
  return `https://${username}.github.io/${repoName}/`;
}