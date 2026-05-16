[Setup]
AppName=SmartPrice
AppVersion=1.16.20
DefaultDirName={pf}\SmartPrice
DefaultGroupName=SmartPrice
OutputBaseFilename=Instalador_SmartPrice
Compression=lzma
SolidCompression=yes
DisableDirPage=no
UsePreviousAppDir=no
WizardStyle=modern

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "SmartPrice"; ValueData: """{app}\SmartPrice.exe"""; \
    Tasks: autostart


[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
Name: "autostart"; Description: "Iniciar SmartPrice automáticamente al iniciar Windows"; GroupDescription: "Inicio automático:"


[Files]
Source: "C:\Users\Op_1111\output\SmartPrice\SmartPrice.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\Op_1111\output\SmartPrice\_internal\*"; DestDir: "{app}\_internal"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "DB\veripre.db"
Source: "C:\Users\Op_1111\output\SmartPrice\_internal\DB\veripre.db"; DestDir: "{app}\_internal\DB"; Flags: onlyifdoesntexist ignoreversion
Source: "J:\Dowloads_C_160526\vlc-3.0.21-win32.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\SmartPrice"; Filename: "{app}\SmartPrice.exe"; WorkingDir: "{app}\_internal"
Name: "{group}\Desinstalar SmartPrice"; Filename: "{uninstallexe}"
Name: "{commondesktop}\SmartPrice"; Filename: "{app}\SmartPrice.exe"; Tasks: desktopicon; WorkingDir: "{app}\_internal"


[Run]
Filename: "{tmp}\vlc-3.0.21-win32.exe"; Parameters: "/S"; StatusMsg: "Instalando VLC..."; Flags: waituntilterminated
Filename: "{app}\SmartPrice.exe"; Description: "Iniciar SmartPrice"; Flags: nowait postinstall
