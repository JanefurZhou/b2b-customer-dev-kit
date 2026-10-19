
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

$screenshotDir = $(if ($env:WA_SCREENSHOT_DIR) { $env:WA_SCREENSHOT_DIR } else { Join-Path $env:TEMP "wa_screenshots" })
$msgDir = $(if ($env:WA_MESSAGE_DIR) { $env:WA_MESSAGE_DIR } else { Join-Path $env:TEMP "wa_messages" })
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
