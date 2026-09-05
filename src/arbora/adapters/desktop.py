"""Windows desktop / process adapter."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from arbora.adapters.powershell import ps_quote, require_windows, run_powershell
from arbora.core.types import StepResult, new_id
from arbora.voice.windows import sanitize_speech_text, speak_text

# Common friendly names → launch targets (Start-Process / Appx aliases).
APP_ALIASES: dict[str, str] = {
    "notepad": "notepad.exe",
    "calc": "calc.exe",
    "calculator": "calc.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "wordpad": "wordpad.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "msedge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "code": "Code.exe",
    "vscode": "Code.exe",
    "visual studio code": "Code.exe",
    "discord": "Discord.exe",
    "spotify": "Spotify.exe",
    "wt": "wt.exe",
    "windows terminal": "wt.exe",
    "slack": "slack.exe",
}

_KNOWN_LAUNCH_PATHS: dict[str, tuple[str, ...]] = {
    "chrome": (
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
    ),
    "edge": (
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
    ),
    "firefox": (
        r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
        r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",
    ),
    "vscode": (
        r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe",
        r"%ProgramFiles%\Microsoft VS Code\Code.exe",
    ),
    "discord": (r"%LocalAppData%\Discord\Discord.exe",),
    "spotify": (
        r"%AppData%\Spotify\Spotify.exe",
        r"%LocalAppData%\Microsoft\WindowsApps\Spotify.exe",
    ),
    "wt": (r"%LocalAppData%\Microsoft\WindowsApps\wt.exe",),
    "slack": (r"%LocalAppData%\slack\slack.exe",),
}

_EXE_TO_PATH_KEY = {
    "chrome.exe": "chrome",
    "msedge.exe": "edge",
    "firefox.exe": "firefox",
    "code.exe": "vscode",
    "discord.exe": "discord",
    "spotify.exe": "spotify",
    "wt.exe": "wt",
    "slack.exe": "slack",
}


def resolve_launch_target(name: str) -> str:
    """Map a friendly name to an exe or a known install path if it exists."""
    raw = name.strip()
    if not raw:
        return raw
    lowered = raw.lower()
    exe = APP_ALIASES.get(lowered, raw)
    key = _EXE_TO_PATH_KEY.get(exe.lower(), lowered if lowered in _KNOWN_LAUNCH_PATHS else "")
    for candidate in _KNOWN_LAUNCH_PATHS.get(key, ()):
        path = Path(os.path.expandvars(candidate))
        if path.is_file():
            return str(path)
    return exe


CLIPBOARD_PREVIEW_CHARS = 120
CLIPBOARD_SAVE_MAX_CHARS = 20_000
BROWSER_URL_MAX_CHARS = 2_000
INSTALLED_BROWSER_ALIASES = frozenset(
    {
        "chrome",
        "google chrome",
        "edge",
        "microsoft edge",
        "msedge",
        "firefox",
    }
)

_SECRET_MARKERS = (
    "password=",
    "passwd=",
    "pwd=",
    "secret=",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "bearer ",
    "authorization:",
    "private_key",
    "-----begin",
    "ghp_",
    "github_pat_",
    "glpat-",
    "xoxb-",
    "xoxp-",
    "sk-ant-",
    "sk-proj-",
    "akia",
)


def clipboard_looks_secret(text: str) -> bool:
    """True when clipboard text looks like a password, token, or key."""
    if not text or not text.strip():
        return False
    lower = text.lower()
    if any(marker in lower for marker in _SECRET_MARKERS):
        return True
    if re.search(r"(?i)(^|[\s\"'=])sk-[A-Za-z0-9]{10,}", text):
        return True
    stripped = text.strip()
    if stripped.count(".") == 2 and len(stripped) >= 40 and stripped.startswith("eyJ"):
        return True
    compact = "".join(stripped.split())
    if len(compact) >= 32 and all(char in "0123456789abcdefABCDEF" for char in compact):
        return True
    return False


def parse_clipboard_snapshot(stdout: str) -> dict[str, Any]:
    """Parse the structured Get-Clipboard snapshot written by PowerShell."""
    kind = "empty"
    length = 0
    width: int | None = None
    height: int | None = None
    files: list[str] = []
    capturing_text = False
    text_lines: list[str] = []
    for line in (stdout or "").splitlines():
        if capturing_text:
            text_lines.append(line)
            continue
        if line == "TEXT_BEGIN":
            capturing_text = True
            continue
        if line.startswith("KIND="):
            kind = line.split("=", 1)[1].strip().lower() or "empty"
        elif line.startswith("LENGTH="):
            try:
                length = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                length = 0
        elif line.startswith("WIDTH="):
            try:
                width = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                width = None
        elif line.startswith("HEIGHT="):
            try:
                height = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                height = None
        elif line.startswith("FILE="):
            files.append(line.split("=", 1)[1])
    text = "\n".join(text_lines)
    if kind == "text" and not length:
        length = len(text)
    if kind == "files" and not length:
        length = len(files)
    return {
        "kind": kind,
        "length": length,
        "width": width,
        "height": height,
        "files": files,
        "text": text,
    }


def format_clipboard_report(snapshot: dict[str, Any], *, reveal: bool) -> str:
    kind = str(snapshot.get("kind") or "empty")
    if kind == "empty":
        return "Clipboard is empty."
    if kind == "image":
        width = snapshot.get("width")
        height = snapshot.get("height")
        size = f" {width}x{height}" if width and height else ""
        return f"Clipboard holds an image{size}. Pixel data is not shown."
    if kind == "files":
        files = [str(item) for item in snapshot.get("files") or []]
        count = int(snapshot.get("length") or len(files))
        lines = [f"Clipboard holds {count} file path(s)."]
        lines.extend(f"  {name}" for name in files[:20])
        return "\n".join(lines)
    length = int(snapshot.get("length") or 0)
    text = str(snapshot.get("text") or "")
    if clipboard_looks_secret(text):
        return (
            f"Clipboard holds text ({length} chars). "
            "Content withheld because it looks like a secret (password, token, or key)."
        )
    if not reveal:
        return (
            f"Clipboard holds text ({length} chars). "
            "Content withheld; ask to show clipboard text for a short preview."
        )
    preview = text.replace("\r\n", "\n")
    if len(preview) > CLIPBOARD_PREVIEW_CHARS:
        preview = preview[:CLIPBOARD_PREVIEW_CHARS] + "…"
    return f"Clipboard text ({length} chars):\n{preview}"


def clipboard_save_payload(snapshot: dict[str, Any]) -> tuple[str | None, str]:
    """Return (text, error). Text is None when the clipboard must not be written to disk."""
    kind = str(snapshot.get("kind") or "empty")
    if kind == "empty":
        return None, "Clipboard is empty; nothing to save"
    if kind == "image":
        return None, "Clipboard holds an image; save clipboard to notes only writes text"
    if kind == "files":
        return None, "Clipboard holds file paths; save clipboard to notes only writes text"
    text = str(snapshot.get("text") or "")
    if not text.strip():
        return None, "Clipboard text is empty; nothing to save"
    if clipboard_looks_secret(text):
        return None, (
            "Refusing to save clipboard text because it looks like a secret "
            "(password, token, or key)"
        )
    if len(text) > CLIPBOARD_SAVE_MAX_CHARS:
        return None, (
            f"Clipboard text is {len(text)} chars; "
            f"refusing to save more than {CLIPBOARD_SAVE_MAX_CHARS}"
        )
    return text.replace("\r\n", "\n"), ""


_BATTERY_STATUS_LABELS = {
    1: "Other",
    2: "Unknown",
    3: "Fully charged",
    4: "Low",
    5: "Critical",
    6: "Charging",
    7: "Charging and high",
    8: "Charging and low",
    9: "Charging and critical",
    10: "Undefined",
    11: "Partially charged",
}

_PRINTER_STATUS_LABELS = {
    1: "Other",
    2: "Unknown",
    3: "Idle",
    4: "Printing",
    5: "Warmup",
    6: "Stopped printing",
    7: "Offline",
}

_PC_SYSTEM_TYPE_LABELS = {
    1: "Desktop",
    2: "Mobile / laptop",
    3: "Workstation",
    4: "Enterprise server",
    5: "SOHO server",
    6: "Appliance PC",
    7: "Performance server",
    8: "Slate / tablet",
}

_BATTERY_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "Write-Output '=== Power ==='; "
    "try { "
    "  $cs = Get-CimInstance -ClassName Win32_ComputerSystem; "
    "  Write-Output ('PCSystemType=' + $cs.PCSystemType); "
    "} catch { Write-Output 'PCSystemType='; }; "
    "Write-Output '=== Battery ==='; "
    "$bats = @(Get-CimInstance -ClassName Win32_Battery); "
    "Write-Output ('COUNT=' + @($bats).Count); "
    "$bats | Select-Object -First 4 | ForEach-Object { "
    "  Write-Output 'BATTERY_BEGIN'; "
    "  Write-Output ('NAME=' + $_.Name); "
    "  Write-Output ('STATUS=' + $_.BatteryStatus); "
    "  Write-Output ('PERCENT=' + $_.EstimatedChargeRemaining); "
    "  Write-Output ('RUNTIME_MIN=' + $_.EstimatedRunTime); "
    "}"
)

_PRINTER_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "Write-Output '=== Printers ==='; "
    "$ps = @(Get-CimInstance -ClassName Win32_Printer); "
    "Write-Output ('COUNT=' + @($ps).Count); "
    "$ps | Select-Object -First 20 | ForEach-Object { "
    "  Write-Output 'PRINTER_BEGIN'; "
    "  Write-Output ('NAME=' + $_.Name); "
    "  Write-Output ('DEFAULT=' + $_.Default); "
    "  Write-Output ('STATUS=' + $_.PrinterStatus); "
    "  Write-Output ('WORKOFFLINE=' + $_.WorkOffline); "
    "  Write-Output ('PORT=' + $_.PortName); "
    "  Write-Output ('NETWORK=' + $_.Network); "
    "  Write-Output ('SHARED=' + $_.Shared); "
    "}"
)

STARTUP_COMMAND_MAX_CHARS = 180
STARTUP_MAX_ITEMS = 40

_STARTUP_SOURCE_LABELS = {
    "hkcu_run": "HKCU Run",
    "hklm_run": "HKLM Run",
    "startup_folder": "Startup folder",
}

_STARTUP_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "function Emit-RunKey([string]$source, [string]$path) { "
    "  $item = Get-Item -LiteralPath $path; "
    "  if (-not $item) { return }; "
    "  $names = @($item.GetValueNames() | Where-Object { $_ -and $_ -ne '(default)' } | Select-Object -First 20); "
    "  foreach ($name in $names) { "
    "    Write-Output 'ITEM_BEGIN'; "
    "    Write-Output ('SOURCE=' + $source); "
    "    Write-Output ('NAME=' + $name); "
    "    $val = [string]$item.GetValue($name); "
    "    if ($null -eq $val) { $val = '' }; "
    "    if ($val.Length -gt 180) { $val = $val.Substring(0, 180) }; "
    "    Write-Output ('COMMAND=' + $val); "
    "  } "
    "}; "
    "Write-Output '=== Startup ==='; "
    "Emit-RunKey 'hkcu_run' 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'; "
    "Emit-RunKey 'hklm_run' 'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'; "
    "$folder = [Environment]::GetFolderPath('Startup'); "
    "if ($folder) { "
    "  $files = @(Get-ChildItem -LiteralPath $folder -Force -ErrorAction SilentlyContinue | "
    "    Where-Object { -not $_.PSIsContainer } | Select-Object -First 20); "
    "  foreach ($f in $files) { "
    "    Write-Output 'ITEM_BEGIN'; "
    "    Write-Output 'SOURCE=startup_folder'; "
    "    Write-Output ('NAME=' + $f.Name); "
    "    Write-Output 'COMMAND='; "
    "  } "
    "}"
)

_DEFAULT_BROWSER_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "function Read-Choice([string]$scheme) { "
    "  $p = 'HKCU:\\Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\' + $scheme + '\\UserChoice'; "
    "  $item = Get-ItemProperty -LiteralPath $p; "
    "  $prog = ''; "
    "  if ($item -and $item.ProgId) { $prog = [string]$item.ProgId }; "
    "  Write-Output (($scheme.ToUpper()) + '_PROGID=' + $prog); "
    "}; "
    "Write-Output '=== DefaultBrowser ==='; "
    "Read-Choice 'https'; "
    "Read-Choice 'http'"
)

DISPLAY_MAX_ITEMS = 8

_DISPLAY_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "Add-Type -AssemblyName System.Windows.Forms; "
    "$screens = @([System.Windows.Forms.Screen]::AllScreens); "
    "Write-Output '=== Displays ==='; "
    "Write-Output ('COUNT=' + @($screens).Count); "
    "$screens | Select-Object -First 8 | ForEach-Object { "
    "  Write-Output 'DISPLAY_BEGIN'; "
    "  Write-Output ('DEVICE=' + $_.DeviceName); "
    "  Write-Output ('PRIMARY=' + $_.Primary); "
    "  Write-Output ('WIDTH=' + $_.Bounds.Width); "
    "  Write-Output ('HEIGHT=' + $_.Bounds.Height); "
    "  Write-Output ('X=' + $_.Bounds.X); "
    "  Write-Output ('Y=' + $_.Bounds.Y); "
    "  Write-Output ('WORKING_WIDTH=' + $_.WorkingArea.Width); "
    "  Write-Output ('WORKING_HEIGHT=' + $_.WorkingArea.Height); "
    "  Write-Output ('BITS=' + $_.BitsPerPixel); "
    "}"
)

WINDOWS_UPDATE_DESC_MAX_CHARS = 80

_WINDOWS_UPDATE_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "Write-Output '=== WindowsUpdate ==='; "
    "$hotfixes = @(Get-HotFix | Where-Object { $_.InstalledOn } | Sort-Object InstalledOn -Descending); "
    "Write-Output ('COUNT=' + @($hotfixes).Count); "
    "$latest = $hotfixes | Select-Object -First 1; "
    "if ($latest) { "
    "  Write-Output 'UPDATE_BEGIN'; "
    "  Write-Output ('KB=' + $latest.HotFixID); "
    "  $when = ''; "
    "  if ($latest.InstalledOn) { $when = $latest.InstalledOn.ToString('yyyy-MM-dd') }; "
    "  Write-Output ('INSTALLED=' + $when); "
    "  $desc = [string]$latest.Description; "
    "  if ($null -eq $desc) { $desc = '' }; "
    "  if ($desc.Length -gt 80) { $desc = $desc.Substring(0, 80) }; "
    "  Write-Output ('DESC=' + $desc); "
    "}"
)

_TIMEZONE_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "Write-Output '=== TimeZone ==='; "
    "try { "
    "  $tz = Get-TimeZone; "
    "  Write-Output ('TZ_ID=' + $tz.Id); "
    "  Write-Output ('TZ_NAME=' + $tz.DisplayName); "
    "  Write-Output ('TZ_STD=' + $tz.StandardName); "
    "  $offset = ''; "
    "  if ($tz.BaseUtcOffset) { $offset = $tz.BaseUtcOffset.ToString() }; "
    "  Write-Output ('TZ_OFFSET=' + $offset); "
    "  Write-Output ('TZ_DST=' + $tz.SupportsDaylightSavingTime); "
    "} catch { Write-Output 'TZ_ID='; }; "
    "Write-Output '=== Locale ==='; "
    "try { "
    "  $culture = Get-Culture; "
    "  Write-Output ('CULTURE=' + $culture.Name); "
    "  Write-Output ('CULTURE_DISPLAY=' + $culture.DisplayName); "
    "} catch { Write-Output 'CULTURE='; }; "
    "try { "
    "  $sys = Get-WinSystemLocale; "
    "  Write-Output ('SYSTEM_LOCALE=' + $sys.Name); "
    "} catch { Write-Output 'SYSTEM_LOCALE='; }"
)

_THEME_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "$path = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize'; "
    "try { "
    "  $apps = (Get-ItemProperty -Path $path -Name AppsUseLightTheme).AppsUseLightTheme; "
    "  Write-Output ('APPS_LIGHT=' + [int]$apps); "
    "} catch { Write-Output 'APPS_LIGHT='; }; "
    "try { "
    "  $sys = (Get-ItemProperty -Path $path -Name SystemUsesLightTheme).SystemUsesLightTheme; "
    "  Write-Output ('SYSTEM_LIGHT=' + [int]$sys); "
    "} catch { Write-Output 'SYSTEM_LIGHT='; }"
)

_VOLUME_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "Add-Type -TypeDefinition @'\n"
    "using System;\n"
    "using System.Runtime.InteropServices;\n"
    "[Guid(\"5CDF2C82-841E-4546-9722-0CF74078229A\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
    "interface IArboraAudioEndpointVolume {\n"
    "  int _a(); int _b(); int _c(); int _d(); int _e(); int _f();\n"
    "  int GetMasterVolumeLevelScalar(out float pfLevel);\n"
    "  int _g(); int _h(); int _i(); int _j(); int _k();\n"
    "  int GetMute(out bool pbMute);\n"
    "}\n"
    "[Guid(\"D666063F-1587-4E43-81F1-B948E807363F\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
    "interface IArboraMmDevice {\n"
    "  int Activate(ref Guid id, int clsCtx, int activationParams, "
    "[MarshalAs(UnmanagedType.IUnknown)] out object iface);\n"
    "}\n"
    "[Guid(\"A95664D2-9614-4F35-A746-DE8DB63617E6\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
    "interface IArboraMmDeviceEnumerator {\n"
    "  int _a();\n"
    "  int GetDefaultAudioEndpoint(int dataFlow, int role, out IArboraMmDevice ppDevice);\n"
    "}\n"
    "[ComImport, Guid(\"BCDE0395-E52F-467C-8E3D-C4579291692E\")] class ArboraMmDeviceEnumeratorComObject { }\n"
    "public class ArboraVolumeProbe {\n"
    "  public static string Snapshot() {\n"
    "    var enumerator = new ArboraMmDeviceEnumeratorComObject() as IArboraMmDeviceEnumerator;\n"
    "    IArboraMmDevice dev;\n"
    "    Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0, 1, out dev));\n"
    "    Guid iid = typeof(IArboraAudioEndpointVolume).GUID;\n"
    "    object ep;\n"
    "    Marshal.ThrowExceptionForHR(dev.Activate(ref iid, 23, 0, out ep));\n"
    "    var vol = (IArboraAudioEndpointVolume)ep;\n"
    "    float scalar = 0;\n"
    "    Marshal.ThrowExceptionForHR(vol.GetMasterVolumeLevelScalar(out scalar));\n"
    "    bool muted = false;\n"
    "    Marshal.ThrowExceptionForHR(vol.GetMute(out muted));\n"
    "    int percent = (int)Math.Round(scalar * 100.0);\n"
    "    if (percent < 0) { percent = 0; }\n"
    "    if (percent > 100) { percent = 100; }\n"
    "    return \"PERCENT=\" + percent + \"\\nMUTED=\" + (muted ? \"1\" : \"0\");\n"
    "  }\n"
    "}\n"
    "'@ -ErrorAction SilentlyContinue; "
    "try { "
    "  Write-Output ([ArboraVolumeProbe]::Snapshot()); "
    "} catch { Write-Output 'PERCENT='; Write-Output 'MUTED='; }"
)

_WALLPAPER_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "$path = 'HKCU:\\Control Panel\\Desktop'; "
    "try { "
    "  $wp = (Get-ItemProperty -Path $path -Name Wallpaper).Wallpaper; "
    "  Write-Output ('WALLPAPER=' + $wp); "
    "} catch { Write-Output 'WALLPAPER='; }; "
    "try { "
    "  $style = (Get-ItemProperty -Path $path -Name WallpaperStyle).WallpaperStyle; "
    "  Write-Output ('STYLE=' + $style); "
    "} catch { Write-Output 'STYLE='; }; "
    "try { "
    "  $tile = (Get-ItemProperty -Path $path -Name TileWallpaper).TileWallpaper; "
    "  Write-Output ('TILE=' + $tile); "
    "} catch { Write-Output 'TILE='; }"
)

_IDLE_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "Add-Type -TypeDefinition @'\n"
    "using System;\n"
    "using System.Runtime.InteropServices;\n"
    "public class ArboraIdleProbe {\n"
    "  [StructLayout(LayoutKind.Sequential)]\n"
    "  public struct LASTINPUTINFO { public uint cbSize; public uint dwTime; }\n"
    "  [DllImport(\"user32.dll\")] public static extern bool GetLastInputInfo(ref LASTINPUTINFO plii);\n"
    "  public static uint IdleMs() {\n"
    "    LASTINPUTINFO info = new LASTINPUTINFO();\n"
    "    info.cbSize = (uint)Marshal.SizeOf(info);\n"
    "    GetLastInputInfo(ref info);\n"
    "    return unchecked((uint)Environment.TickCount) - info.dwTime;\n"
    "  }\n"
    "}\n"
    "'@ -ErrorAction SilentlyContinue; "
    "try { "
    "  Write-Output ('IDLE_MS=' + [ArboraIdleProbe]::IdleMs()); "
    "} catch { Write-Output 'IDLE_MS='; }"
)

_AUDIO_DEVICE_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "Add-Type -TypeDefinition @'\n"
    "using System;\n"
    "using System.Runtime.InteropServices;\n"
    "[StructLayout(LayoutKind.Sequential)]\n"
    "struct ArboraPropertyKey {\n"
    "  public Guid fmtid;\n"
    "  public uint pid;\n"
    "}\n"
    "[StructLayout(LayoutKind.Explicit)]\n"
    "struct ArboraPropVariant {\n"
    "  [FieldOffset(0)] public ushort vt;\n"
    "  [FieldOffset(8)] public IntPtr p;\n"
    "}\n"
    "[Guid(\"886d8eeb-8cf2-4446-8d02-cdba1dbdcf99\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
    "interface IArboraPropertyStore {\n"
    "  int GetCount(out uint cProps);\n"
    "  int GetAt(uint iProp, out ArboraPropertyKey pkey);\n"
    "  int GetValue(ref ArboraPropertyKey key, out ArboraPropVariant pv);\n"
    "}\n"
    "[Guid(\"D666063F-1587-4E43-81F1-B948E807363F\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
    "interface IArboraNamedMmDevice {\n"
    "  int Activate(ref Guid id, int clsCtx, int activationParams, "
    "[MarshalAs(UnmanagedType.IUnknown)] out object iface);\n"
    "  int OpenPropertyStore(int stgmAccess, out IArboraPropertyStore store);\n"
    "}\n"
    "[Guid(\"A95664D2-9614-4F35-A746-DE8DB63617E6\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n"
    "interface IArboraNamedMmDeviceEnumerator {\n"
    "  int _a();\n"
    "  int GetDefaultAudioEndpoint(int dataFlow, int role, out IArboraNamedMmDevice ppDevice);\n"
    "}\n"
    "[ComImport, Guid(\"BCDE0395-E52F-467C-8E3D-C4579291692E\")] class ArboraNamedMmDeviceEnumeratorComObject { }\n"
    "public class ArboraAudioDeviceProbe {\n"
    "  public static string Snapshot() {\n"
    "    var enumerator = new ArboraNamedMmDeviceEnumeratorComObject() as IArboraNamedMmDeviceEnumerator;\n"
    "    IArboraNamedMmDevice dev;\n"
    "    Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0, 1, out dev));\n"
    "    IArboraPropertyStore store;\n"
    "    Marshal.ThrowExceptionForHR(dev.OpenPropertyStore(0, out store));\n"
    "    ArboraPropertyKey key = new ArboraPropertyKey();\n"
    "    key.fmtid = new Guid(\"a45c254e-df1c-4efd-8020-67d146a850e0\");\n"
    "    key.pid = 14;\n"
    "    ArboraPropVariant pv;\n"
    "    Marshal.ThrowExceptionForHR(store.GetValue(ref key, out pv));\n"
    "    string name = \"\";\n"
    "    if (pv.vt == 31 && pv.p != IntPtr.Zero) {\n"
    "      name = Marshal.PtrToStringUni(pv.p) ?? \"\";\n"
    "    }\n"
    "    if (name.Length > 180) { name = name.Substring(0, 180); }\n"
    "    return \"NAME=\" + name + \"\\nFLOW=playback\";\n"
    "  }\n"
    "}\n"
    "'@ -ErrorAction SilentlyContinue; "
    "try { "
    "  Write-Output ([ArboraAudioDeviceProbe]::Snapshot()); "
    "} catch { Write-Output 'NAME='; Write-Output 'FLOW='; }"
)

INSTALLED_APPS_MAX_ITEMS = 40
INSTALLED_APP_NAME_MAX_CHARS = 120
INSTALLED_APP_PUBLISHER_MAX_CHARS = 80

_INSTALLED_APPS_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "$paths = @("
    "'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall', "
    "'HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall', "
    "'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall'"
    "); "
    "$seen = @{}; "
    "$items = New-Object System.Collections.Generic.List[object]; "
    "foreach ($path in $paths) { "
    "  Get-ChildItem -LiteralPath $path | ForEach-Object { "
    "    $p = Get-ItemProperty -LiteralPath $_.PSPath; "
    "    $name = [string]$p.DisplayName; "
    "    if (-not $name) { return }; "
    "    $name = $name.Trim(); "
    "    if (-not $name) { return }; "
    "    if ($seen.ContainsKey($name)) { return }; "
    "    $seen[$name] = $true; "
    "    if ($name.Length -gt 120) { $name = $name.Substring(0, 120) }; "
    "    $pub = [string]$p.Publisher; "
    "    if ($null -eq $pub) { $pub = '' }; "
    "    $pub = $pub.Trim(); "
    "    if ($pub.Length -gt 80) { $pub = $pub.Substring(0, 80) }; "
    "    $items.Add([pscustomobject]@{ Name = $name; Publisher = $pub }) "
    "  } "
    "}; "
    "Write-Output '=== InstalledApps ==='; "
    "Write-Output ('COUNT=' + $items.Count); "
    "$items | Sort-Object Name | Select-Object -First 40 | ForEach-Object { "
    "  Write-Output 'APP_BEGIN'; "
    "  Write-Output ('NAME=' + $_.Name); "
    "  Write-Output ('PUBLISHER=' + $_.Publisher) "
    "}"
)

HOSTS_MAX_BYTES = 64_000
HOSTS_MAX_ENTRIES = 40


def windows_hosts_path() -> Path:
    """Fixed Windows hosts path; callers cannot redirect this inspect."""
    root = os.environ.get("SystemRoot") or r"C:\Windows"
    return Path(root) / "System32" / "drivers" / "etc" / "hosts"


def parse_battery_snapshot(stdout: str) -> dict[str, Any]:
    """Parse the structured Win32_Battery snapshot written by PowerShell."""
    pc_type: int | None = None
    count = 0
    batteries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in (stdout or "").splitlines():
        if line == "BATTERY_BEGIN":
            current = {"name": "", "status": None, "percent": None, "runtime_min": None}
            batteries.append(current)
            continue
        if line.startswith("PCSystemType="):
            raw = line.split("=", 1)[1].strip()
            try:
                pc_type = int(raw) if raw else None
            except ValueError:
                pc_type = None
        elif line.startswith("COUNT="):
            try:
                count = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                count = 0
        elif current is not None and line.startswith("NAME="):
            current["name"] = line.split("=", 1)[1].strip()
        elif current is not None and line.startswith("STATUS="):
            try:
                current["status"] = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                current["status"] = None
        elif current is not None and line.startswith("PERCENT="):
            try:
                current["percent"] = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                current["percent"] = None
        elif current is not None and line.startswith("RUNTIME_MIN="):
            try:
                current["runtime_min"] = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                current["runtime_min"] = None
    if not count:
        count = len(batteries)
    return {"pc_system_type": pc_type, "count": count, "batteries": batteries}


def format_battery_report(snapshot: dict[str, Any]) -> str:
    pc_type = snapshot.get("pc_system_type")
    chassis = _PC_SYSTEM_TYPE_LABELS.get(int(pc_type), "Unknown chassis") if pc_type is not None else "Unknown chassis"
    lines = [f"Power: {chassis} (PCSystemType={pc_type if pc_type is not None else 'n/a'})"]
    batteries = list(snapshot.get("batteries") or [])
    count = int(snapshot.get("count") or len(batteries))
    if count < 1 and not batteries:
        lines.append("No battery reported (desktop / AC-only).")
        return "\n".join(lines)
    lines.append(f"Battery count: {count}")
    for item in batteries:
        name = str(item.get("name") or "Battery")
        status = item.get("status")
        status_label = _BATTERY_STATUS_LABELS.get(int(status), "Unknown") if status is not None else "Unknown"
        percent = item.get("percent")
        if isinstance(percent, int) and 0 <= percent <= 100:
            charge = f"{percent}%"
        else:
            charge = "unknown %"
        parts = [name, f"charge={charge}", f"status={status_label}"]
        runtime = item.get("runtime_min")
        if isinstance(runtime, int) and 1 <= runtime <= 10_000:
            parts.append(f"runtime={runtime} min")
        lines.append("  " + "; ".join(parts))
    return "\n".join(lines)


def parse_printer_snapshot(stdout: str) -> dict[str, Any]:
    """Parse the structured Win32_Printer snapshot written by PowerShell."""
    count = 0
    printers: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in (stdout or "").splitlines():
        if line == "PRINTER_BEGIN":
            current = {
                "name": "",
                "default": False,
                "status": None,
                "work_offline": False,
                "port": "",
                "network": False,
                "shared": False,
            }
            printers.append(current)
            continue
        if line.startswith("COUNT="):
            try:
                count = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                count = 0
            continue
        if current is None:
            continue
        if line.startswith("NAME="):
            current["name"] = line.split("=", 1)[1].strip()
        elif line.startswith("DEFAULT="):
            current["default"] = line.split("=", 1)[1].strip().lower() in {"true", "1"}
        elif line.startswith("STATUS="):
            try:
                current["status"] = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                current["status"] = None
        elif line.startswith("WORKOFFLINE="):
            current["work_offline"] = line.split("=", 1)[1].strip().lower() in {"true", "1"}
        elif line.startswith("PORT="):
            current["port"] = line.split("=", 1)[1].strip()
        elif line.startswith("NETWORK="):
            current["network"] = line.split("=", 1)[1].strip().lower() in {"true", "1"}
        elif line.startswith("SHARED="):
            current["shared"] = line.split("=", 1)[1].strip().lower() in {"true", "1"}
    if not count:
        count = len(printers)
    return {"count": count, "printers": printers}


def format_printer_report(snapshot: dict[str, Any]) -> str:
    printers = list(snapshot.get("printers") or [])
    count = int(snapshot.get("count") or len(printers))
    if count < 1 and not printers:
        return "No printers reported."
    lines = [f"Printer count: {count}"]
    for item in printers:
        name = str(item.get("name") or "Printer")
        status = item.get("status")
        status_label = _PRINTER_STATUS_LABELS.get(int(status), "Unknown") if status is not None else "Unknown"
        flags: list[str] = []
        if item.get("default"):
            flags.append("default")
        if item.get("work_offline"):
            flags.append("offline")
        if item.get("network"):
            flags.append("network")
        if item.get("shared"):
            flags.append("shared")
        flag_text = f" ({', '.join(flags)})" if flags else ""
        port = str(item.get("port") or "").strip()
        port_text = f"; port={port}" if port else ""
        lines.append(f"  {name}{flag_text}; status={status_label}{port_text}")
    default_names = [str(item.get("name") or "") for item in printers if item.get("default")]
    if default_names:
        lines.insert(1, f"Default printer: {default_names[0]}")
    else:
        lines.insert(1, "Default printer: (none marked)")
    return "\n".join(lines)


def parse_startup_snapshot(stdout: str) -> dict[str, Any]:
    """Parse the structured HKCU/HKLM Run + Startup-folder snapshot."""
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in (stdout or "").splitlines():
        if line == "ITEM_BEGIN":
            current = {"source": "", "name": "", "command": ""}
            items.append(current)
            continue
        if current is None:
            continue
        if line.startswith("SOURCE="):
            current["source"] = line.split("=", 1)[1].strip()
        elif line.startswith("NAME="):
            current["name"] = line.split("=", 1)[1].strip()
        elif line.startswith("COMMAND="):
            current["command"] = line.split("=", 1)[1].strip()
    return {"items": items[:STARTUP_MAX_ITEMS]}


def format_startup_report(snapshot: dict[str, Any]) -> str:
    items = list(snapshot.get("items") or [])
    if not items:
        return "No startup apps reported."
    lines = [f"Startup items: {len(items)}"]
    for item in items:
        source = _STARTUP_SOURCE_LABELS.get(str(item.get("source") or ""), "Other")
        name = str(item.get("name") or "unnamed")
        command = str(item.get("command") or "").strip()
        if command and clipboard_looks_secret(command):
            command = "(command withheld)"
        elif len(command) > STARTUP_COMMAND_MAX_CHARS:
            command = command[:STARTUP_COMMAND_MAX_CHARS]
        if command:
            lines.append(f"  [{source}] {name} — {command}")
        else:
            lines.append(f"  [{source}] {name}")
    return "\n".join(lines)


def browser_name_from_progid(progid: str) -> str:
    """Map a UserChoice ProgId to a friendly browser name."""
    raw = (progid or "").strip()
    lower = raw.lower()
    if not raw:
        return "Unknown"
    if lower.startswith("chromehtml"):
        return "Google Chrome"
    if lower.startswith("msedgehtm"):
        return "Microsoft Edge"
    if lower.startswith("firefoxurl"):
        return "Mozilla Firefox"
    if lower.startswith("ie.http") or lower in {"htmlfile", "ie.https"}:
        return "Internet Explorer"
    if lower.startswith("operastable") or lower.startswith("opera"):
        return "Opera"
    if lower.startswith("bravehtml"):
        return "Brave"
    if lower.startswith("appx"):
        return "Microsoft Store app"
    return raw


def parse_default_browser_snapshot(stdout: str) -> dict[str, str]:
    """Parse https/http UserChoice ProgIds from PowerShell."""
    https_progid = ""
    http_progid = ""
    for line in (stdout or "").splitlines():
        if line.startswith("HTTPS_PROGID="):
            https_progid = line.split("=", 1)[1].strip()
        elif line.startswith("HTTP_PROGID="):
            http_progid = line.split("=", 1)[1].strip()
    return {"https_progid": https_progid, "http_progid": http_progid}


def format_default_browser_report(snapshot: dict[str, str]) -> str:
    https_progid = str(snapshot.get("https_progid") or "").strip()
    http_progid = str(snapshot.get("http_progid") or "").strip()
    if not https_progid and not http_progid:
        return "No default browser association reported."
    lines: list[str] = []
    if https_progid:
        lines.append(
            f"Default browser (https): {browser_name_from_progid(https_progid)} ({https_progid})"
        )
    else:
        lines.append("Default browser (https): (none reported)")
    if http_progid and http_progid.lower() != https_progid.lower():
        lines.append(
            f"HTTP association: {browser_name_from_progid(http_progid)} ({http_progid})"
        )
    elif http_progid:
        lines.append("HTTP association: same as https")
    return "\n".join(lines)


def parse_display_snapshot(stdout: str) -> dict[str, Any]:
    """Parse attached-display bounds from System.Windows.Forms.Screen."""
    count = 0
    displays: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in (stdout or "").splitlines():
        if line == "DISPLAY_BEGIN":
            current = {
                "device": "",
                "primary": False,
                "width": None,
                "height": None,
                "x": None,
                "y": None,
                "working_width": None,
                "working_height": None,
                "bits": None,
            }
            displays.append(current)
            continue
        if line.startswith("COUNT="):
            try:
                count = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                count = 0
            continue
        if current is None:
            continue
        if line.startswith("DEVICE="):
            current["device"] = line.split("=", 1)[1].strip()
        elif line.startswith("PRIMARY="):
            current["primary"] = line.split("=", 1)[1].strip().lower() in {"true", "1"}
        elif line.startswith("WIDTH="):
            try:
                current["width"] = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                current["width"] = None
        elif line.startswith("HEIGHT="):
            try:
                current["height"] = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                current["height"] = None
        elif line.startswith("X="):
            try:
                current["x"] = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                current["x"] = None
        elif line.startswith("Y="):
            try:
                current["y"] = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                current["y"] = None
        elif line.startswith("WORKING_WIDTH="):
            try:
                current["working_width"] = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                current["working_width"] = None
        elif line.startswith("WORKING_HEIGHT="):
            try:
                current["working_height"] = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                current["working_height"] = None
        elif line.startswith("BITS="):
            try:
                current["bits"] = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                current["bits"] = None
    if not count:
        count = len(displays)
    return {"count": count, "displays": displays[:DISPLAY_MAX_ITEMS]}


def format_display_report(snapshot: dict[str, Any]) -> str:
    displays = list(snapshot.get("displays") or [])
    count = int(snapshot.get("count") or len(displays))
    if count < 1 and not displays:
        return "No displays reported."
    lines = [f"Display count: {count}"]
    for item in displays:
        device = str(item.get("device") or "Display")
        width = item.get("width")
        height = item.get("height")
        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
            size = f"{width}x{height}"
        else:
            size = "unknown resolution"
        flags: list[str] = []
        if item.get("primary"):
            flags.append("primary")
        flag_text = f" ({', '.join(flags)})" if flags else ""
        origin = ""
        x_pos = item.get("x")
        y_pos = item.get("y")
        if isinstance(x_pos, int) and isinstance(y_pos, int):
            origin = f" at {x_pos},{y_pos}"
        working = ""
        work_w = item.get("working_width")
        work_h = item.get("working_height")
        if isinstance(work_w, int) and isinstance(work_h, int) and work_w > 0 and work_h > 0:
            working = f"; working={work_w}x{work_h}"
        bits = item.get("bits")
        bits_text = f"; {bits} bpp" if isinstance(bits, int) and bits > 0 else ""
        lines.append(f"  {device}{flag_text} {size}{origin}{working}{bits_text}")
    return "\n".join(lines)


def parse_windows_update_snapshot(stdout: str) -> dict[str, Any]:
    """Parse the latest Get-HotFix install date (no InstalledBy, no full list)."""
    count = 0
    kb = ""
    installed = ""
    description = ""
    in_update = False
    for line in (stdout or "").splitlines():
        if line == "UPDATE_BEGIN":
            in_update = True
            continue
        if line.startswith("COUNT="):
            try:
                count = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                count = 0
            continue
        if not in_update:
            continue
        if line.startswith("KB="):
            kb = line.split("=", 1)[1].strip()
        elif line.startswith("INSTALLED="):
            installed = line.split("=", 1)[1].strip()
        elif line.startswith("DESC="):
            description = line.split("=", 1)[1].strip()
    if len(description) > WINDOWS_UPDATE_DESC_MAX_CHARS:
        description = description[:WINDOWS_UPDATE_DESC_MAX_CHARS]
    return {"count": count, "kb": kb, "installed": installed, "description": description}


def format_windows_update_report(snapshot: dict[str, Any]) -> str:
    kb = str(snapshot.get("kb") or "").strip()
    installed = str(snapshot.get("installed") or "").strip()
    description = str(snapshot.get("description") or "").strip()
    count = int(snapshot.get("count") or 0)
    if not kb and not installed:
        return "No Windows Update install date reported."
    detail = kb or "unknown KB"
    if description:
        detail = f"{detail} — {description}"
    when = installed or "unknown date"
    lines = [f"Last Windows Update install: {when} ({detail})"]
    if count > 1:
        lines.append(f"Hotfixes with an install date: {count} (listing withheld; last install only)")
    return "\n".join(lines)


def parse_timezone_snapshot(stdout: str) -> dict[str, str]:
    """Parse Get-TimeZone / Get-Culture / Get-WinSystemLocale keys."""
    snapshot = {
        "tz_id": "",
        "tz_name": "",
        "tz_std": "",
        "tz_offset": "",
        "tz_dst": "",
        "culture": "",
        "culture_display": "",
        "system_locale": "",
    }
    mapping = (
        ("TZ_ID=", "tz_id"),
        ("TZ_NAME=", "tz_name"),
        ("TZ_STD=", "tz_std"),
        ("TZ_OFFSET=", "tz_offset"),
        ("TZ_DST=", "tz_dst"),
        ("CULTURE_DISPLAY=", "culture_display"),
        ("CULTURE=", "culture"),
        ("SYSTEM_LOCALE=", "system_locale"),
    )
    for line in (stdout or "").splitlines():
        for prefix, key in mapping:
            if line.startswith(prefix):
                snapshot[key] = line.split("=", 1)[1].strip()
                break
    return snapshot


def format_timezone_report(snapshot: dict[str, str]) -> str:
    tz_id = str(snapshot.get("tz_id") or "").strip()
    tz_name = str(snapshot.get("tz_name") or "").strip()
    tz_std = str(snapshot.get("tz_std") or "").strip()
    tz_offset = str(snapshot.get("tz_offset") or "").strip()
    tz_dst = str(snapshot.get("tz_dst") or "").strip().lower()
    culture = str(snapshot.get("culture") or "").strip()
    culture_display = str(snapshot.get("culture_display") or "").strip()
    system_locale = str(snapshot.get("system_locale") or "").strip()
    if not any((tz_id, tz_name, tz_std, culture, system_locale)):
        return "No time zone or locale reported."
    lines: list[str] = []
    if tz_name or tz_id or tz_std:
        label = tz_name or tz_id or tz_std
        extra = f" ({tz_id})" if tz_id and tz_name and tz_id.lower() != tz_name.lower() else ""
        parts = [f"Time zone: {label}{extra}"]
        if tz_offset:
            parts.append(f"offset {tz_offset}")
        if tz_dst in {"true", "1"}:
            parts.append("DST supported")
        elif tz_dst in {"false", "0"}:
            parts.append("DST not supported")
        lines.append("; ".join(parts))
    if culture or culture_display:
        shown = culture_display or culture
        tag = ""
        if culture and culture_display and culture.lower() not in culture_display.lower():
            tag = f" ({culture})"
        lines.append(f"User culture: {shown}{tag}")
    if system_locale:
        lines.append(f"System locale: {system_locale}")
    return "\n".join(lines)


def parse_theme_snapshot(stdout: str) -> dict[str, str]:
    """Parse AppsUseLightTheme / SystemUsesLightTheme keys."""
    snapshot = {"apps_light": "", "system_light": ""}
    mapping = (("APPS_LIGHT=", "apps_light"), ("SYSTEM_LIGHT=", "system_light"))
    for line in (stdout or "").splitlines():
        for prefix, key in mapping:
            if line.startswith(prefix):
                snapshot[key] = line.split("=", 1)[1].strip()
                break
    return snapshot


def format_theme_report(snapshot: dict[str, str]) -> str:
    apps = _theme_label(snapshot.get("apps_light"))
    system = _theme_label(snapshot.get("system_light"))
    if apps is None and system is None:
        return "No theme setting reported."
    lines: list[str] = []
    if apps is not None:
        lines.append(f"Apps: {apps}")
    if system is not None:
        lines.append(f"System chrome: {system}")
    return "\n".join(lines)


def _theme_label(raw: str | None) -> str | None:
    text = str(raw or "").strip().lower()
    if text in {"1", "true"}:
        return "light"
    if text in {"0", "false"}:
        return "dark"
    return None


def parse_volume_snapshot(stdout: str) -> dict[str, str]:
    """Parse default-endpoint volume percent and mute flag."""
    snapshot = {"percent": "", "muted": ""}
    mapping = (("PERCENT=", "percent"), ("MUTED=", "muted"))
    for line in (stdout or "").splitlines():
        for prefix, key in mapping:
            if line.startswith(prefix):
                snapshot[key] = line.split("=", 1)[1].strip()
                break
    return snapshot


def format_volume_report(snapshot: dict[str, str]) -> str:
    percent_raw = str(snapshot.get("percent") or "").strip()
    muted_raw = str(snapshot.get("muted") or "").strip().lower()
    lines: list[str] = []
    if percent_raw:
        try:
            percent = int(percent_raw)
        except ValueError:
            percent = None
        if percent is not None:
            percent = max(0, min(100, percent))
            lines.append(f"Volume: {percent}%")
    if muted_raw in {"1", "true"}:
        lines.append("Muted: yes")
    elif muted_raw in {"0", "false"}:
        lines.append("Muted: no")
    if not lines:
        return "No volume or mute state reported."
    return "\n".join(lines)


def parse_wallpaper_snapshot(stdout: str) -> dict[str, str]:
    """Parse desktop wallpaper path and style keys."""
    snapshot = {"wallpaper": "", "style": "", "tile": ""}
    mapping = (("WALLPAPER=", "wallpaper"), ("STYLE=", "style"), ("TILE=", "tile"))
    for line in (stdout or "").splitlines():
        for prefix, key in mapping:
            if line.startswith(prefix):
                snapshot[key] = line.split("=", 1)[1].strip()
                break
    return snapshot


def format_wallpaper_report(snapshot: dict[str, str]) -> str:
    path = str(snapshot.get("wallpaper") or "").strip()
    style_raw = str(snapshot.get("style") or "").strip()
    tile_raw = str(snapshot.get("tile") or "").strip().lower()
    style = _wallpaper_style_label(style_raw, tile_raw)
    if not path and style is None:
        return "No wallpaper path reported."
    lines: list[str] = []
    if path:
        lines.append(f"Wallpaper: {path}")
    else:
        lines.append("Wallpaper: none (solid color or unset)")
    if style:
        lines.append(f"Style: {style}")
    return "\n".join(lines)


def _wallpaper_style_label(style_raw: str, tile_raw: str) -> str | None:
    if tile_raw in {"1", "true"}:
        return "tile"
    text = str(style_raw or "").strip()
    if not text:
        return None
    labels = {
        "0": "center",
        "2": "stretch",
        "6": "fit",
        "10": "fill",
        "22": "span",
    }
    return labels.get(text)


def parse_idle_snapshot(stdout: str) -> dict[str, str]:
    """Parse last-input idle duration in milliseconds."""
    snapshot = {"idle_ms": ""}
    for line in (stdout or "").splitlines():
        if line.startswith("IDLE_MS="):
            snapshot["idle_ms"] = line.split("=", 1)[1].strip()
    return snapshot


def format_idle_report(snapshot: dict[str, str]) -> str:
    raw = str(snapshot.get("idle_ms") or "").strip()
    if not raw:
        return "No idle time reported."
    try:
        idle_ms = int(raw)
    except ValueError:
        return "No idle time reported."
    if idle_ms < 0:
        idle_ms = 0
    seconds = idle_ms // 1000
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
    if minutes:
        parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
    if secs or not parts:
        parts.append(f"{secs} second" + ("s" if secs != 1 else ""))
    return "Idle for " + " ".join(parts) + "."


def parse_audio_device_snapshot(stdout: str) -> dict[str, str]:
    """Parse the default playback endpoint friendly name."""
    snapshot = {"name": "", "flow": ""}
    mapping = (("NAME=", "name"), ("FLOW=", "flow"))
    for line in (stdout or "").splitlines():
        for prefix, key in mapping:
            if line.startswith(prefix):
                snapshot[key] = line.split("=", 1)[1].strip()
                break
    return snapshot


def format_audio_device_report(snapshot: dict[str, str]) -> str:
    name = str(snapshot.get("name") or "").strip()
    flow = str(snapshot.get("flow") or "").strip().lower() or "playback"
    if not name:
        return "No default playback device reported."
    return f"Default {flow} device: {name}"


def parse_installed_apps_snapshot(stdout: str) -> dict[str, Any]:
    """Parse a capped DisplayName listing from uninstall registry keys."""
    count = 0
    apps: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in (stdout or "").splitlines():
        if line == "APP_BEGIN":
            current = {"name": "", "publisher": ""}
            apps.append(current)
            continue
        if line.startswith("COUNT="):
            try:
                count = int(line.split("=", 1)[1].strip() or "0")
            except ValueError:
                count = 0
            continue
        if current is None:
            continue
        if line.startswith("NAME="):
            current["name"] = line.split("=", 1)[1].strip()[:INSTALLED_APP_NAME_MAX_CHARS]
        elif line.startswith("PUBLISHER="):
            current["publisher"] = line.split("=", 1)[1].strip()[:INSTALLED_APP_PUBLISHER_MAX_CHARS]
    shown = apps[:INSTALLED_APPS_MAX_ITEMS]
    if not count:
        count = len(shown)
    return {"count": count, "apps": shown}


def format_installed_apps_report(snapshot: dict[str, Any]) -> str:
    apps = list(snapshot.get("apps") or [])
    count = int(snapshot.get("count") or len(apps))
    if not apps:
        return "No installed apps reported."
    cap_note = ""
    if count > len(apps):
        cap_note = f" (showing {len(apps)} of {count})"
    lines = [f"Installed apps: {len(apps)}{cap_note}"]
    for item in apps:
        name = str(item.get("name") or "unnamed")
        publisher = str(item.get("publisher") or "").strip()
        if publisher:
            lines.append(f"  {name} — {publisher}")
        else:
            lines.append(f"  {name}")
    return "\n".join(lines)


def parse_hosts_snapshot(text: str) -> dict[str, Any]:
    """Parse IP-to-name mappings from a hosts file; comments are counted, not shown."""
    entries: list[dict[str, Any]] = []
    comment_lines = 0
    extra = 0
    for raw_line in (text or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            comment_lines += 1
            continue
        if "#" in stripped:
            stripped = stripped.split("#", 1)[0].strip()
            if not stripped:
                comment_lines += 1
                continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        address = parts[0][:80]
        names = [name[:120] for name in parts[1:][:8]]
        if len(entries) >= HOSTS_MAX_ENTRIES:
            extra += 1
            continue
        entries.append({"address": address, "names": names})
    return {"entries": entries, "comment_lines": comment_lines, "extra": extra}


def format_hosts_report(snapshot: dict[str, Any]) -> str:
    entries = list(snapshot.get("entries") or [])
    extra = int(snapshot.get("extra") or 0)
    comments = int(snapshot.get("comment_lines") or 0)
    if not entries:
        return "No hosts file mappings reported."
    total = len(entries) + extra
    cap_note = f" (showing {len(entries)} of {total})" if extra else ""
    lines = [f"Hosts mappings: {len(entries)}{cap_note}"]
    for item in entries:
        address = str(item.get("address") or "")
        names = " ".join(str(name) for name in (item.get("names") or []))
        lines.append(f"  {address}  {names}".rstrip())
    if comments:
        lines.append(f"Comment lines skipped: {comments}")
    return "\n".join(lines)


def is_safe_http_url(url: str) -> bool:
    """True for http(s) URLs with a host and no embedded credentials."""
    raw = (url or "").strip()
    if not raw or len(raw) > BROWSER_URL_MAX_CHARS:
        return False
    if any(ch.isspace() for ch in raw):
        return False
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").strip().strip(".")
    return bool(host)


def installed_browser_alias(name: str) -> str | None:
    lowered = name.strip().lower()
    if lowered in INSTALLED_BROWSER_ALIASES:
        if lowered in {"google chrome"}:
            return "chrome"
        if lowered in {"microsoft edge", "msedge"}:
            return "edge"
        return lowered
    return None


def open_in_browser_script(target: str, url: str) -> str:
    """Start-Process the installed browser with one http(s) URL argument."""
    quoted_target = ps_quote(target)
    quoted_url = ps_quote(url)
    return (
        f"$target = {quoted_target}; "
        f"$url = {quoted_url}; "
        "$cmd = Get-Command -Name $target -ErrorAction SilentlyContinue; "
        "if ($cmd) { $target = $cmd.Source }; "
        "try { "
        "  Start-Process -FilePath $target -ArgumentList @($url) -ErrorAction Stop | Out-Null; "
        "  Write-Output \"Opened $url in $target\" "
        "} catch { "
        "  Write-Error $_.Exception.Message; exit 1 "
        "}"
    )


def close_window_script(needle: str) -> str:
    """PowerShell that posts WM_CLOSE via CloseMainWindow — never taskkill."""
    quoted = ps_quote(needle)
    return (
        f"$needle = {quoted}; "
        "$proc = Get-Process | Where-Object { "
        "  $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -and "
        "  ($_.MainWindowTitle -like ('*' + $needle + '*') -or $_.ProcessName -like ('*' + $needle + '*')) "
        "} | Select-Object -First 1; "
        "if (-not $proc) { Write-Error \"No window matched '$needle'\"; exit 1 }; "
        "$sent = $proc.CloseMainWindow(); "
        "if (-not $sent) { Write-Error \"CloseMainWindow failed for '$($proc.MainWindowTitle)'\"; exit 1 }; "
        "Write-Output (\"Sent WM_CLOSE to {0} (pid {1}) title={2}\" "
        "-f $proc.ProcessName, $proc.Id, $proc.MainWindowTitle)"
    )


def _clipboard_arg_reveal(args: dict[str, Any]) -> bool:
    value = args.get("reveal", False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


_CLIPBOARD_PS = (
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "try { $drop = Get-Clipboard -Format FileDropList } catch { $drop = $null }; "
    "if ($drop) { "
    "  $names = @($drop | ForEach-Object { $_.ToString() }); "
    "  Write-Output 'KIND=files'; "
    "  Write-Output ('LENGTH=' + $names.Count); "
    "  $names | Select-Object -First 20 | ForEach-Object { Write-Output ('FILE=' + $_) }; "
    "} else { "
    "  try { $img = Get-Clipboard -Format Image } catch { $img = $null }; "
    "  if ($img) { "
    "    Write-Output 'KIND=image'; "
    "    Write-Output ('WIDTH=' + $img.Width); "
    "    Write-Output ('HEIGHT=' + $img.Height); "
    "  } else { "
    "    try { $text = Get-Clipboard -Raw } catch { $text = $null }; "
    "    if ($null -ne $text -and [string]$text -ne '') { "
    "      Write-Output 'KIND=text'; "
    "      Write-Output ('LENGTH=' + ([string]$text).Length); "
    "      Write-Output 'TEXT_BEGIN'; "
    "      Write-Output ([string]$text); "
    "    } else { "
    "      Write-Output 'KIND=empty'; "
    "      Write-Output 'LENGTH=0'; "
    "    } "
    "  } "
    "}"
)


class DesktopAdapter:
    name = "desktop"

    def execute(self, action: str, args: dict[str, Any], *, dry_run: bool = False) -> StepResult:
        if action == "list_running_apps":
            return self._list_running_apps(dry_run=dry_run)
        if action == "launch_app":
            return self._launch_app(str(args.get("name", "")), dry_run=dry_run)
        if action == "focus_window":
            return self._focus_window(
                str(args.get("title_contains", args.get("name", ""))),
                dry_run=dry_run,
            )
        if action == "inspect_clipboard":
            return self._inspect_clipboard(reveal=_clipboard_arg_reveal(args), dry_run=dry_run)
        if action == "save_clipboard_text":
            return self._save_clipboard_text(str(args.get("path", "")), dry_run=dry_run)
        if action == "speak_text":
            return self._speak_text(str(args.get("text", "")), dry_run=dry_run)
        if action == "capture_screenshot":
            return self._capture_screenshot(
                str(args.get("path", "")),
                str(args.get("window_title", args.get("title_contains", ""))),
                dry_run=dry_run,
            )
        if action == "inspect_network":
            return self._inspect_network(dry_run=dry_run)
        if action == "inspect_battery":
            return self._inspect_battery(dry_run=dry_run)
        if action == "close_window":
            return self._close_window(
                str(args.get("title_contains", args.get("name", ""))),
                dry_run=dry_run,
            )
        if action == "open_in_browser":
            return self._open_in_browser(
                str(args.get("url", "")),
                str(args.get("name", args.get("browser", ""))),
                dry_run=dry_run,
            )
        if action == "inspect_printers":
            return self._inspect_printers(dry_run=dry_run)
        if action == "inspect_startup":
            return self._inspect_startup(dry_run=dry_run)
        if action == "inspect_default_browser":
            return self._inspect_default_browser(dry_run=dry_run)
        if action == "inspect_display":
            return self._inspect_display(dry_run=dry_run)
        if action == "inspect_windows_update":
            return self._inspect_windows_update(dry_run=dry_run)
        if action == "inspect_timezone":
            return self._inspect_timezone(dry_run=dry_run)
        if action == "inspect_theme":
            return self._inspect_theme(dry_run=dry_run)
        if action == "inspect_volume":
            return self._inspect_volume(dry_run=dry_run)
        if action == "inspect_wallpaper":
            return self._inspect_wallpaper(dry_run=dry_run)
        if action == "inspect_idle":
            return self._inspect_idle(dry_run=dry_run)
        if action == "inspect_audio_device":
            return self._inspect_audio_device(dry_run=dry_run)
        if action == "inspect_installed_apps":
            return self._inspect_installed_apps(dry_run=dry_run)
        if action == "inspect_hosts":
            return self._inspect_hosts(dry_run=dry_run)
        return StepResult(
            step_id=new_id("res_"),
            ok=False,
            output="",
            error=f"Unknown desktop action '{action}'",
            dry_run=dry_run,
        )

    def _list_running_apps(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output="[dry-run] Would list running applications with visible windows",
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)

        command = (
            "Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle } | "
            "Sort-Object ProcessName | "
            "Select-Object -First 40 ProcessName, Id, MainWindowTitle | "
            "Format-Table -AutoSize | Out-String -Width 200"
        )
        outcome = run_powershell(command, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error,
            )
        output = outcome.stdout or "(no visible windows found)"
        return StepResult(step_id=new_id("res_"), ok=True, output=output)

    def _launch_app(self, name: str, *, dry_run: bool) -> StepResult:
        if not name.strip():
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="launch_app requires args.name",
                dry_run=dry_run,
            )
        target = resolve_launch_target(name)
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would launch '{target}'",
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)

        quoted = ps_quote(target)
        # Resolve via Get-Command when possible, then Start-Process.
        command = (
            f"$target = {quoted}; "
            "$cmd = Get-Command -Name $target -ErrorAction SilentlyContinue; "
            "if ($cmd) { $target = $cmd.Source }; "
            "try { "
            "  Start-Process -FilePath $target -ErrorAction Stop | Out-Null; "
            "  Write-Output \"Launched: $target\" "
            "} catch { "
            "  Write-Error $_.Exception.Message; exit 1 "
            "}"
        )
        outcome = run_powershell(command, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or f"Failed to launch '{target}'",
            )
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=outcome.stdout or f"Launched '{target}'",
        )

    def _focus_window(self, title_contains: str, *, dry_run: bool) -> StepResult:
        needle = title_contains.strip()
        if not needle:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="focus_window requires args.title_contains or args.name",
                dry_run=dry_run,
            )
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would focus window containing '{needle}'",
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)

        quoted = ps_quote(needle)
        command = (
            "Add-Type -TypeDefinition @'\n"
            "using System;\n"
            "using System.Runtime.InteropServices;\n"
            "public class ArboraWin {\n"
            "  [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd);\n"
            "  [DllImport(\"user32.dll\")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);\n"
            "}\n"
            "'@ -ErrorAction SilentlyContinue; "
            f"$needle = {quoted}; "
            "$proc = Get-Process | Where-Object { "
            "  $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -and "
            "  ($_.MainWindowTitle -like ('*' + $needle + '*') -or $_.ProcessName -like ('*' + $needle + '*')) "
            "} | Select-Object -First 1; "
            "if (-not $proc) { Write-Error \"No window matched '$needle'\"; exit 1 }; "
            "[void][ArboraWin]::ShowWindowAsync($proc.MainWindowHandle, 9); "
            "[void][ArboraWin]::SetForegroundWindow($proc.MainWindowHandle); "
            "Write-Output (\"Focused: {0} (pid {1}) title={2}\" -f $proc.ProcessName, $proc.Id, $proc.MainWindowTitle)"
        )
        outcome = run_powershell(command, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or f"Failed to focus '{needle}'",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=outcome.stdout or f"Focused '{needle}'")

    def _inspect_clipboard(self, *, reveal: bool, dry_run: bool) -> StepResult:
        if dry_run:
            if reveal:
                output = (
                    "[dry-run] Would inspect the clipboard and show a short text preview "
                    "unless it looks like a secret"
                )
            else:
                output = "[dry-run] Would inspect the clipboard (type and length only; content withheld)"
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=output,
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_CLIPBOARD_PS, timeout_seconds=15)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Failed to read the clipboard",
            )
        snapshot = parse_clipboard_snapshot(outcome.stdout)
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=format_clipboard_report(snapshot, reveal=reveal),
        )

    def _save_clipboard_text(self, path_raw: str, *, dry_run: bool) -> StepResult:
        target = path_raw.strip()
        if not target:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="save_clipboard_text requires args.path",
                dry_run=dry_run,
            )
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    f"[dry-run] Would save clipboard text to {target} "
                    "unless empty, non-text, or secret-like"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_CLIPBOARD_PS, timeout_seconds=15)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Failed to read the clipboard",
            )
        snapshot = parse_clipboard_snapshot(outcome.stdout)
        text, error = clipboard_save_payload(snapshot)
        if text is None:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=error)
        path = Path(target).expanduser()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        except PermissionError:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Permission denied writing: {path}",
            )
        except OSError as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Failed to write {path}: {exc}",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=f"Saved clipboard text to {path}")

    def _speak_text(self, text: str, *, dry_run: bool) -> StepResult:
        spoken = sanitize_speech_text(text)
        if not spoken:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="speak_text requires args.text",
                dry_run=dry_run,
            )
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would speak: {spoken}",
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        result = speak_text(spoken)
        if not result.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=result.error or "Spoken output failed",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=f"Spoke: {result.text}")

    def _capture_screenshot(self, path_raw: str, window_title: str, *, dry_run: bool) -> StepResult:
        target = path_raw.strip()
        needle = window_title.strip()
        if not target:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="capture_screenshot requires args.path",
                dry_run=dry_run,
            )
        if dry_run:
            scope = f"window matching '{needle}'" if needle else "the primary screen"
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=f"[dry-run] Would capture {scope} to {target}",
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        quoted_path = ps_quote(target)
        if needle:
            quoted_title = ps_quote(needle)
            command = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "Add-Type -AssemblyName System.Drawing; "
                "Add-Type -TypeDefinition @'\n"
                "using System;\n"
                "using System.Runtime.InteropServices;\n"
                "public class ArboraShot {\n"
                "  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }\n"
                "  [DllImport(\"user32.dll\")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);\n"
                "}\n"
                "'@ -ErrorAction SilentlyContinue; "
                f"$needle = {quoted_title}; "
                "$proc = Get-Process | Where-Object { "
                "  $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -and "
                "  $_.MainWindowTitle -like ('*' + $needle + '*') "
                "} | Select-Object -First 1; "
                "if (-not $proc) { Write-Error \"No window matched '$needle'\"; exit 1 }; "
                "$rect = New-Object ArboraShot+RECT; "
                "[void][ArboraShot]::GetWindowRect($proc.MainWindowHandle, [ref]$rect); "
                "$w = [Math]::Max(1, $rect.Right - $rect.Left); "
                "$h = [Math]::Max(1, $rect.Bottom - $rect.Top); "
                "$bmp = New-Object System.Drawing.Bitmap $w, $h; "
                "$g = [System.Drawing.Graphics]::FromImage($bmp); "
                "$g.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size $w, $h)); "
                f"$path = {quoted_path}; "
                "$dir = Split-Path -Parent $path; "
                "if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }; "
                "$bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png); "
                "$g.Dispose(); $bmp.Dispose(); "
                "Write-Output (\"Saved window screenshot: $path title=$($proc.MainWindowTitle)\")"
            )
        else:
            command = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "Add-Type -AssemblyName System.Drawing; "
                "$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                "$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height; "
                "$g = [System.Drawing.Graphics]::FromImage($bmp); "
                "$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size); "
                f"$path = {quoted_path}; "
                "$dir = Split-Path -Parent $path; "
                "if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }; "
                "$bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png); "
                "$g.Dispose(); $bmp.Dispose(); "
                "Write-Output (\"Saved screenshot: $path\")"
            )
        outcome = run_powershell(command, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Screenshot capture failed",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=outcome.stdout or f"Saved screenshot: {target}")

    def _inspect_network(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would list network adapters, IPv4 addresses, and connection "
                    "profiles (no Wi-Fi keys or passwords)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        command = (
            "$ErrorActionPreference = 'SilentlyContinue'; "
            "Write-Output '=== Adapters ==='; "
            "Get-NetAdapter | Select-Object -First 20 Name, Status, LinkSpeed, MacAddress | "
            "Format-Table -AutoSize | Out-String -Width 200; "
            "Write-Output '=== IPv4 ==='; "
            "Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
            "Where-Object { $_.IPAddress -notlike '127.*' } | "
            "Select-Object -First 20 InterfaceAlias, IPAddress, PrefixLength | "
            "Format-Table -AutoSize | Out-String -Width 200; "
            "Write-Output '=== Connection profiles ==='; "
            "Get-NetConnectionProfile | Select-Object Name, InterfaceAlias, NetworkCategory | "
            "Format-Table -AutoSize | Out-String -Width 200"
        )
        outcome = run_powershell(command, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Network inspect failed",
            )
        text = outcome.stdout or "(no adapter data)"
        lowered = text.lower()
        if "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a Wi-Fi key",
            )
        return StepResult(step_id=new_id("res_"), ok=True, output=text)

    def _inspect_battery(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would read battery charge and AC/chassis status "
                    "(no serials, passwords, or powercfg reports)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_BATTERY_PS, timeout_seconds=20)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Battery inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_battery_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_battery_report(snapshot))

    def _close_window(self, title_contains: str, *, dry_run: bool) -> StepResult:
        needle = title_contains.strip()
        if not needle:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="close_window requires args.title_contains or args.name",
                dry_run=dry_run,
            )
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    f"[dry-run] Would send WM_CLOSE to a window matching '{needle}' "
                    "(CloseMainWindow; not a force-kill)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        command = close_window_script(needle)
        lowered = command.lower()
        if "taskkill" in lowered or "stop-process" in lowered or ".kill(" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to run a close script that looks like a force-kill",
            )
        outcome = run_powershell(command, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or f"Failed to close window matching '{needle}'",
            )
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=outcome.stdout or f"Sent WM_CLOSE to window matching '{needle}'",
        )

    def _open_in_browser(self, url: str, name: str, *, dry_run: bool) -> StepResult:
        raw_url = url.strip()
        alias = installed_browser_alias(name)
        if not raw_url:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="open_in_browser requires args.url",
                dry_run=dry_run,
            )
        if alias is None:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="open_in_browser requires args.name (chrome, edge, or firefox)",
                dry_run=dry_run,
            )
        if not is_safe_http_url(raw_url):
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="open_in_browser only accepts http(s) URLs without credentials",
                dry_run=dry_run,
            )
        target = resolve_launch_target(alias)
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    f"[dry-run] Would open {raw_url} in installed {alias} "
                    f"({target}; Start-Process, not Playwright)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        command = open_in_browser_script(target, raw_url)
        outcome = run_powershell(command, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or f"Failed to open URL in {alias}",
            )
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=outcome.stdout or f"Opened {raw_url} in {alias}",
        )

    def _inspect_printers(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would list installed printers and the default printer "
                    "(no print jobs, driver paths, or secrets)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_PRINTER_PS, timeout_seconds=20)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Printer inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_printer_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_printer_report(snapshot))

    def _inspect_startup(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would list HKCU/HKLM Run names and the user Startup folder "
                    "(no enable/disable, no Task Scheduler, no secrets)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_STARTUP_PS, timeout_seconds=20)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Startup inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_startup_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_startup_report(snapshot))

    def _inspect_default_browser(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would read the default http(s) browser ProgId "
                    "(no Hash, no association changes)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_DEFAULT_BROWSER_PS, timeout_seconds=20)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Default browser inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_default_browser_snapshot(text)
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=format_default_browser_report(snapshot),
        )

    def _inspect_display(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would list attached displays and their resolutions "
                    "(no mode changes, no DPI writes)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_DISPLAY_PS, timeout_seconds=20)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Display inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_display_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_display_report(snapshot))

    def _inspect_windows_update(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would read the last Get-HotFix install date "
                    "(no install, no scan, no full KB dump)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_WINDOWS_UPDATE_PS, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Windows Update inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_windows_update_snapshot(text)
        return StepResult(
            step_id=new_id("res_"),
            ok=True,
            output=format_windows_update_report(snapshot),
        )

    def _inspect_timezone(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would read the current time zone and locale "
                    "(no tzutil /s, no Set-TimeZone or Set-Culture)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_TIMEZONE_PS, timeout_seconds=20)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Time zone inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_timezone_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_timezone_report(snapshot))

    def _inspect_theme(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would read the Windows light/dark theme "
                    "(no Set-ItemProperty, no personalization writes)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_THEME_PS, timeout_seconds=20)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Theme inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_theme_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_theme_report(snapshot))

    def _inspect_volume(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would read the default playback volume and mute state "
                    "(no SetMasterVolumeLevelScalar, no mute toggle)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_VOLUME_PS, timeout_seconds=20)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Volume inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_volume_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_volume_report(snapshot))

    def _inspect_wallpaper(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would read the desktop wallpaper path "
                    "(no SystemParametersInfo SPI_SETDESKWALLPAPER, no personalization writes)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_WALLPAPER_PS, timeout_seconds=20)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Wallpaper inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_wallpaper_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_wallpaper_report(snapshot))

    def _inspect_idle(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would read last-input idle time "
                    "(no BlockInput, no SendInput, no key or mouse injection)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_IDLE_PS, timeout_seconds=20)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Idle inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_idle_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_idle_report(snapshot))

    def _inspect_audio_device(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would read the default playback device friendly name "
                    "(no SetDefaultEndpoint, no PolicyConfig, no device switches)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_AUDIO_DEVICE_PS, timeout_seconds=20)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Audio device inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_audio_device_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_audio_device_report(snapshot))

    def _inspect_installed_apps(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    f"[dry-run] Would list up to {INSTALLED_APPS_MAX_ITEMS} installed app names "
                    "from uninstall registry keys (no appwiz.cpl, no Win32_Product, no uninstall)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        outcome = run_powershell(_INSTALLED_APPS_PS, timeout_seconds=30)
        if not outcome.ok:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output=outcome.stdout,
                error=outcome.error or "Installed apps inspect failed",
            )
        text = outcome.stdout or ""
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_installed_apps_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_installed_apps_report(snapshot))

    def _inspect_hosts(self, *, dry_run: bool) -> StepResult:
        if dry_run:
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output=(
                    "[dry-run] Would read the Windows hosts file mappings "
                    "(no Set-Content, no Add-Content, no notepad edit)"
                ),
                dry_run=True,
            )
        platform_error = require_windows()
        if platform_error:
            return StepResult(step_id=new_id("res_"), ok=False, output="", error=platform_error)
        path = windows_hosts_path()
        if not path.is_file():
            return StepResult(
                step_id=new_id("res_"),
                ok=True,
                output="Hosts file not found.",
            )
        try:
            data = path.read_bytes()
        except OSError as exc:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error=f"Failed to read hosts file: {exc}",
            )
        if len(data) > HOSTS_MAX_BYTES:
            data = data[:HOSTS_MAX_BYTES]
        text = data.decode("utf-8", errors="replace")
        lowered = text.lower()
        if "password" in lowered or "key content" in lowered or "keycontent" in lowered:
            return StepResult(
                step_id=new_id("res_"),
                ok=False,
                output="",
                error="Refusing to return output that looks like a secret",
            )
        snapshot = parse_hosts_snapshot(text)
        return StepResult(step_id=new_id("res_"), ok=True, output=format_hosts_report(snapshot))
