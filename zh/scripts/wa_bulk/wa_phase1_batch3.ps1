# WA Phase1 - Open chat + screenshot for 10 contacts (no send)
# GDI+ fix: save to $env:TEMP first, then Copy-Item to the screenshot directory

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Override with your own local screenshot folder before running.
$screenshotDir = $env:WA_SCREENSHOT_DIR
if (-not $screenshotDir) { $screenshotDir = Join-Path $env:TEMP "wa_screenshots" }
$tempDir = $env:TEMP

# Placeholder contact list - fill with your OWN verified targets before running.
# Phone format: country code + number, digits only (E.164 without '+'), e.g. "<phone-E164>".
$contacts = @(
    @{Idx=1;  Brand="<customer-name-1>";  Phone="<phone-E164-1>"}
    @{Idx=2;  Brand="<customer-name-2>";  Phone="<phone-E164-2>"}
    @{Idx=3;  Brand="<customer-name-3>";  Phone="<phone-E164-3>"}
    @{Idx=4;  Brand="<customer-name-4>";  Phone="<phone-E164-4>"}
    @{Idx=5;  Brand="<customer-name-5>";  Phone="<phone-E164-5>"}
    @{Idx=6;  Brand="<customer-name-6>";  Phone="<phone-E164-6>"}
    @{Idx=7;  Brand="<customer-name-7>";  Phone="<phone-E164-7>"}
    @{Idx=8;  Brand="<customer-name-8>";  Phone="<phone-E164-8>"}
    @{Idx=9;  Brand="<customer-name-9>";  Phone="<phone-E164-9>"}
    @{Idx=10; Brand="<customer-name-10>"; Phone="<phone-E164-10>"}
)

# ---- Pre-flight guard: refuse placeholders, bad formats and duplicate numbers ----
$seen = @{}
$preflight = @()
foreach ($c in $contacts) {
    $p = [string]$c.Phone
    if ($p -match '[<>]' -or ([string]$c.Brand) -match '[<>]') {
        $preflight += "#$($c.Idx): still a <placeholder> - fill in your own verified contact"
        continue
    }
    if ($p -notmatch '^\d{8,15}$') {
        $preflight += "#$($c.Idx) $($c.Brand): phone '$p' must be 8-15 digits, no + / spaces / dashes"
    }
    if ($seen.ContainsKey($p)) {
        $preflight += "#$($c.Idx) $($c.Brand): DUPLICATE number $p (already #$($seen[$p]))"
    } else {
        $seen[$p] = $c.Idx
    }
}
if ($preflight.Count -gt 0) {
    Write-Output "REFUSED: fix these before running:"
    $preflight | ForEach-Object { Write-Output "  - $_" }
    exit 1
}

Write-Output "=== PHASE 1: Verify $($contacts.Count) contacts ==="

foreach ($c in $contacts) {
    $idx = $c.Idx
    $brand = $c.Brand
    $phone = $c.Phone

    Write-Output "--- #$idx $brand (+$phone) ---"

    # Open chat via whatsapp:// protocol
    Start-Process "whatsapp://send?phone=$phone"
    Start-Sleep -Seconds 4

    # Wait for WhatsApp focus (poll up to 8 seconds)
    $focused = $false
    $focusTitle = ""
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        try {
            $procs = Get-Process -Name WhatsApp.Root -ErrorAction SilentlyContinue
            if ($procs) {
                foreach ($p in $procs) {
                    if ($p.MainWindowTitle -ne '') {
                        $focusTitle = $p.MainWindowTitle
                        $focused = $true
                        break
                    }
                }
            }
        } catch {}
        if ($focused) { break }
        Start-Sleep -Milliseconds 200
    }

    if (-not $focused) {
        Write-Output "SKIP: WhatsApp not focused"
        continue
    }

    # Screenshot: save to TEMP first (GDI+ safe), then copy
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen
    $bmp = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)

    $tempFile = Join-Path $tempDir "wa_verify_${idx}.png"
    $destFile = Join-Path $screenshotDir "phase1_${idx}_${phone}.png"

    try {
        $bmp.Save($tempFile, [System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose()
        $bmp.Dispose()
        Copy-Item -Path $tempFile -Destination $destFile -Force
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        Write-Output "OK: phase1_${idx}_${phone}.png"
    } catch {
        Write-Output "ERROR: Screenshot failed - $_"
        $g.Dispose()
        $bmp.Dispose()
    }

    # Delay between contacts
    Start-Sleep -Milliseconds 500
}

Write-Output "=== PHASE 1 COMPLETE ==="
