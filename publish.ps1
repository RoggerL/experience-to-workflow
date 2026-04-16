# Publish ExpForge to GitHub
# Run this script and follow the prompts

$username = Read-Host "Enter your GitHub username"
$repo = Read-Host "Enter repository name (e.g., expforge)"

if ([string]::IsNullOrWhiteSpace($username) -or [string]::IsNullOrWhiteSpace($repo)) {
    Write-Host "Username and repo name are required." -ForegroundColor Red
    exit 1
}

$remoteUrl = "https://github.com/$username/$repo.git"

Write-Host "Adding remote origin: $remoteUrl"
git remote remove origin 2>$null
git remote add origin $remoteUrl

Write-Host "Pushing to GitHub..."
git branch -M main
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "Success! Your repo is live at: https://github.com/$username/$repo" -ForegroundColor Green
} else {
    Write-Host "Push failed. Make sure the repository exists on GitHub and you have push access." -ForegroundColor Red
    Write-Host "If the repo does not exist yet, create it first at: https://github.com/new"
}
