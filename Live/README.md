# Pragyaan — One-hour runnable MVP

## Windows setup

```powershell
cd C:\path\to\Pragyaan_final_ready
py -m pip install -r requirements.txt
py -m playwright install chromium
$env:GEMINI_API_KEY = "YOUR_EXISTING_KEY"
$env:GEMINI_MODEL = "gemini-3.8-flash"
```

Test the included local shop:

```powershell
py main.py "add a laptop to the cart and reach checkout" "file:///C:/path/to/Pragyaan_final_ready/target-app/target_app.html"
```

Or serve it:

```powershell
cd target-app
py -m http.server 8000
```

Then in another PowerShell:

```powershell
cd C:\path\to\Pragyaan_final_ready
py main.py "add a laptop to the cart and reach checkout" "http://localhost:8000/target_app.html"
```

Use your own target app by replacing the URL.

The architecture is: observe visible UI -> Gemini proposes one structured action -> deterministic validation/resolution -> Playwright executes -> screenshot/trace -> repeat.
