import express from "express";
import dotenv from "dotenv";
import { generateCode } from "../lib/llm.js";
import { createRepository, createFile, enableGitHubPages } from "../lib/github.js";
import { generateReadmeTemplate, MIT_LICENSE } from "../lib/templates.js";

dotenv.config();
const app = express();
app.use(express.json());

// Example route — generate and deploy app
app.post("/deploy", async (req, res) => {
  try {
    const { task, brief } = req.body;
    console.log(`🚀 Starting deployment for: ${task}`);

    // Step 1: Generate code with Gemini
    const html = await generateCode(brief);

    // Step 2: Create a new GitHub repo
    const repo = await createRepository(task);

    // Step 3: Upload files
    await createFile(repo, "index.html", html, "Initial commit");
    await createFile(repo, "LICENSE", MIT_LICENSE, "Add license");

    const readme = generateReadmeTemplate(task, brief, repo.html_url);
    await createFile(repo, "README.md", readme, "Add README");

    // Step 4: Enable GitHub Pages
    await enableGitHubPages(repo);

    res.json({
      success: true,
      message: "✅ Deployed successfully!",
      repo: repo.html_url,
      live: `https://${process.env.GITHUB_USERNAME}.github.io/${repo.name}/`
    });
  } catch (err) {
    console.error("❌ Deployment failed:", err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.listen(process.env.PORT || 5000, () =>
  console.log(`✅ Server running on http://localhost:${process.env.PORT || 5000}`)
);