# diagnostico.ps1 — SOLO LEE informacion, no cambia nada. Correr en PowerShell (no hace falta admin).
# Uso:  powershell -ExecutionPolicy Bypass -File .\diagnostico.ps1
$ErrorActionPreference = 'SilentlyContinue'
$os  = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor
$ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)
$ver = [System.Environment]::OSVersion.Version
$wsl = (wsl --version 2>&1 | Out-String) -replace "`0",""
$distros = (wsl -l -v 2>&1 | Out-String) -replace "`0",""

"=== DIAGNOSTICO $(Get-Date -Format s) ==="
"Equipo        : $env:COMPUTERNAME  (usuario Windows: $env:USERNAME)"
"Windows       : $($os.Caption)  build $($ver.Build)  [$($os.OSArchitecture)]"
"  -> Modo espejo de WSL2 requiere Windows 11 build >= 22621 : " + $(if ($ver.Build -ge 22621) {"SI"} else {"NO"})
"CPU           : $($cpu[0].Name)"
"Nucleos fisicos: $(($cpu | Measure-Object NumberOfCores -Sum).Sum)   Logicos: $(($cpu | Measure-Object NumberOfLogicalProcessors -Sum).Sum)"
"RAM (GB)      : $ram"
"GPU           : $((Get-CimInstance Win32_VideoController | ForEach-Object Name) -join ' | ')"
"Virtualizacion: " + $(if ((Get-CimInstance Win32_Processor).VirtualizationFirmwareEnabled) {"activada en BIOS"} else {"DESACTIVADA o desconocida (WSL2 la necesita)"})
""
"--- Adaptadores de red ---"
Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed, MediaType | Format-Table -AutoSize | Out-String -Width 200
"Tiene puerto/adaptador Ethernet cableado: " + $(if (Get-NetAdapter -Physical | Where-Object { $_.InterfaceDescription -match 'Ethernet|Realtek PCIe|USB.*(LAN|GbE|Ethernet)|GbE' -and $_.InterfaceDescription -notmatch 'Wi-?Fi|Wireless|Bluetooth' }) {"SI"} else {"NO (necesita adaptador USB-Ethernet)"})
""
"--- IPs actuales ---"
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '169.*' -and $_.IPAddress -ne '127.0.0.1' } | Select-Object InterfaceAlias, IPAddress, PrefixLength | Format-Table -AutoSize | Out-String -Width 200
""
"--- WSL ---"
$wsl
$distros
"--- Plan de energia ---"
(powercfg /getactivescheme)
"--- Estado de bateria/corriente ---"
"En corriente (AC): " + $(if ((Get-CimInstance Win32_Battery) -eq $null) {"equipo sin bateria"} else {(Get-CimInstance Win32_Battery).BatteryStatus})
"=== FIN ==="
