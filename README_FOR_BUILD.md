# How to Build Your Android App

Since building Android apps on Windows is complex, I have set up a workflow that uses GitHub to build the app for you automatically.

## Steps to Build

1.  **Create a GitHub Account** (if you don't have one): [github.com](https://github.com)
2.  **Create a New Repository**:
    *   Go to "New Repository".
    *   Name it something like `image-search-app`.
    *   Make it **Public** (Private repos have limited free Actions minutes, but work too).
3.  **Upload Files**:
    *   Upload ALL the files in your folder to this new repository.
        *   `app.py`
        *   `main.py`
        *   `buildozer.spec`
        *   `requirements.txt`
        *   `.github/workflows/build.yml` (Ensure this is in the `.github/workflows` folder structure)
        *   `templates/` folder
        *   (You don't need `downloads`, `__pycache__`, or `venv`)
4.  **Wait for Build**:
    *   Go to the **Actions** tab in your GitHub repository.
    *   You will see a workflow named "Build Android APK" running.
    *   It will take about 10-15 minutes.
5.  **Download APK**:
    *   Once the workflow shows a green checkmark (Success), click on it.
    *   Scroll down to the **Artifacts** section at the bottom.
    *   Click on `app-debug-apk` to download the zip file.
    *   Extract the zip to find your `.apk` file.
6.  **Install on Phone**:
    *   Transfer the file to your phone.
    *   Tap to install (you may need to allow "Install from unknown sources").

## Troubleshooting
- If the build fails, check the logs in the Actions tab.
- Common issues are usually related to dependencies or version mismatches, but I have pinned critical versions in `buildozer.spec`.
