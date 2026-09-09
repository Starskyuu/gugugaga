$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$editorPath = 'C:\Program Files\Unity\Hub\Editor\6000.6.0f1\Editor\Unity.exe'
$logDirectory = Join-Path $projectPath 'Logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
foreach ($methodName in @('RescueSim.Editor.BuildRescueMission.BuildAndValidate','RescueSim.Editor.BuildRescueMission.BuildPlayer')) {
    $logName = 'Mission_' + ($methodName.Split('.')[-1]) + '.log'
    $arguments = @('-batchmode','-quit','-projectPath',('"' + $projectPath + '"'),'-executeMethod',$methodName,'-logFile',('"' + (Join-Path $logDirectory $logName) + '"'))
    $process = Start-Process -FilePath $editorPath -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "Unity failed: $methodName. See $logDirectory\$logName" }
}
$playerPath = Join-Path $projectPath 'Builds\Mission\RescueMissionSimulation.exe'
$process = Start-Process -FilePath $playerPath -ArgumentList @('-missionCheck','-logFile',('"' + (Join-Path $logDirectory 'Mission_Runtime.log') + '"')) -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) { throw 'Mission runtime verification failed.' }
Write-Host ('Ready: ' + $playerPath)
