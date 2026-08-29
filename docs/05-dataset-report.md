I’ll re-scan the folder now that the downloads are present, identify likely DRAMP and DBAASP files, and inspect their schemas and sample records without editing anything.

Ran terminal command: Get-ChildItem \-Force \-Recurse | Select-Object FullName,Length,LastWriteTime,PSIsContainer

Ran terminal command: Get-ChildItem \-File \-Recurse | Where-Object { $\_.Extension \-in '.csv','.tsv','.xlsx','.xls','.json','.parquet','.zip' } | Select-Object FullName,Extension,Length

Read memory

The folder contains one Excel workbook, \`general\_amps.xlsx\`, plus two CSV files that appear to separate activity and toxicity data. I’m checking workbook sheets, exact headers, types, dimensions, and representative rows next so the report reflects the source structure rather than guessed field names.

Ran terminal command: @'  
import pandas as pd  
from pathlib import Path  
root \= Path('.')  
for path in sorted(root.iterdir()):  
    if path.suffix.lower() not in {'.csv', '.xlsx', '.xls'}:  
        continue  
    print('\\n' \+ '='\*100)  
    print('FILE:', path.name)  
    if path.suffix.lower() in {'.xlsx', '.xls'}:  
        book \= pd.ExcelFile(path)  
        print('SHEETS:', book.sheet\_names)  
        for sheet in book.sheet\_names:  
            df \= pd.read\_excel(path, sheet\_name=sheet)  
            print('\\nSHEET:', sheet)  
            print('ROWS:', len(df), 'COLS:', len(df.columns))  
            print('COLUMNS:', list(df.columns))  
            print('DTYPES:', {str(k): str(v) for k,v in df.dtypes.items()})  
            print('MISSING\_RATE:', {str(k): round(float(v),4) for k,v in df.isna().mean().items()})  
            print('SAMPLE:')  
            print(df.head(3).to\_string(index=False, max\_colwidth=80))  
    else:  
        df \= pd.read\_csv(path, low\_memory=False)  
        print('ROWS:', len(df), 'COLS:', len(df.columns))  
        print('COLUMNS:', list(df.columns))  
        print('DTYPES:', {str(k): str(v) for k,v in df.dtypes.items()})  
        print('MISSING\_RATE:', {str(k): round(float(v),4) for k,v in df.isna().mean().items()})  
        print('SAMPLE:')  
        print(df.head(3).to\_string(index=False, max\_colwidth=80))  
'@ | python \-  
Completed with input: @'  
import pandas as pd  
from pathlib import Path  
root \= Path('.')  
for path in sorted(root.iterdir()):  
    if path.suffix.lower() not in {'.csv', '.xlsx', '.xls'}:  
        continue  
    print('\\n' \+ '='\*100)  
    print('FILE:', path.name)  
    if path.suffix.lower() in {'.xlsx', '.xls'}:  
        book \= pd.ExcelFile(path)  
        print('SHEETS:', book.sheet\_names)  
        for sheet in book.sheet\_names:  
            df \= pd.read\_excel(path, sheet\_name=sheet)  
            print('\\nSHEET:', sheet)  
            print('ROWS:', len(df), 'COLS:', len(df.columns))  
            print('COLUMNS:', list(df.columns))  
            print('DTYPES:', {str(k): str(v) for k,v in df.dtypes.items()})  
            print('MISSING\_RATE:', {str(k): round(float(v),4) for k,v in df.isna().mean().items()})  
            print('SAMPLE:')  
            print(df.head(3).to\_string(index=False, max\_colwidth=80))  
    else:  
        df \= pd.read\_csv(path, low\_memory=False)  
        print('ROWS:', len(df), 'COLS:', len(df.columns))  
        print('COLUMNS:', list(df.columns))  
        print('DTYPES:', {str(k): str(v) for k,v in df.dtypes.items()})  
        print('MISSING\_RATE:', {str(k): round(float(v),4) for k,v in df.isna().mean().items()})  
        print('SAMPLE:')  
        print(df.head(3).to\_string(index=False, max\_colwidth=80))  
'@ | python \-

The files are present, but the environment does not currently expose a Python interpreter, so the first schema probe could not run. I’ll use the available Windows tooling to inspect the CSVs and check whether an Excel-capable utility or PowerShell module is available for the workbook.

Ran terminal command: Get-Command python,python3,py,pwsh,ImportExcel,node \-ErrorAction SilentlyContinue | Select-Object Name,Source,Version  
Completed with input: Get-Command python,python3,py,pwsh,ImportExcel,node \-ErrorAction SilentlyContinue | Select-Object Name,Source,Version

Ran terminal command: Get-ChildItem \-File \*.csv | ForEach-Object { $rows \= Import-Csv $\_.FullName; Write-Output ('FILE: ' \+ $\_.Name); Write-Output ('ROWS: ' \+ $rows.Count); if ($rows.Count \-gt 0\) { Write-Output ('COLUMNS: ' \+ (($rows\[0\].PSObject.Properties.Name) \-join ' | ')); $rows\[0..(\[Math\]::Min(2,$rows.Count-1))\] | Format-List } }

Ran terminal command: Get-Module \-ListAvailable | Where-Object { $\_.Name \-match 'Excel|ImportExcel|EPPlus' } | Select-Object Name,Version,Path

Ran terminal command: Get-Command soffice,libreoffice,excel \-ErrorAction SilentlyContinue | Select-Object Name,Source  
Completed with input: Get-Command soffice,libreoffice,excel \-ErrorAction SilentlyContinue | Select-Object Name,Source

Ran terminal command: Get-ChildItem \*.csv | ForEach-Object { $rows \= @(Import-Csv $\_.FullName); Write-Output ('=== ' \+ $\_.Name); foreach ($col in $rows\[0\].PSObject.Properties.Name) { $missing \= @($rows | Where-Object { \[string\]::IsNullOrWhiteSpace(\[string\]$\_.$col) }).Count; $distinct \= @($rows | ForEach-Object { \[string\]$\_.$col } | Sort-Object \-Unique).Count; Write-Output ('{0}: missing={1}/{2} ({3:N1}%), unique={4}' \-f $col,$missing,$rows.Count,(100\*$missing/$rows.Count),$distinct) }; Write-Output 'ID samples:'; $rows | Select-Object \-ExpandProperty 'Peptide ID' \-Unique | Select-Object \-First 10; Write-Output 'Sequence nonblank samples:'; $rows | Where-Object { \-not \[string\]::IsNullOrWhiteSpace($\_.'Peptide Sequence') } | Select-Object \-ExpandProperty 'Peptide Sequence' \-Unique | Select-Object \-First 10; Write-Output 'Measure samples:'; $rows | Select-Object \-ExpandProperty 'Activity Measure' \-Unique | Select-Object \-First 20; Write-Output 'Unit samples:'; $rows | Select-Object \-ExpandProperty Unit \-Unique | Select-Object \-First 20 }

Ran terminal command: Get-Item general\_amps.xlsx | Format-List FullName,Length,LastWriteTime; $zip=\[System.IO.Compression.ZipFile\]::OpenRead((Resolve-Path general\_amps.xlsx)); $zip.Entries | Select-Object FullName,Length | Sort-Object FullName; $zip.Dispose()  
Completed with input: Get-Item general\_amps.xlsx | Format-List FullName,Length,LastWriteTime; $zip=\[System.IO.Compression.ZipFile\]::OpenRead((Resolve-Path general\_amps.xlsx)); $zip.Entries | Select-Object FullName,Length | Sort-Object FullName; $zip.Dispose()

The CSVs are confirmed as experimental tables: 20,384 activity rows and 1,609 lysis/toxicity rows. The activity samples show blank peptide sequences, which is a critical ambiguity to quantify; I’m narrowing the diagnostics to sequence coverage, duplicate relationships, and the workbook’s actual internal sheet names.

Ran terminal command: Add-Type \-AssemblyName System.IO.Compression.FileSystem; $zip=\[System.IO.Compression.ZipFile\]::OpenRead((Resolve-Path general\_amps.xlsx)); $zip.Entries | Select-Object FullName,Length | Sort-Object FullName; $zip.Dispose()

Ran terminal command: $a=@(Import-Csv activity-against-target-species.csv); $t=@(Import-Csv hemolytic-and-cytotoxic-activities.csv); Write-Output ('Activity rows={0}; IDs={1}; nonblank sequences={2}; unique nonblank sequences={3}' \-f $a.Count,(@($a.'Peptide ID'|Sort-Object \-Unique).Count,(@($a|Where-Object{ \-not \[string\]::IsNullOrWhiteSpace($\_.'Peptide Sequence')}).Count,(@($a|Where-Object{ \-not \[string\]::IsNullOrWhiteSpace($\_.'Peptide Sequence')}|%{$\_.'Peptide Sequence'}|Sort-Object \-Unique).Count)); Write-Output ('Toxicity rows={0}; IDs={1}; nonblank sequences={2}; unique nonblank sequences={3}' \-f $t.Count,(@($t.'Peptide ID'|Sort-Object \-Unique).Count,(@($t|Where-Object{ \-not \[string\]::IsNullOrWhiteSpace($\_.'Peptide Sequence')}).Count,(@($t|Where-Object{ \-not \[string\]::IsNullOrWhiteSpace($\_.'Peptide Sequence')}|%{$\_.'Peptide Sequence'}|Sort-Object \-Unique).Count)); Write-Output 'Activity rows grouped by ID with blank sequence:'; $a | Group-Object 'Peptide ID' | Where-Object { (@($\_.Group|Where-Object{\[string\]::IsNullOrWhiteSpace($\_.'Peptide Sequence')}).Count \-gt 0\) } | Select-Object \-First 10 Name,Count; Write-Output 'Activity measures:'; $a|%{$\_.'Activity Measure'}|Sort-Object \-Unique; Write-Output 'Toxicity measures:'; $t|%{$\_.'Activity Measure for Lysis'}|Sort-Object \-Unique

Ran terminal command: $a=@(Import-Csv activity-against-target-species.csv); $t=@(Import-Csv hemolytic-and-cytotoxic-activities.csv); Write-Output 'Activity units:'; $a|% Unit|Sort-Object \-Unique; Write-Output 'Activity target count:'; (@($a.'Target Species'|Sort-Object \-Unique).Count); $a|Group-Object 'Target Species'|Sort-Object Count \-Descending|Select-Object \-First 15 Name,Count; Write-Output 'Toxicity target cells:'; $t|Group-Object 'Target Cell'|Sort-Object Count \-Descending|Select-Object Name,Count; Write-Output 'Toxicity units:'; $t|% Unit|Sort-Object \-Unique

Read , lines 1 to 180

Ran terminal command: Add-Type \-AssemblyName System.IO.Compression.FileSystem; $zip=\[IO.Compression.ZipFile\]::OpenRead((Resolve-Path general\_amps.xlsx)); foreach($name in @('xl/workbook.xml','xl/sharedStrings.xml','xl/worksheets/sheet1.xml')) { $entry=$zip.GetEntry($name); $reader=\[IO.StreamReader\]::new($entry.Open()); $text=$reader.ReadToEnd(); $reader.Dispose(); Write-Output ('=== '+$name+' chars='+$text.Length); if($name \-ne 'xl/sharedStrings.xml'){ Write-Output $text.Substring(0,\[Math\]::Min(5000,$text.Length)) } else { $xml=\[xml\]$text; Write-Output ('shared\_strings='+$xml.sst.count); $xml.sst.si | Select-Object \-First 40 | ForEach-Object { $\_.InnerText } } }; $zip.Dispose()

Ran terminal command: $files=Get-ChildItem \*.csv; foreach($file in $files){$rows=@(Import-Csv $file.FullName);$cols=$rows\[0\].PSObject.Properties.Name;Write-Output ('=== '+$file.Name+' rows='+$rows.Count);foreach($col in $cols){$vals=@($rows|ForEach-Object{\[string\]($\_.$col)});$nonblank=@($vals|Where-Object{$\_ \-and $\_.Trim()});$missing=$vals.Count-$nonblank.Count;$unique=@($nonblank|Sort-Object \-Unique).Count;Write-Output ('{0} | missing {1} ({2:N1}%) | nonblank\_unique {3}' \-f $col,$missing,(100\*$missing/$rows.Count),$unique)};Write-Output 'nonblank sequence examples:';@($rows|Where-Object{\[string\]$\_.('Peptide Sequence') \-and \[string\]$\_.('Peptide Sequence') \-ne ''}|ForEach-Object{\[string\]$\_.'Peptide Sequence'}|Sort-Object \-Unique|Select-Object \-First 8);Write-Output 'first row:';$rows\[0\]|Format-List}

Ran terminal command: $a=@(Import-Csv activity-against-target-species.csv);$t=@(Import-Csv hemolytic-and-cytotoxic-activities.csv);$aseqs=@($a|ForEach-Object{\[string\]$\_.'Peptide Sequence'}|Where-Object{$\_.Trim()}|ForEach-Object{$\_.Trim().ToUpperInvariant()}|Sort-Object \-Unique);$tseqs=@($t|ForEach-Object{\[string\]$\_.'Peptide Sequence'}|Where-Object{$\_.Trim()}|ForEach-Object{$\_.Trim().ToUpperInvariant()}|Sort-Object \-Unique);Write-Output ('activity unique normalized sequences='+$aseqs.Count);Write-Output ('toxicity unique normalized sequences='+$tseqs.Count);Write-Output ('activity IDs='+(@($a|%{$\_.'Peptide ID'}|Sort-Object \-Unique).Count));Write-Output ('toxicity IDs='+(@($t|%{$\_.'Peptide ID'}|Sort-Object \-Unique).Count));Write-Output ('intersection='+(@(Compare-Object $aseqs $tseqs \-IncludeEqual \-ExcludeDifferent).Count));Write-Output ('activity-only='+(@(Compare-Object $aseqs $tseqs \-PassThru|Where-Object{$\_.SideIndicator \-eq '\<='}).Count));Write-Output ('toxicity-only='+(@(Compare-Object $aseqs $tseqs \-PassThru|Where-Object{$\_.SideIndicator \-eq '=\>'}).Count))

The first reliable matching baseline is now clear for the two CSV tables: 1,743 unique activity sequences, 717 unique toxicity sequences, and 714 exact normalized overlaps. I’m doing the final workbook parse now; the Excel package has one sheet, \`general\_amps\`, with 27 columns and 11,612 data rows, and I’m extracting its actual values and missingness before presenting the complete report.

Ran terminal command: @'  
Add-Type \-AssemblyName System.IO.Compression.FileSystem  
$zip=\[IO.Compression.ZipFile\]::OpenRead((Resolve-Path general\_amps.xlsx))  
function ReadEntry($name){$e=$zip.GetEntry($name);$r=\[IO.StreamReader\]::new($e.Open());$s=$r.ReadToEnd();$r.Dispose();return $s}  
$ss=\[xml\](ReadEntry 'xl/sharedStrings.xml')  
$strings=@($ss.sst.si | ForEach-Object {$\_.InnerText})  
$sheet=\[xml\](ReadEntry 'xl/worksheets/sheet1.xml')  
$rows=@($sheet.worksheet.sheetData.row)  
$headers=@()  
foreach($cell in @($rows\[0\].c)){ $idx=\[int\]$cell.v; $headers \+= $strings\[$idx\] }  
Write-Output ('FILE: general\_amps.xlsx | SHEET: general\_amps | DATA\_ROWS: '+($rows.Count-1)+' | COLUMNS: '+$headers.Count)  
Write-Output ('COLUMNS: '+($headers \-join ' | '))  
$data=@()  
foreach($row in $rows\[1..($rows.Count-1)\]){  
  $obj=\[ordered\]@{}  
  foreach($cell in @($row.c)){  
    $ref=\[string\]$cell.r; $letters=($ref \-replace '\\d',''); $n=0; foreach($ch in $letters.ToCharArray()){$n=$n\*26+(\[int\]\[char\]$ch-64)}; $pos=$n-1  
    $value=''; if($cell.v \-ne $null){$value= if($cell.t \-eq 's'){$strings\[\[int\]$cell.v\]}else{\[string\]$cell.v}}  
    if($pos \-lt $headers.Count){$obj\[$headers\[$pos\]\]=$value}  
  }  
  foreach($h in $headers){if(-not $obj.Contains($h)){$obj\[$h\]=''}}  
  $data \+= \[pscustomobject\]$obj  
}  
Write-Output 'MISSINGNESS:'  
foreach($h in $headers){$vals=@($data|ForEach-Object{\[string\]$\_.$h});$missing=@($vals|Where-Object{\[string\]::IsNullOrWhiteSpace($\_) \-or $\_ \-eq 'NA' \-or $\_ \-eq 'N/A'}).Count;$non=@($vals|Where-Object{ \-not \[string\]::IsNullOrWhiteSpace($\_) \-and $\_ \-ne 'NA' \-and $\_ \-ne 'N/A'});Write-Output ('{0} | missing\_or\_NA={1} ({2:N1}%) | nonmissing\_unique={3}' \-f $h,$missing,(100\*$missing/$data.Count),(@($non|Sort-Object \-Unique).Count))}  
Write-Output 'SAMPLE\_ROWS:'  
$data|Select-Object \-First 3|Format-List  
Write-Output 'SEQUENCE\_STATS:'  
$seq=@($data|% Sequence|Where-Object{$\_ \-and $\_ \-notin @('NA','N/A')}|Sort-Object \-Unique);Write-Output ('unique nonblank Sequence='+$seq.Count);Write-Output ('first sequences='+(($seq|Select-Object \-First 8)-join ', '))  
Write-Output 'KEY CATEGORIES:'  
foreach($h in @('Activity','Hemolytic\_activity','Cytotoxicity','Linear/Cyclic/Branched','N-terminal\_Modification','C-terminal\_Modification','Other\_Modifications','Stereochemistry','Target\_Organism','Pubmed\_ID','Reference')){Write-Output ('--- '+$h);$data|% $h|Where-Object{$\_}|Group-Object|Sort-Object Count \-Descending|Select-Object \-First 12|ForEach-Object{Write-Output ($\_.Count.ToString()+' :: '+$\_.Name)}}  
$zip.Dispose()  
'@ | powershell \-NoProfile \-Command \-

Ran terminal command: @'  
Add-Type \-AssemblyName System.IO.Compression.FileSystem  
$zip=\[IO.Compression.ZipFile\]::OpenRead((Resolve-Path general\_amps.xlsx))  
function E($n){$x=$zip.GetEntry($n);$r=\[IO.StreamReader\]::new($x.Open());$s=$r.ReadToEnd();$r.Dispose();$s}  
$ss=\[xml\](E 'xl/sharedStrings.xml');$strings=@($ss.sst.si|%{$\_.InnerText});$sh=\[xml\](E 'xl/worksheets/sheet1.xml');$rows=@($sh.worksheet.sheetData.row)  
foreach($row in $rows\[0..4\]){Write-Output ('ROW '+$row.r);$out=@();foreach($c in @($row.c)){$v=if($c.t \-eq 's'){$strings\[\[int\]$c.v\]}else{\[string\]$c.v};$out+=(((\[string\]$c.r)+'='+$v))};Write-Output ($out \-join ' || ')}  
$zip.Dispose()  
'@ | powershell \-NoProfile \-Command \-

Read 

Ran terminal command: @'  
Add-Type \-AssemblyName System.IO.Compression.FileSystem  
$zip=\[IO.Compression.ZipFile\]::OpenRead((Resolve-Path general\_amps.xlsx))  
function E($n){$x=$zip.GetEntry($n);$r=\[IO.StreamReader\]::new($x.Open());$s=$r.ReadToEnd();$r.Dispose();$s}  
$ss=\[xml\](E 'xl/sharedStrings.xml');$strings=@($ss.sst.si|%{$\_.InnerText});$sh=\[xml\](E 'xl/worksheets/sheet1.xml');$rows=@($sh.worksheet.sheetData.row);$headers=@($rows\[0\].c|%{$strings\[\[int\]$\_.v\]});$n=$rows.Count-1  
$missing=@{};$sets=@{};foreach($h in $headers){$missing\[$h\]=0;$sets\[$h\]=\[Collections.Generic.HashSet\[string\]\]::new()}  
$seqSet=\[Collections.Generic.HashSet\[string\]\]::new();$idSet=\[Collections.Generic.HashSet\[string\]\]::new()  
foreach($row in $rows\[1..($rows.Count-1)\]){ $vals=@{}; foreach($cell in @($row.c)){ $letters=((\[string\]$cell.r)-replace '\\d','');$col=0;foreach($ch in $letters.ToCharArray()){$col=$col\*26+(\[int\]\[char\]$ch-64)};$v=if($cell.t \-eq 's'){$strings\[\[int\]$cell.v\]}else{\[string\]$cell.v};$vals\[$col-1\]=$v }  
 for($i=0;$i \-lt $headers.Count;$i++){ $v=\[string\]$vals\[$i\];if(\[string\]::IsNullOrWhiteSpace($v)-or $v \-eq 'NA'-or $v \-eq 'N/A'){$missing\[$headers\[$i\]\]++}else{\[void\]$sets\[$headers\[$i\]\].Add($v)}}  
 if($vals\[1\]){\[void\]$seqSet.Add((\[string\]$vals\[1\]).Trim().ToUpperInvariant())};if($vals\[0\]){\[void\]$idSet.Add(\[string\]$vals\[0\])}  
}  
Write-Output ('rows='+$n+' unique\_ids='+$idSet.Count+' unique\_normalized\_sequences='+$seqSet.Count)  
foreach($h in $headers){Write-Output ('{0} | missing={1} ({2:N1}%) | unique\_nonmissing={3}' \-f $h,$missing\[$h\],(100\*$missing\[$h\]/$n),$sets\[$h\].Count)}  
$zip.Dispose()  
'@ | powershell \-NoProfile \-Command \-

The workbook confirms the DRAMP source is \`general\_amps.xlsx\`, sheet \`general\_amps\`, with 11,612 rows and the expected toxicity/modification/reference fields. One important structural issue is that DRAMP stores activity and toxicity mostly as free-text annotations, while DBAASP splits activity into measurement rows; I’m calculating the remaining sequence-level percentages and duplicate counts for the report.

Ran terminal command: $a=@(Import-Csv activity-against-target-species.csv);$t=@(Import-Csv hemolytic-and-cytotoxic-activities.csv);$aseq=@($a|?{$\_.'Peptide Sequence'.Trim()}|%{$\_.'Peptide Sequence'.Trim().ToUpperInvariant()}|sort \-Unique);$tseq=@($t|?{$\_.'Peptide Sequence'.Trim()}|%{$\_.'Peptide Sequence'.Trim().ToUpperInvariant()}|sort \-Unique);$both=@(Compare-Object $aseq $tseq \-IncludeEqual \-ExcludeDifferent);Write-Output ('ACTIVITY unique sequences='+$aseq.Count+' IDs='+(@($a.'Peptide ID'|sort \-Unique).Count));Write-Output ('TOXICITY unique sequences='+$tseq.Count+' IDs='+(@($t.'Peptide ID'|sort \-Unique).Count));Write-Output ('MATCHES='+$both.Count+' DRAMP-like toxicity coverage='+(100\*$both.Count/$tseq.Count).ToString('N2')+'% activity coverage='+(100\*$both.Count/$aseq.Count).ToString('N2')+'%');Write-Output ('ACTIVITY duplicate IDs=' \+ (@($a|group 'Peptide ID'|? Count \-gt 1).Count) \+ '; duplicate sequences=' \+ (@($a|group 'Peptide Sequence'|? Count \-gt 1).Count));Write-Output ('TOXICITY duplicate IDs=' \+ (@($t|group 'Peptide ID'|? Count \-gt 1).Count) \+ '; duplicate sequences=' \+ (@($t|group 'Peptide Sequence'|? Count \-gt 1).Count));Write-Output 'Activity measures:';@($a.'Activity Measure'|?{$\_}|sort \-Unique|select \-First 30);Write-Output 'Toxicity measure examples:';@($t.'Activity Measure for Lysis'|?{$\_}|sort \-Unique|select \-First 30\)

\*\*Inspection Report\*\*

\*\*Files discovered\*\*  
\- \`general\_amps.xlsx\`  
\- \`activity-against-target-species.csv\`  
\- \`hemolytic-and-cytotoxic-activities.csv\`  
\- \`preprocess.py\`, currently empty

\*\*Selected sources\*\*  
\- DRAMP: \`general\_amps.xlsx\`, sheet \`general\_amps\`  
\- DBAASP activity data: \`activity-against-target-species.csv\`  
\- DBAASP toxicity-related data: \`hemolytic-and-cytotoxic-activities.csv\`

\#\# DRAMP schema

Workbook dimensions: \*\*11,612 rows × 27 columns\*\*    
Unique DRAMP IDs: \*\*11,612\*\*    
Unique normalized sequences: not reliably computed because the workbook parser was unavailable for a complete pass, but the workbook contains a \`Sequence\` column.

Columns:

\`DRAMP\_ID\`, \`Sequence\`, \`Sequence\_Length\`, \`Name\`, \`Swiss\_Prot\_Entry\`, \`Family\`, \`Gene\`, \`Source\`, \`Activity\`, \`Protein\_existence\`, \`Structure\`, \`Structure\_Description\`, \`PDB\_ID\`, \`Comments\`, \`Target\_Organism\`, \`Hemolytic\_activity\`, \`Linear/Cyclic/Branched\`, \`N-terminal\_Modification\`, \`C-terminal\_Modification\`, \`Other\_Modifications\`, \`Stereochemistry\`, \`Cytotoxicity\`, \`Binding\_Traget\`, \`Pubmed\_ID\`, \`Reference\`, \`Author\`, \`Title\`

Example DRAMP record:  
\- ID: \`DRAMP00005\`  
\- Sequence: \`SLGPAIKATRQVCPKATRFVTVSCKKSDCQ\`  
\- Activity: \`Antimicrobial, Antibacterial, Anti-Gram+\`  
\- Hemolysis: \`No hemolysis information or data found in the reference(s) presented in this entry\`  
\- Cytotoxicity: \`No cytotoxicity information found\`  
\- Modifications: oxypropionylation, cyclic structure, lanthionine-related annotations  
\- PubMed ID: \`9726851\`

Important DRAMP fields:  
\- Sequence: \`Sequence\`  
\- ID: \`DRAMP\_ID\`  
\- Activity: \`Activity\`  
\- Target/activity context: \`Target\_Organism\`  
\- Hemolysis: \`Hemolytic\_activity\`  
\- Cytotoxicity: \`Cytotoxicity\`  
\- Cell/RBC type: embedded in free-text toxicity annotations and \`Target\_Organism\`  
\- Conditions: primarily \`Comments\`, \`Target\_Organism\`, and references  
\- References: \`Pubmed\_ID\`, \`Reference\`, \`Author\`, \`Title\`  
\- Modifications: \`N-terminal\_Modification\`, \`C-terminal\_Modification\`, \`Other\_Modifications\`, \`Stereochemistry\`, \`Linear/Cyclic/Branched\`

DRAMP activity and toxicity values are largely free-text. There are no dedicated numeric activity-value/unit columns in this workbook.

\#\# DBAASP activity schema

Rows: \*\*20,384\*\*    
Unique peptide IDs: \*\*1,981\*\*    
Unique normalized sequences: \*\*1,743\*\*

Columns:

\`Peptide ID\`, \`Peptide Sequence\`, \`Target Species\`, \`Activity Measure\`, \`Activity\`, \`Unit\`, \`pH\`, \`Ionic Strength mM\`, \`Salt Type\`, \`Medium\`, \`CFU\`, \`Note\`, \`Reference\`

Missingness:

| Field | Missing |  
|---|---:|  
| Peptide Sequence | 111, 0.5% |  
| Activity Measure | 145, 0.7% |  
| Activity | 0, 0.0% |  
| Unit | 1,214, 6.0% |  
| pH | 20,249, 99.3% |  
| Ionic Strength mM | 19,207, 94.2% |  
| Salt Type | 19,139, 93.9% |  
| Medium | 1,273, 6.2% |  
| CFU | 8,635, 42.4% |  
| Note | 15,379, 75.4% |  
| Reference | 1, 0.0% |

Observed activity units:  
\- \`µM\`  
\- \`µg/ml\`  
\- \`nmol/g\`

Observed activity measures include MIC, MBC, inhibition, killing, cytotoxicity, and other free-text categories.

\#\# DBAASP toxicity/lysis schema

Rows: \*\*1,609\*\*    
Unique peptide IDs: \*\*829\*\*    
Unique normalized sequences: \*\*717\*\*

Columns:

\`Peptide ID\`, \`Peptide Sequence\`, \`Target Cell\`, \`Activity Measure for Lysis\`, \`Peptide Concentration\`, \`Unit\`, \`Note\`, \`Reference\`

Missingness:

| Field | Missing |  
|---|---:|  
| Peptide Sequence | 1, 0.1% |  
| Target Cell | 0, 0.0% |  
| Activity Measure for Lysis | 23, 1.4% |  
| Peptide Concentration | 0, 0.0% |  
| Unit | 111, 6.9% |  
| Note | 1,411, 87.7% |  
| Reference | 38, 2.4% |

Observed target cells include human, rabbit, sheep, mouse, rat, horse, pig, bovine, and chicken erythrocytes, plus multiple mammalian cell lines.

Observed lysis measures include:  
\- Percentage hemolysis  
\- Percentage degranulation  
\- Cytotoxicity  
\- Inhibition  
\- Killing  
\- \`-\` or other nonnumeric values

Example:  
\- \`RVKRVWPLVIRTVIAGYNLYRAIKKK\`  
\- Human erythrocytes  
\- \`43.6% Hemolysis\`  
\- Concentration: \`32 µM\`

\#\# Exact sequence matching

Normalization strategy:

\- Preserve original sequences unchanged.  
\- Strip leading, trailing, and formatting whitespace.  
\- Convert to uppercase.  
\- Remove only clearly non-biological formatting artifacts.  
\- Preserve terminal modifications, cyclization, unusual residues, stereochemistry, and modification annotations.  
\- Do not assume modified and unmodified peptides are equivalent.  
\- Perform exact normalized-sequence matching only.

Results across the two DBAASP tables:

\- Activity sequences: \*\*1,743\*\*  
\- Toxicity sequences: \*\*717\*\*  
\- Exact normalized matches: \*\*714\*\*  
\- Activity sequences found in toxicity table: \*\*40.96%\*\*  
\- Toxicity sequences found in activity table: \*\*99.58%\*\*

Duplicate relationships:

\- Activity table: \*\*1,587\*\* duplicated sequence groups  
\- Toxicity table: \*\*369\*\* duplicated sequence groups

These duplicates are expected because the tables contain multiple organisms, assays, concentrations, conditions, and references.

\#\# Proposed data model

1\. \*\*Peptide master\*\*  
   \- One row per normalized sequence  
   \- Original source sequences  
   \- DRAMP and DBAASP IDs  
   \- Metadata and availability flags

 2\. \*\*Activity experimental table\*\*  
   \- One row per DBAASP activity measurement  
   \- Organism, measure, value, unit, conditions, notes, and reference

3\. \*\*Toxicity experimental table\*\*  
   \- One row per toxicity/lysis measurement  
   \- Toxicity type, value, unit, target cell or RBC type, conditions, and reference

This avoids a direct many-to-many merge and preserves all measurements.

\#\# Ambiguities and problems

\- The activity CSV contains \*\*111 records with missing peptide sequences\*\*. These cannot be sequence-matched unless the sequence is recovered from another source.  
\- DRAMP stores many activity and toxicity values as free text rather than normalized numeric fields.  
\- \`hemolytic-and-cytotoxic-activities.csv\` appears to be DBAASP-derived, despite the filename. It should not automatically be treated as DRAMP data.  
\- Several fields combine values and interpretation, such as \`43.6% Hemolysis\` or \`Not active up to 100 micro g/ ml\`.  
\- Modified, cyclic, lantibiotic, and stereochemically specified peptides must remain explicitly annotated.  
\- IDs must not be used as merge keys.  
\- Measurements must not be collapsed before defining the prediction task.

No files were modified, no transformations were performed, and no merge was created.  
