
# WA Audit - Post-send verification
# Open each sent chat and screenshot for AI verification
param(
    [string]$ProgressFile = $(if ($env:WA_PROGRESS_FILE) { $env:WA_PROGRESS_FILE } else { Join-Path $env:TEMP "wa_progress.json" }),
    [string]$MessageFile = "",
    [int]$StartFrom = 1
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screenshotDir = $(if ($env:WA_SCREENSHOT_DIR) { $env:WA_SCREENSHOT_DIR } else { Join-Path $env:TEMP "wa_screenshots" })
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
            $waProc = Get-Process WhatsApp -ErrorAction SilentlyContinue
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
