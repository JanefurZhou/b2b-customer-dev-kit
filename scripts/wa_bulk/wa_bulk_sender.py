#!/usr/bin/env python3
"""
WA Bulk Sender - generic B2B kit
Generate PowerShell scripts for WhatsApp Desktop batch messaging.
Core: Screenshot AI verification + template variables + resume + audit + harness.
"""
import base64
import json
import sys
for _s in (sys.stdout, sys.stderr):  # keep non-ASCII output safe when redirected or on legacy Windows consoles
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import re
import random
import time


# ========== Config ==========

# Windows working directories (override with env vars; defaults are neutral placeholders).
# Set WA_WORK_DIR to your own local folder, e.g.  C:\\wa_outreach
_WA_WORK = os.environ.get("WA_WORK_DIR") or os.path.join(os.environ.get("USERPROFILE", r"C:\\Users\\<you>"), "wa_outreach")
SCRIPT_DIR = os.environ.get("WA_SCRIPT_DIR", os.path.join(_WA_WORK, "scripts"))
SCREENSHOT_DIR = os.environ.get("WA_SCREENSHOT_DIR", os.path.join(_WA_WORK, "screenshots"))
# WA_MESSAGE_DIR matches the PowerShell script (WA_MSG_DIR is the legacy name, still accepted)
MSG_DIR = os.environ.get("WA_MESSAGE_DIR") or os.environ.get("WA_MSG_DIR") or os.path.join(_WA_WORK, "messages")
LOG_DIR = os.environ.get("WA_LOG_DIR", os.path.join(_WA_WORK, "logs"))
PROGRESS_FILE = os.environ.get("WA_PROGRESS_FILE") or os.path.join(LOG_DIR, "wa_progress.json")
# Anti-ban: daily sending cap (same as wa_bulk_guide.md "daily count = 200 → stop"); lower it with WA_DAILY_LIMIT
DAILY_COUNT_FILE = os.path.join(LOG_DIR, "wa_daily_count.json")
try:
    DAILY_LIMIT = max(1, min(200, int(os.environ.get("WA_DAILY_LIMIT", "200"))))
except ValueError:
    DAILY_LIMIT = 200


# ========== Onboarding gate (shared with the rest of the kit) ==========
# Read-only commands (validate / preview / progress / template) work before onboarding.
# Anything that opens WhatsApp or produces a send script requires a complete,
# user-confirmed profile — same rule as every email/search script in this kit.
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)


def require_profile():
    """Abort (exit 2) unless config/company_profile.json is complete and user-confirmed."""
    try:
        import config as _cfg
    except ImportError:
        print("ERROR: scripts/config.py not found; cannot verify onboarding. Refusing to continue.")
        sys.exit(2)
    try:
        return _cfg.load_profile(require_complete=True)
    except _cfg.ProfileNotConfigured as e:
        print("ERROR: company profile not ready; generating the WhatsApp sending script is blocked.")
        print(e)
        sys.exit(2)


def _render_ps(template):
    """Substitute local directory tokens in embedded PowerShell templates."""
    return (
        template
        .replace("@@SCRIPT_DIR@@", SCRIPT_DIR)
        .replace("@@SCREENSHOT_DIR@@", SCREENSHOT_DIR)
        .replace("@@MSG_DIR@@", MSG_DIR)
        .replace("@@LOG_DIR@@", LOG_DIR)
    )

# ========== PowerShell Script Templates (Pure English) ==========

AUDIT_PS1 = r"""
# WA Audit - Post-send verification
# Open each sent chat and screenshot for AI verification
param(
    [string]$ProgressFile = "@@LOG_DIR@@\wa_progress.json",
    [string]$MessageFile = "",
    [int]$StartFrom = 1
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screenshotDir = "@@SCREENSHOT_DIR@@"
$tempDir = $env:TEMP

if (-not (Test-Path $ProgressFile)) {
    Write-Output "ERROR: Progress file not found at $ProgressFile"
    exit 1
}

$progress = Get-Content $ProgressFile -Raw | ConvertFrom-Json

# Build brand lookup from message file if provided
$brandLookup = @{}
if ($MessageFile -ne "" -and (Test-Path $MessageFile)) {
    $msgData = Get-Content $MessageFile -Raw | ConvertFrom-Json
    if ($msgData -is [System.Array]) {
        foreach ($item in $msgData) {
            $ph = $item.phone
            $br = $item.brand
            if ($ph -and $br) { $brandLookup[$ph] = $br }
        }
    }
}

# Collect sent entries - support both old format (string array) and new format (objects)
$sentEntries = @()
if ($progress.sent) {
    foreach ($entry in $progress.sent) {
        if ($entry -is [string]) {
            $phone = $entry
            $brand = if ($brandLookup.ContainsKey($phone)) { $brandLookup[$phone] } else { "?" }
            $sentEntries += @{ Phone = $phone; Brand = $brand }
        } elseif ($entry.phone) {
            $sentEntries += @{ Phone = $entry.phone; Brand = ($entry.brand ?? "?") }
        }
    }
}

if ($sentEntries.Count -eq 0) {
    Write-Output "No sent records found in progress file"
    exit 0
}

$total = $sentEntries.Count
Write-Output "Auditing $total sent records..."

for ($i = 0; $i -lt $total; $i++) {
    $idx = $i + 1
    if ($idx -lt $StartFrom) { continue }

    $entry = $sentEntries[$i]
    $phone = $entry.Phone
    $brand = $entry.Brand

    Write-Output "--- Audit #$idx / $total : $brand ($phone) ---"

    # Open chat
    Start-Process "whatsapp://send?phone=$phone"
    Start-Sleep -Seconds 4

    # Wait for WhatsApp focus (poll up to 5 seconds)
    $focused = $false
    for ($attempt = 0; $attempt -lt 25; $attempt++) {
        try {
            $waProc = Get-Process WhatsApp.Root -ErrorAction SilentlyContinue
            if ($waProc -and $waProc.MainWindowTitle -ne '') {
                $focused = $true
                break
            }
        } catch {}
        Start-Sleep -Milliseconds 200
    }

    if (-not $focused) {
        Write-Output "SKIP: WhatsApp not focused for $phone"
        continue
    }

    # Screenshot to temp first (GDI+ safe path)
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen
    $bmp = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)

    $tempFile = Join-Path $tempDir "wa_audit_$idx.png"
    $destFile = Join-Path $screenshotDir "audit_${idx}_${phone}.png"

    try {
        $bmp.Save($tempFile, [System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose()
        $bmp.Dispose()

        # Copy to Chinese path
        Copy-Item -Path $tempFile -Destination $destFile -Force
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        Write-Output "OK: audit_${idx}_${phone}.png"
    } catch {
        Write-Output "ERROR: Screenshot save failed - $_"
        $g.Dispose()
        $bmp.Dispose()
    }

    # Small delay between entries
    Start-Sleep -Milliseconds 500
}

Write-Output "=== AUDIT COMPLETE ==="
"""

HARNESS_PS1 = r"""
# WA Harness - Pre-send dry run
# Send first N messages to YOUR test number to verify format/content
param(
    [Parameter(Mandatory=$true)]
    [string]$TestPhone,
    [Parameter(Mandatory=$true)]
    [string]$MessageFile,
    [int]$Count = 3
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screenshotDir = "@@SCREENSHOT_DIR@@"
$msgDir = "@@MSG_DIR@@"
$tempDir = $env:TEMP

if (-not (Test-Path $MessageFile)) {
    Write-Output "ERROR: Message file not found at $MessageFile"
    exit 1
}

# Load messages (support both array and template formats)
$msgData = Get-Content $MessageFile -Raw | ConvertFrom-Json

$messages = @()
if ($msgData -is [System.Array]) {
    $messages = @($msgData)
} elseif ($msgData.contacts) {
    # Template format - do variable substitution
    $template = $msgData.template
    $defaults = @{}
    foreach ($prop in $msgData.PSObject.Properties) {
        if ($prop.Name -notin @('template','contacts')) {
            $defaults[$prop.Name] = $prop.Value
        }
    }
    foreach ($contact in $msgData.contacts) {
        $msg = $template
        $vars = @{} + $defaults
        foreach ($prop in $contact.PSObject.Properties) {
            $vars[$prop.Name] = $prop.Value
        }
        foreach ($key in $vars.Keys) {
            $msg = $msg.Replace("{$key}", $vars[$key].ToString())
        }
        $messages += @{
            brand = $contact.brand ?? "?"
            phone = $contact.phone ?? ""
            message = $msg
        }
    }
}

if ($messages.Count -eq 0) {
    Write-Output "ERROR: No messages found in file"
    exit 1
}

$limit = [Math]::Min($Count, $messages.Count)
Write-Output "Harness: Sending first $limit messages to test number $TestPhone"
Write-Output ""

# Open test chat once
Start-Process "whatsapp://send?phone=$TestPhone"
Start-Sleep -Seconds 4

# Wait for WhatsApp focus
$focused = $false
for ($attempt = 0; $attempt -lt 25; $attempt++) {
    try {
        $waProc = Get-Process WhatsApp -ErrorAction SilentlyContinue
        if ($waProc -and $waProc.MainWindowTitle -ne '') {
            $focused = $true
            break
        }
    } catch {}
    Start-Sleep -Milliseconds 200
}

if (-not $focused) {
    Write-Output "ERROR: WhatsApp not focused. Is it running?"
    exit 1
}

for ($i = 0; $i -lt $limit; $i++) {
    $msg = $messages[$i]
    $brand = $msg.brand ?? "?"
    $realPhone = $msg.phone ?? "?"
    $messageText = $msg.message ?? ""

    Write-Output "--- Harness #$($i+1)/$limit : $brand (originally to $realPhone) ---"

    # Write message to temp file
    $msgTempFile = Join-Path $msgDir "harness_msg_$($i+1).txt"
    Set-Content -Path $msgTempFile -Value $messageText -Encoding UTF8 -NoNewline

    # Screenshot BEFORE paste
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen
    $bmp = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)

    $tempBefore = Join-Path $tempDir "wa_harness_before_$($i+1).png"
    $destBefore = Join-Path $screenshotDir "harness_${i+1}_before.png"
    try {
        $bmp.Save($tempBefore, [System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose()
        $bmp.Dispose()
        Copy-Item $tempBefore $destBefore -Force
        Remove-Item $tempBefore -Force -ErrorAction SilentlyContinue
        Write-Output "OK: harness_${i+1}_before.png"
    } catch {
        Write-Output "ERROR: Before screenshot failed"
        $g.Dispose()
        $bmp.Dispose()
    }

    # Paste message from temp file
    $clipText = Get-Content $msgTempFile -Raw
    [System.Windows.Forms.Clipboard]::SetText($clipText)
    Start-Sleep -Milliseconds 500
    [System.Windows.Forms.SendKeys]::SendWait('^v')
    Start-Sleep -Milliseconds 1000

    # Screenshot AFTER paste (before send)
    $bmp2 = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
    $g2 = [System.Drawing.Graphics]::FromImage($bmp2)
    $g2.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)

    $tempAfter = Join-Path $tempDir "wa_harness_after_paste_$($i+1).png"
    $destAfter = Join-Path $screenshotDir "harness_${i+1}_pasted.png"
    try {
        $bmp2.Save($tempAfter, [System.Drawing.Imaging.ImageFormat]::Png)
        $g2.Dispose()
        $bmp2.Dispose()
        Copy-Item $tempAfter $destAfter -Force
        Remove-Item $tempAfter -Force -ErrorAction SilentlyContinue
        Write-Output "OK: harness_${i+1}_pasted.png"
    } catch {
        Write-Output "ERROR: After-paste screenshot failed"
        $g2.Dispose()
        $bmp2.Dispose()
    }

    # Send (Enter)
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
    Start-Sleep -Milliseconds 1500

    # Screenshot AFTER send
    $bmp3 = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
    $g3 = [System.Drawing.Graphics]::FromImage($bmp3)
    $g3.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)

    $tempSent = Join-Path $tempDir "wa_harness_sent_$($i+1).png"
    $destSent = Join-Path $screenshotDir "harness_${i+1}_sent.png"
    try {
        $bmp3.Save($tempSent, [System.Drawing.Imaging.ImageFormat]::Png)
        $g3.Dispose()
        $bmp3.Dispose()
        Copy-Item $tempSent $destSent -Force
        Remove-Item $tempSent -Force -ErrorAction SilentlyContinue
        Write-Output "OK: harness_${i+1}_sent.png"
    } catch {
        Write-Output "ERROR: After-send screenshot failed"
        $g3.Dispose()
        $bmp3.Dispose()
    }

    Write-Output "SENT: Message for $brand delivered to test number $TestPhone"

    # Delay between messages
    if ($i -lt $limit - 1) {
        Start-Sleep -Seconds 3
    }
}

Write-Output ""
Write-Output "=== HARNESS COMPLETE ==="
Write-Output "Sent $limit messages to $TestPhone"
Write-Output "Screenshots saved to $screenshotDir"
Write-Output "Please verify message format and content on your phone"
"""


# ========== PowerShell Script Generation (Legacy Base64) ==========

def generate_screenshot_script():
    """Generate screenshot script (Base64 encoded)"""
    script = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
$bitmap.Save('C:\Users\Public\wa_verify.png')
$graphics.Dispose()
$bitmap.Dispose()
Write-Output 'OK'
"""
    return base64.b64encode(script.encode('utf-16-le')).decode('ascii')


def generate_send_script(message_text):
    """Generate send message script (Base64 encoded)"""
    safe_msg = message_text.replace("'", "''")
    safe_msg = safe_msg.replace('\n', ' ').replace('\r', '')
    script = f"""Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Clipboard]::SetText('{safe_msg}')
Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait('^v')
Start-Sleep -Milliseconds 1000
[System.Windows.Forms.SendKeys]::SendWait('{{ENTER}}')
Write-Output 'SENT'
"""
    return base64.b64encode(script.encode('utf-16-le')).decode('ascii')


# ========== Message File Processing ==========

def load_messages(filepath):
    """
    Load message file. Supports:
    1. Array: [{"brand": "X", "phone": "X", "message": "X"}, ...]
    2. Template+vars: {"template": "...", "contacts": [...], ...}
    Returns unified list: [{"brand": "X", "phone": "X", "message": "X"}, ...]
    """
    with open(filepath, 'r', encoding="utf-8-sig") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict) and 'template' in data and 'contacts' in data:
        template = data['template']
        defaults = {k: v for k, v in data.items() if k not in ('template', 'contacts')}
        messages = []
        for contact in data['contacts']:
            variables = {**defaults, **contact}
            msg = template
            for key, value in variables.items():
                if isinstance(value, str):
                    msg = msg.replace('{' + key + '}', str(value))
            messages.append({
                'brand': contact.get('brand', '?'),
                'phone': contact.get('phone', ''),
                'message': msg
            })
        return messages

    raise ValueError("Unsupported message file format")


# ========== Phone Validation ==========

COUNTRY_CODES = {
    '1': {'name': 'US/Canada', 'length': 11},
    '44': {'name': 'UK', 'length': (12, 13)},
    '33': {'name': 'France', 'length': 11},
    '49': {'name': 'Germany', 'length': (12, 13)},
    '39': {'name': 'Italy', 'length': 12},
    '34': {'name': 'Spain', 'length': 11},
    '61': {'name': 'Australia', 'length': 11},
    '81': {'name': 'Japan', 'length': (11, 12)},
    '86': {'name': 'China', 'length': 13},
    '91': {'name': 'India', 'length': 12},
    '55': {'name': 'Brazil', 'length': (12, 13)},
    '82': {'name': 'Korea', 'length': (11, 12)},
}

def normalize_phone(phone):
    """Digits only (drops +, spaces, dashes, brackets). Used for duplicate detection."""
    return re.sub(r"\D", "", str(phone or ""))


def validate_phone(phone):
    """Validate phone format, returns (is_valid, hint).

    Reports every problem at once: formatting characters AND wrong length,
    so a number like '+44 79' is flagged as both, not just 'remove the +'.
    """
    phone = str(phone or "").strip()
    if not phone:
        return False, "Phone is empty"
    problems = []
    if '+' in phone:
        problems.append("contains '+', remove it")
    if ' ' in phone:
        problems.append("contains spaces, remove them")
    digits = normalize_phone(phone)
    if re.search(r"[^\d+\s\-()]", phone):
        problems.append("contains non-digit characters")
    elif digits != phone.replace('+', '').replace(' ', ''):
        problems.append("contains '-' or brackets, remove them")

    if not digits:
        return False, "; ".join(problems + ["no digits found"])

    length_note = None
    for code, info in COUNTRY_CODES.items():
        if digits.startswith(code):
            expected = info['length']
            actual = len(digits)
            ok_len = actual in expected if isinstance(expected, tuple) else actual == expected
            if not ok_len:
                problems.append(f"{info['name']} length wrong: expected {expected} digits, got {actual}")
            length_note = info['name']
            break
    else:
        # E.164 allows at most 15 digits; anything under 8 cannot be a real mobile number
        if not 8 <= len(digits) <= 15:
            problems.append(f"length {len(digits)} is outside the E.164 range (8-15 digits)")

    if problems:
        return False, f"{phone}: " + "; ".join(problems)
    if length_note:
        return True, f"{length_note} format OK"
    return True, "Format OK (unknown country code, length within E.164 range)"


def _placeholders(text):
    """Same placeholder rule as the email senders (config.PLACEHOLDER_RE)."""
    try:
        import config as _c
        return _c.find_placeholder_text(text)
    except Exception:
        return re.findall(r"<[A-Za-z][^<>@\n]{1,60}>|\{[A-Za-z_][A-Za-z0-9_]{1,40}\}", text or "")


def check_messages(messages):
    """Run every pre-send check on a message list.

    Returns a list of human-readable issues (empty list = safe to proceed).
    Checks: phone format/length, empty message, unfilled <...>/{...} placeholders, and DUPLICATE recipients
    (the same number appearing more than once would message one buyer twice).
    """
    issues = []
    seen = {}
    for i, msg in enumerate(messages):
        brand = msg.get('brand', '?')
        phone = msg.get('phone', '')
        ok, hint = validate_phone(phone)
        if not ok:
            issues.append(f"#{i+1} {brand}: {hint}")
        text = str(msg.get('message', ''))
        if not text.strip():
            issues.append(f"#{i+1} {brand}: message is empty")
        leftover = _placeholders(text)
        if leftover:
            issues.append(f"#{i+1} {brand}: unfilled placeholder(s) {', '.join(leftover)} — "
                          "replace with real values before sending")
        key = normalize_phone(phone)
        if key:
            if key in seen:
                j, other = seen[key]
                issues.append(f"#{i+1} {brand}: DUPLICATE number {key} — already used by #{j+1} {other}; "
                              "remove one so the same buyer is not messaged twice")
            else:
                seen[key] = (i, brand)
    return issues


# ========== Progress Management ==========

def load_progress():
    """Load send progress"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding="utf-8-sig") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None
    return None

def save_progress(total, sent, skipped, last_index):
    """Save send progress. sent can be list of strings or list of dicts with phone+brand."""
    progress = {
        'total': total,
        'sent': sent,
        'skipped': skipped,
        'last_index': last_index,
        'timestamp': __import__('datetime').datetime.now().isoformat()
    }
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, 'w', encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def clear_progress():
    """Clear progress file"""
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


# ========== New Commands: Audit & Harness ==========

def cmd_audit(args):
    """Generate audit PowerShell script"""
    require_profile()
    # Save .ps1 to workspace
    script_path = os.path.join(os.path.dirname(__file__), "wa_audit.ps1")
    with open(script_path, 'w', encoding="utf-8") as f:
        f.write(_render_ps(AUDIT_PS1))
    print(f"✅ Audit script saved to: {script_path}")
    print()
    print("Usage:")
    print('  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + os.path.join(SCRIPT_DIR, 'wa_audit.ps1') + '"')
    print()
    print("With custom paths:")
    print('  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + os.path.join(SCRIPT_DIR, 'wa_audit.ps1')
          + '" -ProgressFile "' + PROGRESS_FILE
          + '" -MessageFile "' + os.path.join(MSG_DIR, 'contacts.json') + '" -StartFrom 1')
    print("  1. Upload wa_audit.ps1 to your Windows device (e.g. via file_to_url)")
    print("  2. Execute it on the Windows device running WhatsApp Desktop")
    print("  3. Screenshots saved to " + os.path.join(SCREENSHOT_DIR, "audit_*.png"))
    print("  4. Upload screenshots + read_image to verify each chat window")
    print("  5. Compare phone number in screenshot header with progress record")

def cmd_harness(args):
    """Generate harness PowerShell script.

    Usage: harness [message_file.json]
    Refuses to run before onboarding. If a message file is given, it must pass
    every check in check_messages() (incl. duplicate numbers) first.
    """
    require_profile()
    if args:
        try:
            messages = load_messages(args[0])
        except Exception as e:
            print(f"❌ File read failed: {e}")
            sys.exit(1)
        issues = check_messages(messages)
        if issues:
            print(f"REFUSED: {args[0]} has {len(issues)} issue(s); fix them first:")
            for e in issues:
                print(f"  • {e}")
            sys.exit(1)
        print(f"✅ {args[0]}: {len(messages)} messages passed all pre-send checks")
    # Save .ps1 to workspace
    script_path = os.path.join(os.path.dirname(__file__), "wa_harness.ps1")
    with open(script_path, 'w', encoding="utf-8") as f:
        f.write(_render_ps(HARNESS_PS1))
    print(f"✅ Harness script saved to: {script_path}")
    print()
    print("Usage:")
    print('  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + os.path.join(SCRIPT_DIR, 'wa_harness.ps1')
          + '" -TestPhone <your-own-test-phone-E164> -MessageFile "' + os.path.join(MSG_DIR, 'contacts.json') + '" -Count 3')
    print("Workflow:")
    print("  1. Upload wa_harness.ps1 to your Windows device (e.g. via file_to_url)")
    print("  2. Execute it with YOUR OWN WhatsApp number as TestPhone")
    print("  3. Messages sent to YOUR phone - verify content/format looks correct")
    print("  4. Screenshots: harness_N_before/pasted/sent.png")
    print("  5. If format confirmed, proceed with real batch send")


# ========== Legacy Commands ==========

def cmd_screenshot():
    require_profile()
    print(generate_screenshot_script())

def _today():
    import datetime
    return datetime.date.today().isoformat()


def load_daily_count():
    try:
        with open(DAILY_COUNT_FILE, encoding="utf-8-sig") as f:
            d = json.load(f)
        return int(d.get(_today(), 0))
    except (OSError, ValueError, json.JSONDecodeError):
        return 0


def bump_daily_count():
    d = {}
    try:
        with open(DAILY_COUNT_FILE, encoding="utf-8-sig") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        d = {}
    d = {k: v for k, v in d.items() if k >= _today()[:7]}   # keep the current month only, so the file does not grow forever
    d[_today()] = int(d.get(_today(), 0)) + 1
    os.makedirs(os.path.dirname(DAILY_COUNT_FILE), exist_ok=True)
    with open(DAILY_COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f)
    return d[_today()]


PACING_FILE = os.path.join(LOG_DIR, "wa_pacing.json")


def enforce_pacing(sent_today):
    """Anti-ban pacing (same as wa_bulk_guide.md section 10): random 8–15 s between messages; every 5 messages a random 30–60 s cooldown.
    If not enough time has passed since the last message, wait here before generating the next one. WA_PACING=0 is for tests only."""
    if os.environ.get("WA_PACING", "1") == "0":
        return 0.0
    try:
        with open(PACING_FILE, encoding="utf-8-sig") as f:
            last = float(json.load(f).get("last_ts", 0))
    except (OSError, ValueError, json.JSONDecodeError):
        last = 0.0
    gap = random.uniform(30, 60) if sent_today and sent_today % 5 == 0 else random.uniform(8, 15)
    wait = max(0.0, gap - (time.time() - last)) if last else 0.0
    if wait:
        print(f"# pacing: waiting {wait:.0f}s before this contact"
              + (" (5-contact cooldown)" if sent_today % 5 == 0 else ""), file=sys.stderr)
        time.sleep(wait)
    return wait


def _mark_sent_time():
    os.makedirs(os.path.dirname(PACING_FILE), exist_ok=True)
    with open(PACING_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_ts": time.time()}, f)


def cmd_send(args):
    if not args:
        print("Usage: python3 wa_bulk_sender.py send <message>")
        sys.exit(1)
    require_profile()
    used = load_daily_count()
    if used >= DAILY_LIMIT:
        print(f"STOP: daily limit reached ({used}/{DAILY_LIMIT}). Resume tomorrow; report to the user.")
        sys.exit(3)
    enforce_pacing(used)
    print(generate_send_script(' '.join(args)))
    _mark_sent_time()
    n = bump_daily_count()
    print(f"# daily count: {n}/{DAILY_LIMIT}", file=sys.stderr)

# ========== Convert (CSV / Excel / wa_targets.json → contacts JSON) ==========

_COL_ALIASES = {
    "phone": ("phone", "电话", "手机", "号码", "whatsapp", "wa", "wa_number", "mobile"),  # Chinese aliases kept for imported sheets
    "brand": ("brand", "品牌", "公司", "company", "name", "客户名", "customer"),
    "message": ("message", "消息", "内容", "开发信", "msg"),
    "intro": ("intro", "开场", "开场白"),
}


def _map_columns(header):
    out = {}
    low = [str(h or "").strip().lower() for h in header]
    for field, names in _COL_ALIASES.items():
        for i, h in enumerate(low):
            if h in names:
                out[field] = i
                break
    return out


def _rows_from_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        import csv
        with open(path, newline="", encoding="utf-8-sig") as f:
            return [r for r in csv.reader(f)]
    if ext in (".xlsx", ".xlsm"):
        try:
            import openpyxl  # optional; the rest of the kit stays stdlib-only
        except ImportError:
            raise SystemExit("❌ Reading .xlsx needs openpyxl (pip install openpyxl), "
                             "or save the sheet as CSV and convert the CSV.")
        ws = openpyxl.load_workbook(path, read_only=True, data_only=True).active
        return [["" if c is None else str(c) for c in row] for row in ws.iter_rows(values_only=True)]
    if ext == ".json":
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        items = data.get("pending", data.get("contacts", [])) if isinstance(data, dict) else data
        header = ["brand", "phone", "intro", "message"]
        rows = [header]
        for it in items:
            rows.append([it.get("brand", ""), it.get("phone") or it.get("whatsapp") or it.get("wa_number", ""),
                         it.get("intro", ""), it.get("message", "")])
        return rows
    raise SystemExit(f"❌ Unsupported input type: {ext} (use .csv / .xlsx / wa_targets.json)")


def cmd_convert(args):
    """CSV / Excel / wa_targets.json → contacts JSON (Format A if a message column exists, else Format B)."""
    if not args:
        print("Usage: python3 wa_bulk_sender.py convert <customers.csv|.xlsx|wa_targets.json> [out.json]")
        sys.exit(1)
    src = args[0]
    out = args[1] if len(args) > 1 else os.path.splitext(src)[0] + "_wa.json"
    rows = [r for r in _rows_from_file(src) if any(str(c).strip() for c in r)]
    if not rows:
        print("❌ Empty input")
        sys.exit(1)
    cols = _map_columns(rows[0])
    if "phone" not in cols:
        print("❌ No phone column found (accepted: " + " / ".join(_COL_ALIASES["phone"]) + ")")
        sys.exit(1)
    contacts, skipped = [], 0
    for r in rows[1:]:
        get = lambda k: (str(r[cols[k]]).strip() if k in cols and cols[k] < len(r) else "")
        phone = re.sub(r"[^0-9]", "", get("phone"))
        if not phone:
            skipped += 1
            continue
        c = {"brand": get("brand") or "?", "phone": phone}
        if get("message"):
            c["message"] = get("message")
        if get("intro"):
            c["intro"] = get("intro")
        contacts.append(c)
    if contacts and all("message" in c for c in contacts):
        data = contacts                                   # Format A
    else:
        data = {"template": "<write your template with {brand} {intro}>",
                "contacts": [{k: v for k, v in c.items() if k != "message"} for c in contacts]}  # Format B
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    fmt = "Format A (per-row message)" if isinstance(data, list) else "Format B (template + contacts; fill the template)"
    print(f"✅ {len(contacts)} contacts → {out}  [{fmt}]  skipped(no phone): {skipped}")
    print("Next: validate → preview → harness (nothing is sent by convert).")


def cmd_validate(args):
    if not args:
        print("Usage: python3 wa_bulk_sender.py validate <file>")
        sys.exit(1)
    try:
        messages = load_messages(args[0])
    except Exception as e:
        print(f"❌ File read failed: {e}")
        sys.exit(1)

    print(f"Total: {len(messages)} messages")
    issues = check_messages(messages)
    if issues:
        print(f"⚠ Found {len(issues)} issues — fix them before harness/send:")
        for e in issues:
            print(f"  • {e}")
        sys.exit(1)
    print("✅ All passed (format, length, non-empty, no duplicate numbers)")


def cmd_preview(args):
    if not args:
        print("Usage: python3 wa_bulk_sender.py preview <file>")
        sys.exit(1)
    try:
        messages = load_messages(args[0])
    except Exception as e:
        print(f"❌ File read failed: {e}")
        sys.exit(1)

    dup_index = {}
    for i, msg in enumerate(messages):
        dup_index.setdefault(normalize_phone(msg.get('phone', '')), []).append(i + 1)

    print(f"Total: {len(messages)} messages:")
    for i, msg in enumerate(messages):
        phone = msg.get('phone', '?')
        ok, hint = validate_phone(phone)
        same = [n for n in dup_index.get(normalize_phone(phone), []) if n != i + 1]
        if same:
            ok = False
            hint = f"{hint}; DUPLICATE of #{', #'.join(map(str, same))}"
        status = "✅" if ok else "⚠"
        print(f"  {i+1}. {status} {msg.get('brand', '?')} → {phone} ({hint})")
        m = msg.get('message', '')
        if len(m) > 80:
            m = m[:80] + "..."
        print(f"      {m}")
    issues = check_messages(messages)
    if issues:
        print(f"\n⚠ {len(issues)} issue(s). Run `validate` for the full list; harness/send will refuse this file.")
        sys.exit(1)


def cmd_progress(args):
    """View/clear send progress"""
    if args and args[0] == 'clear':
        clear_progress()
        print("Progress cleared")
        return
    p = load_progress()
    if p:
        sent_count = len(p.get('sent', []))
        skipped_count = len(p.get('skipped', []))
        ts = p.get('timestamp', 'unknown')
        print(f"Progress: total={p['total']}, sent={sent_count}, skipped={skipped_count}, last_index={p['last_index']}, time={ts}")
    else:
        print("No progress record")
    print(f"Today: {load_daily_count()}/{DAILY_LIMIT} sends (wa_daily_count.json)")

def _proof(prof):
    """One verifiable fact for the demo: offer.key_facts (any industry) > legacy product.moq > placeholder."""
    if prof:
        try:
            import config as _c
            facts = _c.offer_facts(prof, limit=1)
            if facts:
                return facts[0] + "."
        except Exception:
            pass
    return "<one verifiable fact from offer.key_facts>"


def cmd_template(args):
    """Demo template substitution"""
    # Values come from YOUR onboarding profile when it is ready; otherwise neutral
    # <placeholders>. Nothing about country, founding year, MOQ, pricing or industry is assumed.
    prof = None
    try:
        import config as _cfg
        prof = _cfg.load_profile(require_complete=False)
    except Exception:
        prof = None

    def pv(dotted, placeholder):
        if not prof:
            return placeholder
        try:
            return _cfg.get(prof, dotted, placeholder)
        except Exception:
            return placeholder

    sample = {
        "template": "Hi {brand} team! {intro} We're {company} — {product}. {proof} {website}",
        "company": pv("company.brand_display", "<your-brand>"),
        "product": pv("product.one_liner_en", "<your one-line product positioning>"),
        "proof": _proof(prof),
        "website": pv("company.website", "<your-website>"),
        "contacts": [
            {"brand": "Acme Corp", "phone": "12125551234", "intro": "<one specific line about their recent news/project/post>"},
            {"brand": "Musterfirma GmbH", "phone": "4915100000001", "intro": "<one specific line about their recent news/project/post>"}
        ]
    }
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(sample, f, ensure_ascii=False)
        tmppath = f.name
    messages = load_messages(tmppath)
    os.unlink(tmppath)
    print("Template substitution demo (values from your profile; <...> = not filled yet):")
    for msg in messages:
        print(f"\n→ {msg['brand']} ({msg['phone']})")
        print(f"  {msg['message']}")


def main():
    if len(sys.argv) < 2:
        print("WA Bulk Sender - generic B2B kit")
        print("\nCommands:")
        print("  screenshot              Generate screenshot script (Base64)")
        print("  send <message>          Generate send message script (Base64)")
        print("  convert <in> [out.json] CSV / .xlsx / wa_targets.json -> contacts JSON (never sends)")
        print("  validate <file>         Validate message JSON file")
        print("  preview <file>          Preview messages + phone validation")
        print("  progress                View send progress")
        print("  progress clear          Clear progress")
        print("  template                Demo template substitution")
        print("  audit                   Generate post-send audit script")
        print("  harness [file]          Generate pre-send dry-run script (checks file first if given)")
        print("\nRead-only commands work before onboarding; screenshot/send/harness/audit require a")
        print("complete, user-confirmed config/company_profile.json.")
        return

    commands = {
        'screenshot': lambda a: cmd_screenshot(),
        'send': cmd_send,
        'convert': cmd_convert,
        'validate': cmd_validate,
        'preview': cmd_preview,
        'progress': cmd_progress,
        'template': lambda a: cmd_template(a),
        'audit': lambda a: cmd_audit(a),
        'harness': lambda a: cmd_harness(a),
    }

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd in commands:
        commands[cmd](args)
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
