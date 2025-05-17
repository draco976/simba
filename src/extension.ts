import * as vscode from "vscode";
import * as path from "path";
import simpleGit from 'simple-git';

interface FileChange {
    type: 'addition' | 'deletion';
    line: number;
    content: string;
}

interface FileInfo {
    filePath: string;
    status: string;
    additions: number;
    deletions: number;
    changes: FileChange[];
}

interface CommitInfo {
    repoName: string;
    authorName: string;
    authorEmail: string;
    hash: string;
    message: string;
    date: string;
    changes: FileInfo[];
}

export function activate(context: vscode.ExtensionContext) {
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
  const gitCheckButton = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      1000
  );
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
                  
                  const upstreamHashes = new Set(upstreamLog.map((commit: { hash: string }) => commit.hash));
                  unpushedCommits = logResult.filter((commit: { hash: string }) => !upstreamHashes.has(commit.hash));
              } catch (err) {
                  console.log('Error getting upstream commits, showing all local commits instead');
                  vscode.window.showInformationMessage('Error comparing with upstream. Showing all local commits.');
              }
          } else {
              vscode.window.showInformationMessage('No upstream branch found. Showing all local commits.');
          }

          if (unpushedCommits.length === 0) {
              console.log('No unpushed commits found');
              vscode.window.showInformationMessage('No unpushed commits found');
          } else {
              console.log('Unpushed commits:');
              
              // Process each commit with detailed information
              for (const commit of unpushedCommits) {
                  const repoInfo: CommitInfo = {
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

                      const git = simpleGit(repo.rootUri.fsPath);
                      const changes = await git.raw(['show', '--name-status', '--pretty=format:', commit.hash]);
                      
                      interface ChangedFile {
                          uri: vscode.Uri;
                          status: string; // 'A': Added, 'M': Modified, 'D': Deleted
                      }
                      
                      const changedFiles = changes.trim().split('\n')
                          .filter((line: string) => line.trim().length > 0) // Filter out empty lines
                          .map((line: string) => {
                              const [status, file] = line.split('\t');
                              if (!file) return null; // Skip invalid entries
                              return {
                                  uri: vscode.Uri.file(path.join(repo.rootUri.fsPath, file)),
                                  status
                              } as ChangedFile;
                          })
                          .filter((file: ChangedFile | null) => file !== null); // Filter out null entries

                      // Process each changed file
                      for (const change of changedFiles as ChangedFile[]) {
                          const fileChange: FileInfo = {
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

                                      if (!inHunk) continue;

                                      if (line.startsWith('+') && !line.startsWith('+++')) {
                                          fileChange.additions++;
                                          fileChange.changes.push({
                                              type: 'addition',
                                              line: lineNumber++,
                                              content: line.substring(1)
                                          });
                                      } else if (line.startsWith('-') && !line.startsWith('---')) {
                                          fileChange.deletions++;
                                          fileChange.changes.push({
                                              type: 'deletion',
                                              line: lineNumber,
                                              content: line.substring(1)
                                          });
                                      } else {
                                          lineNumber++;
                                      }
                                  }
                              }
                          } catch (err) {
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
                  } catch (err) {
                      console.log('Error getting diff:', err);
                  }
              }
              
              vscode.window.showInformationMessage(`Found ${unpushedCommits.length} unpushed commits. Check console for details.`);
          }

      } catch (error) {
          console.error('Error checking unpushed commits:', error);
          vscode.window.showErrorMessage('Error checking unpushed commits');
      }
  });

  context.subscriptions.push(gitCheckButton);
  context.subscriptions.push(disposable);
}