param([string]$Docx,[string]$OutputJson)
$ErrorActionPreference='Stop'
$word=New-Object -ComObject Word.Application
$word.Visible=$false
$word.DisplayAlerts=0
try {
    $document=$word.Documents.Open($Docx,$false,$true)
    $dictionary=$word.Languages.Item(2057).ActiveSpellingDictionary
    if ($null -eq $dictionary) { throw 'UK English spelling dictionary unavailable' }
    $document.Content.LanguageID=2057
    $words=@()
    $contexts=@()
    $errorCount=$document.SpellingErrors.Count
    for ($i=1;$i -le $errorCount;$i++) {
        $range=$document.SpellingErrors.Item($i)
        $text=$range.Text.Trim();$words+=$text
        if ($text -in @('its','queues')) {
            $context=$document.Range([Math]::Max(0,$range.Start-80),[Math]::Min($document.Content.End,$range.End+80)).Text
            $contexts+=[PSCustomObject]@{Word=$text;StandaloneCheck=$word.CheckSpelling($text);Context=$context}
        }
    }
    $result=[PSCustomObject]@{Dictionary=$dictionary.Name;LanguageId=2057;Count=$errorCount;Words=@($words | Sort-Object -Unique);OrdinaryWordContexts=$contexts}
    $result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $OutputJson -Encoding UTF8
    $document.Close(0)
    $result | ConvertTo-Json -Depth 4
} finally { $word.Quit() }
