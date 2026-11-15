param([string]$Docx,[string]$Pdf)
$ErrorActionPreference='Stop'
$word=New-Object -ComObject Word.Application
$word.Visible=$false
$word.DisplayAlerts=0
try {
 $d=$word.Documents.Open($Docx,$false,$true)
 $d.Fields.Update() | Out-Null
 $d.Repaginate()
 Write-Output ('pages='+$d.ComputeStatistics(2)+' words='+$d.ComputeStatistics(0))
 $d.ExportAsFixedFormat($Pdf,17,$false,0,0,1,1,0,$true,$true,0,$true,$true,$true)
 $d.Close(0)
} finally {$word.Quit()}

