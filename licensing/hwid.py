import hashlib
import os
import platform
import subprocess
import sys

def _get_registry_machine_guid() -> str:
    """Retrieve Windows MachineGuid from Registry."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        )
        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return str(value).strip()
    except Exception:
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ
            )
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            return str(value).strip()
        except Exception:
            return ""

def _get_wmi_uuid() -> str:
    """Retrieve Motherboard UUID via PowerShell / WMIC."""
    if platform.system().lower() != "windows":
        return ""
    
    # Try PowerShell CimInstance
    try:
        cmd = ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystemProduct).UUID"]
        out = subprocess.check_output(cmd, creationflags=0x08000000 if sys.platform == "win32" else 0, timeout=3)
        uuid_str = out.decode("utf-8", errors="ignore").strip()
        if uuid_str and len(uuid_str) > 8 and "000000" not in uuid_str.lower():
            return uuid_str
    except Exception:
        pass

    # Try wmic fallback
    try:
        cmd = ["wmic", "csproduct", "get", "uuid"]
        out = subprocess.check_output(cmd, creationflags=0x08000000 if sys.platform == "win32" else 0, timeout=3)
        lines = [line.strip() for line in out.decode("utf-8", errors="ignore").splitlines() if line.strip()]
        if len(lines) >= 2:
            return lines[1]
    except Exception:
        pass
    
    return ""

def _get_cpu_id() -> str:
    """Retrieve Processor ID via PowerShell."""
    if platform.system().lower() != "windows":
        return platform.processor() or ""
    
    try:
        cmd = ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).ProcessorId"]
        out = subprocess.check_output(cmd, creationflags=0x08000000 if sys.platform == "win32" else 0, timeout=3)
        cpu_str = out.decode("utf-8", errors="ignore").strip()
        if cpu_str:
            return cpu_str
    except Exception:
        pass
    return platform.processor() or ""

def get_hardware_id() -> str:
    """
    Generate a unique, stable, deterministic Hardware Fingerprint (HWID)
    bound to the specific PC device.
    Format: DOLA-XXXX-XXXX-XXXX-XXXX
    """
    components = []
    
    # 1. Machine GUID (Very stable per Windows installation)
    machine_guid = _get_registry_machine_guid()
    if machine_guid:
        components.append(f"MG:{machine_guid}")
    
    # 2. Motherboard UUID
    mobo_uuid = _get_wmi_uuid()
    if mobo_uuid:
        components.append(f"UUID:{mobo_uuid}")
        
    # 3. CPU ID
    cpu_id = _get_cpu_id()
    if cpu_id:
        components.append(f"CPU:{cpu_id}")
        
    # Fallback if bare minimum
    if not components:
        node_name = platform.node()
        system_str = platform.system() + platform.version()
        components.append(f"FB:{node_name}:{system_str}")
        
    raw_hwid_string = "||".join(components)
    
    # Hash to SHA-256
    hash_digest = hashlib.sha256(raw_hwid_string.encode("utf-8")).hexdigest().upper()
    
    # Format into 4 chunks: DOLA-XXXX-XXXX-XXXX-XXXX
    formatted_hwid = f"DOLA-{hash_digest[:4]}-{hash_digest[4:8]}-{hash_digest[8:12]}-{hash_digest[12:16]}"
    return formatted_hwid

if __name__ == "__main__":
    hwid = get_hardware_id()
    print(f"Generated Hardware ID: {hwid}")
