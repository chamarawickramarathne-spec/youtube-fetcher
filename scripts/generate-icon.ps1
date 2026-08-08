$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$root = Split-Path -Parent $PSScriptRoot
$mediaDir = Join-Path $root 'media'
New-Item -ItemType Directory -Force -Path $mediaDir | Out-Null

function New-RoundedRectPath([int]$x, [int]$y, [int]$w, [int]$h, [int]$r) {
  $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
  $d = $r * 2
  $path.AddArc($x, $y, $d, $d, 180, 90)
  $path.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
  $path.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
  $path.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
  $path.CloseFigure()
  return $path
}

function New-MasterIcon([int]$size) {
  $bmp = [System.Drawing.Bitmap]::new($size, $size)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAlias

  $s = $size / 1024.0
  function S([double]$v) { return [int][math]::Round($v * $s) }

  # Dark rounded-square background (vertical gradient)
  $bgRect = [System.Drawing.Rectangle]::new(0, 0, $size, $size)
  $bgPath = New-RoundedRectPath 0 0 $size $size (S 230)
  $bgGrad = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
    $bgRect, [System.Drawing.Color]::FromArgb(255, 30, 34, 46), [System.Drawing.Color]::FromArgb(255, 11, 14, 20), 90.0)
  $g.FillPath($bgGrad, $bgPath)
  $bgGrad.Dispose()

  # Subtle red accent ring
  $accentPath = New-RoundedRectPath (S 48) (S 48) (S 928) (S 928) (S 190)
  $accentPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(60, 220, 38, 38), (S 10))
  $g.DrawPath($accentPen, $accentPath)
  $accentPen.Dispose()

  # Red circle
  $cx = S 512; $cy = S 512; $cr = S 310
  $circleRect = [System.Drawing.Rectangle]::new(($cx - $cr), ($cy - $cr), ($cr * 2), ($cr * 2))
  $circlePath = [System.Drawing.Drawing2D.GraphicsPath]::new()
  $circlePath.AddEllipse($circleRect)
  $circleGrad = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
    $circleRect, [System.Drawing.Color]::FromArgb(255, 247, 63, 63), [System.Drawing.Color]::FromArgb(255, 181, 14, 28), 45.0)
  $g.FillPath($circleGrad, $circlePath)
  $circleGrad.Dispose()

  # White play triangle
  $tri = [System.Drawing.PointF[]]::new(3)
  $tri[0] = [System.Drawing.PointF]::new((S 716), (S 472))
  $tri[1] = [System.Drawing.PointF]::new((S 466), (S 388))
  $tri[2] = [System.Drawing.PointF]::new((S 466), (S 556))
  $white = [System.Drawing.Brushes]::White
  $g.FillPolygon($white, $tri)

  # White download arrow (shaft, head, base bar)
  $g.FillRectangle($white, (S 500), (S 560), (S 24), (S 72))
  $head = [System.Drawing.PointF[]]::new(3)
  $head[0] = [System.Drawing.PointF]::new((S 512), (S 676))
  $head[1] = [System.Drawing.PointF]::new((S 460), (S 622))
  $head[2] = [System.Drawing.PointF]::new((S 564), (S 622))
  $g.FillPolygon($white, $head)
  $g.FillRectangle($white, (S 448), (S 676), (S 128), (S 26))

  $g.Dispose()
  return $bmp
}

# PNG outputs
$master = New-MasterIcon 1024
$master.Save((Join-Path $mediaDir 'icon-1024.png'), [System.Drawing.Imaging.ImageFormat]::Png)
$png512 = [System.Drawing.Bitmap]::new(512, 512)
$g512 = [System.Drawing.Graphics]::FromImage($png512)
$g512.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g512.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g512.DrawImage($master, [System.Drawing.Rectangle]::new(0, 0, 512, 512))
$g512.Dispose()
$png512.Save((Join-Path $mediaDir 'icon.png'), [System.Drawing.Imaging.ImageFormat]::Png)
$png512.Dispose()

# Multi-size ICO (PNG-compressed frames, Vista+)
$sizes = @(256, 128, 64, 48, 32, 24, 16)
$frames = @{}
foreach ($sz in $sizes) {
  $frame = [System.Drawing.Bitmap]::new($sz, $sz)
  $gf = [System.Drawing.Graphics]::FromImage($frame)
  $gf.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $gf.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $gf.DrawImage($master, [System.Drawing.Rectangle]::new(0, 0, $sz, $sz))
  $gf.Dispose()
  $frames[$sz] = $frame
}
$master.Dispose()

$icoPath = Join-Path $mediaDir 'icon.ico'
$fs = [System.IO.File]::Open($icoPath, [System.IO.FileMode]::Create)
$bw = [System.IO.BinaryWriter]::new($fs)
$count = $sizes.Count
$bw.Write([UInt16]0); $bw.Write([UInt16]1); $bw.Write([UInt16]$count)
$offset = 6 + 16 * $count
$dataList = @()
foreach ($sz in $sizes) {
  $ms = [System.IO.MemoryStream]::new()
  $frames[$sz].Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
  $pngBytes = $ms.ToArray()
  $bw.Write([Byte]($sz -band 0xFF)); $bw.Write([Byte]($sz -band 0xFF))
  $bw.Write([Byte]0); $bw.Write([Byte]0)
  $bw.Write([UInt16]1); $bw.Write([UInt16]32)
  $bw.Write([UInt32]$pngBytes.Length); $bw.Write([UInt32]$offset)
  $offset += $pngBytes.Length
  $dataList += ,$pngBytes
  $ms.Dispose(); $frames[$sz].Dispose()
}
foreach ($data in $dataList) { $bw.Write($data) }
$bw.Dispose(); $fs.Dispose()

Write-Output "Generated:"
Get-ChildItem $mediaDir | Select-Object Name, Length
