import express from 'express';

const app = express();
app.use(express.json());

app.post('/api/build', async (req, res) => {
  try {
    const { validateRequest } = await import('../lib/utils.js');
    
    // Validate and add round=1 for build
    const buildRequest = { ...req.body, round: 1 };
    validateRequest(buildRequest);
    
    const { email, secret, task, nonce, brief, checks = [], evaluation_url, attachments = [] } = buildRequest;

    if (secret !== process.env.STUDENT_SECRET) {
      return res.status(403).json({ error: 'Invalid secret' });
    }

    console.log(`🏗️ BUILD request for task: ${task}, email: ${email}`);

    res.json({
      success: true,
      message: 'Build request accepted and processing',
      task,
      round: 1,
      timestamp: new Date().toISOString()
    });

    // Process build
    const { generateCode } = await import('../lib/llm.js');
    const { createRepository, createFile, enableGitHubPages, getLatestCommitSha, getRepoUrl, getPagesUrl } = await import('../lib/github.js');
    const { MIT_LICENSE, generateReadmeTemplate } = await import('../lib/templates.js');
    const { postWithRetry } = await import('../lib/utils.js');

    const repoName = `app-${task}`.toLowerCase();
    
    // Generate and deploy
    const htmlCode = await generateCode(`Build: ${brief}\n\nChecks:\n${checks.join('\n')}`);
    const repo = await createRepository(task);
    
    await createFile(repo, 'index.html', htmlCode, `Initial build: ${brief.substring(0, 50)}...`);
    await createFile(repo, 'LICENSE', MIT_LICENSE, 'Add MIT license');
    
    const readme = generateReadmeTemplate(task, brief, getRepoUrl(repoName), 1);
    await createFile(repo, 'README.md', readme, 'Add README');
    
    await enableGitHubPages(repo);
    const commit_sha = await getLatestCommitSha(repo);

    // Notify evaluation
    await postWithRetry(evaluation_url, {
      email, task, round: 1, nonce,
      repo_url: getRepoUrl(repoName),
      commit_sha,
      pages_url: getPagesUrl(repoName),
      timestamp: new Date().toISOString()
    });

    console.log(`✅ Build completed for task: ${task}`);

  } catch (error) {
    console.error('❌ Build failed:', error.message);
    res.status(500).json({ error: 'Build processing failed', message: error.message });
  }
});

export default app;