"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const simple_git_1 = __importDefault(require("simple-git"));
function activate(context) {
    console.log("Extension is now active!, this is where we will setup connection with our server");
    // Open the test directory when extension activates
    const homeDir = process.env.HOME || process.env.USERPROFILE;
    if (homeDir) {
        const testDirPath = path.join(homeDir, 'test-dir');
        // Create the directory if it doesn't exist
        const fs = require('fs');
        if (!fs.existsSync(testDirPath)) {
            fs.mkdirSync(testDirPath, { recursive: true });
        }
        // Open the folder
        vscode.commands.executeCommand('vscode.openFolder', vscode.Uri.file(testDirPath), {
            forceNewWindow: false
        });
    }
    // Create status bar item
    const gitCheckButton = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 1000);
    gitCheckButton.text = "$(git-commit) Check Unpushed Commits";
    gitCheckButton.tooltip = "Check for unpushed git commits";
    gitCheckButton.command = 'extension.checkUnpushedCommits';
    gitCheckButton.show();
    // Register command
    let disposable = vscode.commands.registerCommand('extension.checkUnpushedCommits', async () => {
        const gitExtension = vscode.extensions.getExtension('vscode.git')?.exports;
        if (!gitExtension) {
            vscode.window.showErrorMessage('Git extension not found');
            return;
        }
        const git = gitExtension.getAPI(1);
        const repo = git.repositories[0];
        if (!repo) {
            vscode.window.showErrorMessage('No git repository found');
            return;
        }
        try {
            // Get local and remote refs
            const localRefs = await repo.getRefs();
            const currentBranch = repo.state.HEAD;
            if (!currentBranch) {
                vscode.window.showErrorMessage('Not on any branch');
                return;
            }
            // Get commits
            const logResult = await repo.log({
                maxEntries: 100
            });
            let unpushedCommits = logResult;
            // If there's an upstream branch, filter for unpushed commits only
            if (currentBranch.upstream) {
                try {
                    const upstreamLog = await repo.log({
                        maxEntries: 100
                    });
                    const upstreamHashes = new Set(upstreamLog.map((commit) => commit.hash));
                    unpushedCommits = logResult.filter((commit) => !upstreamHashes.has(commit.hash));
                }
                catch (err) {
                    console.log('Error getting upstream commits, showing all local commits instead');
                    vscode.window.showInformationMessage('Error comparing with upstream. Showing all local commits.');
                }
            }
            else {
                vscode.window.showInformationMessage('No upstream branch found. Showing all local commits.');
            }
            if (unpushedCommits.length === 0) {
                console.log('No unpushed commits found');
                vscode.window.showInformationMessage('No unpushed commits found');
            }
            else {
                console.log('Unpushed commits:');
                // Process each commit with detailed information
                for (const commit of unpushedCommits) {
                    const repoInfo = {
                        repoName: repo.rootUri.path.split('/').pop() || '',
                        authorName: commit.authorName,
                        authorEmail: commit.authorEmail,
                        hash: commit.hash.substring(0, 7),
                        message: commit.message,
                        date: commit.authorDate.toLocaleString(),
                        changes: []
                    };
                    try {
                        // Get the changes for this specific commit
                        const git = (0, simple_git_1.default)(repo.rootUri.fsPath);
                        const changes = await git.raw(['show', '--name-status', '--pretty=format:', commit.hash]);
                        const changedFiles = changes.trim().split('\n')
                            .filter((line) => line.trim().length > 0) // Filter out empty lines
                            .map((line) => {
                            const [status, file] = line.split('\t');
                            if (!file)
                                return null; // Skip invalid entries
                            return {
                                uri: vscode.Uri.file(path.join(repo.rootUri.fsPath, file)),
                                status
                            };
                        })
                            .filter((file) => file !== null); // Filter out null entries
                        // Process each changed file
                        for (const change of changedFiles) {
                            const fileChange = {
                                filePath: change.uri.fsPath,
                                status: change.status,
                                additions: 0,
                                deletions: 0,
                                changes: []
                            };
                            try {
                                // Get raw diff output for this specific commit using git show
                                const gitDiff = await git.raw(['show', '--unified=0', commit.hash, '--', change.uri.fsPath]);
                                if (gitDiff) {
                                    const lines = gitDiff.split('\n');
                                    let lineNumber = 0;
                                    let inHunk = false;
                                    for (const line of lines) {
                                        if (line.startsWith('@@')) {
                                            const match = line.match(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
                                            if (match) {
                                                lineNumber = parseInt(match[1]) - 1;
                                                inHunk = true;
                                            }
                                            continue;
                                        }
                                        if (!inHunk)
                                            continue;
                                        if (line.startsWith('+') && !line.startsWith('+++')) {
                                            fileChange.additions++;
                                            fileChange.changes.push({
                                                type: 'addition',
                                                line: lineNumber++,
                                                content: line.substring(1)
                                            });
                                        }
                                        else if (line.startsWith('-') && !line.startsWith('---')) {
                                            fileChange.deletions++;
                                            fileChange.changes.push({
                                                type: 'deletion',
                                                line: lineNumber,
                                                content: line.substring(1)
                                            });
                                        }
                                        else {
                                            lineNumber++;
                                        }
                                    }
                                }
                            }
                            catch (err) {
                                console.log(`Error getting diff for file ${change.uri.fsPath}:`, err);
                            }
                            repoInfo.changes.push(fileChange);
                        }
                        // send json information as POST request to server
                        const server_url = 'http://localhost:3000/commit';
                        const response = await fetch(server_url, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(repoInfo)
                        });
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        const responseData = await response.json();
                        console.log('Response from server:', responseData);
                        console.log(JSON.stringify(repoInfo, null, 2));
                    }
                    catch (err) {
                        console.log('Error getting diff:', err);
                    }
                }
                vscode.window.showInformationMessage(`Found ${unpushedCommits.length} unpushed commits. Check console for details.`);
            }
        }
        catch (error) {
            console.error('Error checking unpushed commits:', error);
            vscode.window.showErrorMessage('Error checking unpushed commits');
        }
    });
    context.subscriptions.push(gitCheckButton);
    context.subscriptions.push(disposable);
}
exports.activate = activate;
//# sourceMappingURL=extension.js.map