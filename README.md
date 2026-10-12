# Abdi Abera Portfolio

The portfolio is served by a small Flask backend. Contact form submissions are
validated and emailed to `worldbbc@gmail.com` through Gmail SMTP.

## Run locally on Windows

1. Install Python 3.10 or later.
2. In PowerShell, from this folder, create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Create a Google App Password for `worldbbc@gmail.com` (Google Account
   2-Step Verification must be enabled). Keep it private, then set it in the
   current PowerShell session:

   ```powershell
   $env:GMAIL_APP_PASSWORD = "your-google-app-password"
   ```

4. Start the site:

   ```powershell
   python -m flask --app app run
   ```

5. Open <http://127.0.0.1:5000>.

Run the backend tests with:

```powershell
python -m unittest discover -s tests
```

## Deploy to Render

1. Push this project to a GitHub repository. Do not add your Google App Password
   to the repository.
2. In Render, choose **New** → **Blueprint**, then connect that repository.
   Render reads `render.yaml` and creates the web service.
3. In the service’s **Environment** settings, set `GMAIL_APP_PASSWORD` to the
   Google App Password. Save the change and wait for the service to deploy.
4. Open the `onrender.com` URL shown on the service’s Render dashboard.

Render may take a short time to wake the free service after inactivity. The
`/healthz` endpoint reports when the web service is responding.
