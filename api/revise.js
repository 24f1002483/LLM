import express from 'express';

const app = express();
app.use(express.json());

app.post('/api/revise', async (req, res) => {
  try {
    const { validateRequest } = await import('../lib/utils.js');
    
    // Validate and add round=2 for revise
    const reviseRequest = { ...req.body, round: 2 };
    validateRequest(reviseRequest);
    
    const { email, secret, task, nonce, brief, checks = [], evaluation_url } = reviseRequest;

    if (secret !== process.env.STUDENT_SECRET) {
      return res.status(403).json({ error: 'Invalid secret' });
    }

    console.log(`🔄 REVISE request for task: ${task}, email: ${email}`);

    res.json({
      success: true,
      message: 'Revision request accepted and processing',
      task,
      round: 2,
      timestamp: new Date().toISOString()
    });

    // Process revision
    const { generateCode } = await import('../lib/llm.js');
    const { updateFile, enableGitHubPages, getLatestCommitSha, getRepoUrl, getPagesUrl } = await import('../lib/github.js');
    const { generateReadmeTemplate } = await import('../lib/templates.js');
    const { postWithRetry } = await import('../lib/utils.js');

    const repoName = `app-${task}`.toLowerCase();
    const repo = { owner: { login: process.env.GITHUB_USERNAME }, name: repoName };

    // Generate revised code
    const revisedHtml = await generateCode(`REVISION Required:\n${brief}\n\nValidation Checks:\n${checks.join('\n')}`, 'This is a revision round. Modify and improve the existing application.');
    
    // Update files
    await updateFile(repo, 'index.html', revisedHtml, `Revision: ${brief.substring(0, 50)}...`);
    
    const updatedReadme = generateReadmeTemplate(task, brief, getRepoUrl(repoName), 2);
    await updateFile(repo, 'README.md', updatedReadme, 'Update README for revision');
    
    await enableGitHubPages(repo);
    const commit_sha = await getLatestCommitSha(repo);

    // Notify evaluation
    await postWithRetry(evaluation_url, {
      email, task, round: 2, nonce,
      repo_url: getRepoUrl(repoName),
      commit_sha,
      pages_url: getPagesUrl(repoName),
      timestamp: new Date().toISOString()
    });

    console.log(`✅ Revision completed for task: ${task}`);

  } catch (error) {
    console.error('❌ Revision failed:', error.message);
    res.status(500).json({ error: 'Revision processing failed', message: error.message });
  }
});

export default app;