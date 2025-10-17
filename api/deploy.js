import { generateCode } from "../lib/llm.js";
import { createRepository, createFile, enableGitHubPages } from "../lib/github.js";
import { MIT_LICENSE, generateReadmeTemplate } from "../lib/templates.js";

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const { task, brief } = req.body;

    // Step 1: Generate code using Gemini
    const html = await generateCode(brief);

    // Step 2: Create GitHub repo
    const repo = await createRepository(task);

    // Step 3: Upload files
    await createFile(repo, "index.html", html, "Initial commit");
    await createFile(repo, "LICENSE", MIT_LICENSE, "Add license");

    const readme = generateReadmeTemplate(task, brief, repo.html_url);
    await createFile(repo, "README.md", readme, "Add README");

    // Step 4: Enable GitHub Pages
    await enableGitHubPages(repo);

    res.status(200).json({
      success: true,
      message: "✅ Deployed successfully!",
      repo: repo.html_url,
      live: `https://${process.env.GITHUB_USERNAME}.github.io/${repo.name}/`
    });
  } catch (err) {
    console.error("❌ Deployment failed:", err.message);
    res.status(500).json({ success: false, error: err.message });
  }
}
