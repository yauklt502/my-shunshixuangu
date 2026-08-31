$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Get-Listener([int]$port) {
  $listener = [System.Net.HttpListener]::new()
  $listener.Prefixes.Add("http://127.0.0.1:$port/")
  $listener.Start()
  return $listener
}

function Write-Bytes($ctx, [int]$status, [string]$contentType, [byte[]]$bytes) {
  $ctx.Response.StatusCode = $status
  $ctx.Response.ContentType = $contentType
  $ctx.Response.AddHeader("Cache-Control", "no-store")
  $ctx.Response.AddHeader("Access-Control-Allow-Origin", "*")
  $ctx.Response.AddHeader("Access-Control-Allow-Headers", "Content-Type")
  $ctx.Response.AddHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
  $ctx.Response.ContentLength64 = $bytes.Length
  if ($bytes.Length -gt 0) {
    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
  }
  $ctx.Response.Close()
}

function Write-Json($ctx, [int]$status, [string]$json) {
  Write-Bytes $ctx $status "application/json; charset=utf-8" ([Text.Encoding]::UTF8.GetBytes($json))
}

function Sanitize-FileName([string]$name) {
  if ([string]::IsNullOrWhiteSpace($name)) { return "" }
  $clean = $name
  foreach ($ch in [IO.Path]::GetInvalidFileNameChars()) {
    $clean = $clean.Replace([string]$ch, "_")
  }
  return $clean
}

function Invoke-SaveScreenshot($ctx) {
  $req = $ctx.Request
  if ($req.HttpMethod -eq "OPTIONS") {
    Write-Bytes $ctx 204 "text/plain" ([byte[]]@())
    return
  }
  if ($req.HttpMethod -ne "POST") {
    Write-Json $ctx 405 '{"ok":false,"error":"method not allowed"}'
    return
  }
  try {
    $reader = New-Object System.IO.StreamReader($req.InputStream, [Text.Encoding]::UTF8)
    $body = $reader.ReadToEnd()
    $reader.Close()
    if ([string]::IsNullOrWhiteSpace($body)) {
      Write-Json $ctx 400 '{"ok":false,"error":"empty body"}'
      return
    }
    $obj = $body | ConvertFrom-Json
    $data = [string]$obj.data
    $filename = [string]$obj.filename
    if ([string]::IsNullOrWhiteSpace($data)) {
      Write-Json $ctx 400 '{"ok":false,"error":"missing image data"}'
      return
    }
    $b64 = $data
    if ($b64 -match "^data:image/png;base64,(.+)$") {
      $b64 = $matches[1]
    }
    $filename = [IO.Path]::GetFileName((Sanitize-FileName $filename))
    if ([string]::IsNullOrWhiteSpace($filename)) {
      $filename = "lt88_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".png"
    }
    if (-not $filename.ToLowerInvariant().EndsWith(".png")) {
      $filename += ".png"
    }
    $day = $null
    if ($filename -match "(\d{8})") { $day = $matches[1] }
    if ([string]::IsNullOrWhiteSpace($day)) { $day = Get-Date -Format "yyyyMMdd" }
    $dir = Join-Path $root "screenshots"
    $dayDir = Join-Path $dir $day
    if (-not (Test-Path -LiteralPath $dayDir)) {
      New-Item -ItemType Directory -Path $dayDir -Force | Out-Null
    }
    $full = Join-Path $dayDir $filename
    [IO.File]::WriteAllBytes($full, [Convert]::FromBase64String($b64))
    $payload = @{ ok = $true; path = $full; filename = $filename } | ConvertTo-Json -Compress
    Write-Json $ctx 200 $payload
  } catch {
    $msg = $_.Exception.Message
    $json = '{"ok":false,"error":' + ($msg | ConvertTo-Json -Compress) + '}'
    Write-Json $ctx 500 $json
  }
}

$port = 3001
$listener = $null
foreach ($tryPort in 3001..3003) {
  try {
    $listener = Get-Listener $tryPort
    $port = $tryPort
    break
  } catch {}
}
if (-not $listener) {
  Write-Host "Cannot bind port 3001-3003"
  exit 1
}

Write-Host "LongTou 88 at http://127.0.0.1:$port/"
Start-Process "http://127.0.0.1:$port/"

$mime = @{
  ".html" = "text/html; charset=utf-8"
  ".js"   = "application/javascript; charset=utf-8"
  ".css"  = "text/css; charset=utf-8"
  ".json" = "application/json; charset=utf-8"
  ".png"  = "image/png"
}

try {
  while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $path = $ctx.Request.Url.LocalPath
    if ($path -eq "/save-screenshot") {
      Invoke-SaveScreenshot $ctx
      continue
    }
    if ([string]::IsNullOrWhiteSpace($path) -or $path -eq "/") { $path = "/index.html" }
    $relative = $path.TrimStart("/").Replace("/", [IO.Path]::DirectorySeparatorChar)
    $full = [IO.Path]::GetFullPath((Join-Path $root $relative))
    $rootFull = [IO.Path]::GetFullPath($root) + [IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase) -and $full -ne [IO.Path]::GetFullPath($root)) {
      $ctx.Response.StatusCode = 403
      $ctx.Response.Close()
      continue
    }
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
      $ctx.Response.StatusCode = 404
      $bytes = [Text.Encoding]::UTF8.GetBytes("not found")
      $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
      $ctx.Response.Close()
      continue
    }
    $ext = [IO.Path]::GetExtension($full).ToLowerInvariant()
    $ctx.Response.ContentType = $(if ($mime.ContainsKey($ext)) { $mime[$ext] } else { "application/octet-stream" })
    $data = [IO.File]::ReadAllBytes($full)
    $ctx.Response.ContentLength64 = $data.Length
    $ctx.Response.AddHeader("Cache-Control", "no-store")
    $ctx.Response.OutputStream.Write($data, 0, $data.Length)
    $ctx.Response.Close()
  }
} finally {
  if ($listener -and $listener.IsListening) { $listener.Stop() }
}
