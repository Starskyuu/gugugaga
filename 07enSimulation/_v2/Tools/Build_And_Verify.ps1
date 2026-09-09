$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$editorPath = 'C:\Program Files\Unity\Hub\Editor\6000.6.0f1\Editor\Unity.exe'
$logDirectory = Join-Path $projectPath 'Logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
foreach ($methodName in @('RescueSim.Editor.BuildRescueProject.BuildAndValidate','RescueSim.Editor.BuildRescueProject.BuildPlayer')) {
    $logName = ($methodName.Split('.')[-1]) + '.log'
    $arguments = @('-batchmode','-quit','-projectPath',('"' + $projectPath + '"'),'-executeMethod',$methodName,'-logFile',('"' + (Join-Path $logDirectory $logName) + '"'))
    $process = Start-Process -FilePath $editorPath -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "Unity failed: $methodName. See $logDirectory\$logName" }
}
Write-Host ('Ready: ' + (Join-Path $projectPath 'Builds\Windows\RescueBoatPhysicsLab.exe'))
