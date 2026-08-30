$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Get-Listener([int]$port) {
  $listener = [System.Net.HttpListener]::new()
  $listener.Prefixes.Add("http://127.0.0.1:$port/")
  $listener.Start()
  return $listener
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
