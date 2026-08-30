$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch {}

$script:TdxReady = $false
$script:TdxError = ""
$script:TdxLoadLock = $false

function Ensure-TdxEngine {
  if ($script:TdxReady) { return }
  if ($script:TdxLoadLock) {
    while ($script:TdxLoadLock -and -not $script:TdxReady) { Start-Sleep -Milliseconds 200 }
    return
  }
  $script:TdxLoadLock = $true
  try {
    $tdxCs = Join-Path $root "TdxEngine.cs"
    if (-not (Test-Path -LiteralPath $tdxCs)) {
      $script:TdxError = "missing TdxEngine.cs"
      return
    }
    $code = [IO.File]::ReadAllText($tdxCs, [Text.Encoding]::UTF8)
    $refs = @("System.dll", "System.Core.dll")
    $compDll = Join-Path ([Runtime.InteropServices.RuntimeEnvironment]::GetRuntimeDirectory()) "System.IO.Compression.dll"
    if (Test-Path -LiteralPath $compDll) { $refs += $compDll }
    Add-Type -TypeDefinition $code -Language CSharp -ReferencedAssemblies $refs
    $script:TdxReady = $true
  } catch {
    if ($_.Exception.Message -match "already exists") {
      $script:TdxReady = $true
    } else {
      $script:TdxError = $_.Exception.Message
    }
  } finally {
    $script:TdxLoadLock = $false
  }
}

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
  $ctx.Response.AddHeader("Access-Control-Allow-Headers", "X-api-key, Content-Type")
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

function Invoke-Tdx($ctx) {
  $req = $ctx.Request
  if ($req.HttpMethod -eq "OPTIONS") {
    Write-Bytes $ctx 204 "text/plain" ([byte[]]@())
    return
  }
  if (-not $script:TdxReady) {
    Ensure-TdxEngine
  }
  if (-not $script:TdxReady) {
    $msg = $script:TdxError
    if ([string]::IsNullOrWhiteSpace($msg)) { $msg = "通达信引擎未加载" }
    $json = '{"ok":false,"tradeDate":"","updatedAt":"","session":"closed","universe":"all","sort":"change","source":"tdx-hq","indices":[],"ztCount":0,"zbCount":0,"sectors":[],"error":' + ('通达信引擎加载失败：' + $msg | ConvertTo-Json -Compress) + '}'
    Write-Json $ctx 200 $json
    return
  }
  $path = $req.Url.LocalPath
  try {
    if ($path -eq "/tdx/status") {
      Write-Json $ctx 200 ([ShunshiTdx.TdxApi]::Status())
      return
    }
    $universe = $req.QueryString["universe"]
    $sort = $req.QueryString["sort"]
    $mode = $req.QueryString["mode"]
    if ([string]::IsNullOrWhiteSpace($mode)) { $mode = $req.QueryString["source"] }
    $vipdoc = $req.QueryString["vipdoc"]
    if ([string]::IsNullOrWhiteSpace($vipdoc)) { $vipdoc = "E:\new_tdx\vipdoc" }
    $date = $req.QueryString["date"]
    Write-Json $ctx 200 ([ShunshiTdx.TdxApi]::Snapshot($universe, $sort, $mode, $vipdoc, $date))
  } catch {
    $err = $_.Exception.Message
    $json = '{"ok":false,"tradeDate":"","indices":[],"ztCount":0,"zbCount":0,"sectors":[],"error":' + ($err | ConvertTo-Json -Compress) + '}'
    Write-Json $ctx 200 $json
  }
}

function Invoke-ThsProxy($ctx) {
  $req = $ctx.Request
  if ($req.HttpMethod -eq "OPTIONS") {
    Write-Bytes $ctx 204 "text/plain" ([byte[]]@())
    return
  }
  $rel = $req.Url.LocalPath.Substring("/ths-api".Length)
  if (-not $rel.StartsWith("/api/")) {
    Write-Bytes $ctx 403 "application/json; charset=utf-8" ([Text.Encoding]::UTF8.GetBytes('{"code":403,"message":"blocked"}'))
    return
  }
  $apiKey = $req.Headers["X-api-key"]
  if ([string]::IsNullOrWhiteSpace($apiKey)) {
    $apiKey = $req.QueryString["key"]
  }
  $upstream = "https://fuyao.aicubes.cn" + $rel + $req.Url.Query
  try {
    $web = [System.Net.HttpWebRequest]::Create($upstream)
    $web.Method = "GET"
    $web.Timeout = 25000
    $web.ReadWriteTimeout = 25000
    $web.UserAgent = "ShunshiWatch/1.0"
    if (-not [string]::IsNullOrWhiteSpace($apiKey)) {
      [void]$web.Headers.Add("X-api-key", $apiKey)
    }
    $resp = $web.GetResponse()
    try {
      $ms = New-Object System.IO.MemoryStream
      $resp.GetResponseStream().CopyTo($ms)
      $bytes = $ms.ToArray()
      $ctype = $resp.ContentType
      if ([string]::IsNullOrWhiteSpace($ctype)) { $ctype = "application/json; charset=utf-8" }
      Write-Bytes $ctx 200 $ctype $bytes
    } finally {
      $resp.Close()
    }
  } catch [System.Net.WebException] {
    $errResp = $_.Exception.Response
    if ($errResp) {
      try {
        $reader = New-Object System.IO.StreamReader($errResp.GetResponseStream())
        $text = $reader.ReadToEnd()
        $status = [int]$errResp.StatusCode
        Write-Bytes $ctx $status "application/json; charset=utf-8" ([Text.Encoding]::UTF8.GetBytes($text))
        return
      } catch {}
    }
    $msg = '{"code":502,"message":"fuyao proxy failed"}'
    Write-Bytes $ctx 502 "application/json; charset=utf-8" ([Text.Encoding]::UTF8.GetBytes($msg))
  }
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
    $filename = [IO.Path]::GetFileName(($filename -replace '[\\/:*?"<>|]', '_'))
    if ([string]::IsNullOrWhiteSpace($filename)) {
      $filename = "shunshi_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".png"
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

$listener = $null
$usedPort = 0
foreach ($port in 3000, 3001, 3002, 5173) {
  try {
    $listener = Get-Listener $port
    $usedPort = $port
    break
  } catch {
    $listener = $null
  }
}

if (-not $listener) {
  Write-Host "Cannot start. Ports 3000-3002 are busy."
  Read-Host "Press Enter to exit"
  exit 1
}

$url = "http://127.0.0.1:$usedPort/"
Start-Process $url
Write-Host "Opened $url"
Write-Host "Keep this window open. Close window = stop the board."

$mime = @{
  ".html" = "text/html; charset=utf-8"
  ".js"   = "text/javascript; charset=utf-8"
  ".css"  = "text/css; charset=utf-8"
  ".txt"  = "text/plain; charset=utf-8"
  ".svg"  = "image/svg+xml"
  ".ico"  = "image/x-icon"
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
    if ($path.StartsWith("/ths-api/")) {
      Invoke-ThsProxy $ctx
      continue
    }
    if ($path.StartsWith("/tdx/")) {
      Invoke-Tdx $ctx
      continue
    }
    if ([string]::IsNullOrWhiteSpace($path) -or $path -eq "/") {
      $path = "/index.html"
    }
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
