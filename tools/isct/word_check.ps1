param([string]$Docx, [string]$Pdf)
$ErrorActionPreference = "Stop"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($Docx, $false, $true)
    $doc.Repaginate()
    $pages = $doc.ComputeStatistics(2)   # wdStatisticPages
    $words = $doc.ComputeStatistics(0)
    "pages=$pages words=$words"
    foreach ($needle in @("Introduction", "Materials and Methods", "Results", "Discussion", "Conclusion", "Disclosure of Interests", "References")) {
        $rng = $doc.Content
        $f = $rng.Find
        $f.MatchCase = $true
        $found = $f.Execute($needle)
        if ($found) { "{0,-26} page {1}" -f $needle, $rng.Information(3) } else { "$needle not found" }
    }
    $last = $doc.Paragraphs.Last.Range
    "last paragraph page: " + $last.Information(3)
    "equations (OMaths): " + $doc.OMaths.Count
    "inline shapes: " + $doc.InlineShapes.Count
    "tables: " + $doc.Tables.Count
    if ($Pdf) { $doc.ExportAsFixedFormat($Pdf, 17); "pdf saved" }
    $doc.Close($false)
} finally {
    $word.Quit()
}
