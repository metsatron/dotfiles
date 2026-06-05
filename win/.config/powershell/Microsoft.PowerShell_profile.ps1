Import-Module PSReadLine

$Host.UI.RawUI.ForegroundColor = "White"

# 24-bit ANSI colors — immune to terminal palette remapping
$e = [char]27
Set-PSReadLineOption -Colors @{
    Command            = "$e[38;2;220;220;170m"   # #DCDCAA pale yellow
    Parameter          = "$e[38;2;156;220;254m"   # #9CDCFE light blue
    Operator           = "$e[38;2;212;212;212m"   # #D4D4D4 light gray
    Variable           = "$e[38;2;156;220;254m"   # #9CDCFE light blue
    String             = "$e[38;2;206;145;120m"   # #CE9178 warm orange
    Number             = "$e[38;2;181;206;168m"   # #B5CEA8 light green
    Member             = "$e[38;2;220;220;170m"   # #DCDCAA pale yellow
    Type               = "$e[38;2;78;201;176m"    # #4EC9B0 teal
    Comment            = "$e[38;2;106;153;85m"    # #6A9955 muted green
    Keyword            = "$e[38;2;197;134;192m"   # #C586C0 soft purple
    Error              = "$e[38;2;244;71;71m"     # #F44747 red
    Selection          = "$e[7m"                  # reverse video
    Default            = "$e[38;2;212;212;212m"   # #D4D4D4 light gray
    Emphasis           = "$e[38;2;220;220;170m"   # #DCDCAA pale yellow
    ContinuationPrompt = "$e[38;2;212;212;212m"   # #D4D4D4 light gray
}

# Git Bash — gbash avoids shadowing WSL's bash.exe if WSL is ever added
function gbash { & "C:\Program Files\Git\bin\bash.exe" -i -l @args }
