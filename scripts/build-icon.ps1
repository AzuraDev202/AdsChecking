$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$assetDir = Join-Path (Split-Path $PSScriptRoot -Parent) 'adschecking/assets'
New-Item -ItemType Directory -Path $assetDir -Force | Out-Null
$frames = @()
foreach ($size in @(16, 20, 24, 32, 48, 64, 128, 256)) {
    $bitmap = New-Object System.Drawing.Bitmap(($size * 4), ($size * 4))
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.ScaleTransform(($size * 4 / 256.0), ($size * 4 / 256.0))
    $shape = New-Object System.Drawing.Drawing2D.GraphicsPath
    $shape.AddArc(8, 8, 96, 96, 180, 90)
    $shape.AddArc(152, 8, 96, 96, 270, 90)
    $shape.AddArc(152, 152, 96, 96, 0, 90)
    $shape.AddArc(8, 152, 96, 96, 90, 90)
    $shape.CloseFigure()
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml('#126c60'))
    $graphics.FillPath($brush, $shape)
    $letter = New-Object System.Drawing.Pen([System.Drawing.Color]::White, 21)
    $letter.StartCap = $letter.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $letter.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
    $graphics.DrawLines($letter, [System.Drawing.PointF[]]@(
        [System.Drawing.PointF]::new(57, 184), [System.Drawing.PointF]::new(100, 67),
        [System.Drawing.PointF]::new(139, 174)))
    $graphics.DrawLine($letter, 76, 141, 124, 141)
    $check = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml('#a6efd1'), 21)
    $check.StartCap = $check.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $check.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
    $graphics.DrawLines($check, [System.Drawing.PointF[]]@(
        [System.Drawing.PointF]::new(131, 158), [System.Drawing.PointF]::new(156, 183),
        [System.Drawing.PointF]::new(204, 113)))
    $small = New-Object System.Drawing.Bitmap($size, $size)
    $resize = [System.Drawing.Graphics]::FromImage($small)
    $resize.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $resize.DrawImage($bitmap, 0, 0, $size, $size)
    $buffer = New-Object System.IO.MemoryStream
    $small.Save($buffer, [System.Drawing.Imaging.ImageFormat]::Png)
    $frames += ,@{ Size = $size; Bytes = $buffer.ToArray() }
    if ($size -eq 256) { $small.Save((Join-Path $assetDir 'app.png'), [System.Drawing.Imaging.ImageFormat]::Png) }
    $buffer.Dispose(); $resize.Dispose(); $small.Dispose()
    $check.Dispose(); $letter.Dispose(); $brush.Dispose(); $shape.Dispose(); $graphics.Dispose(); $bitmap.Dispose()
}
$stream = [System.IO.File]::Create((Join-Path $assetDir 'app.ico'))
$writer = New-Object System.IO.BinaryWriter($stream)
$writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]$frames.Count)
$offset = 6 + 16 * $frames.Count
foreach ($frame in $frames) {
    $dimension = if ($frame.Size -eq 256) { 0 } else { $frame.Size }
    $writer.Write([byte]$dimension); $writer.Write([byte]$dimension)
    $writer.Write([byte]0); $writer.Write([byte]0)
    $writer.Write([uint16]1); $writer.Write([uint16]32)
    $writer.Write([uint32]$frame.Bytes.Length); $writer.Write([uint32]$offset)
    $offset += $frame.Bytes.Length
}
foreach ($frame in $frames) { $writer.Write([byte[]]$frame.Bytes) }
$writer.Dispose(); $stream.Dispose()
Write-Output 'Created app.ico (8 sizes) and app.png.'
