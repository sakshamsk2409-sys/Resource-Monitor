import os
import json
import datetime
import platform
import socket
import psutil
import webbrowser

try:
    import pynvml
    HAS_PYNVML = True
except ImportError:
    pynvml = None
    HAS_PYNVML = False


def export_system_report(output_dir=None):
    if not output_dir:
        output_dir = os.getcwd()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    html_file = os.path.join(output_dir, f"system_report_{timestamp}.html")
    json_file = os.path.join(output_dir, f"system_report_{timestamp}.json")

    # Gather Data
    hostname = socket.gethostname()
    os_name = f"{platform.system()} {platform.release()} ({platform.machine()})"
    cpu_model = platform.processor() or "x86/x64 Family Processor"
    cores_phys = psutil.cpu_count(logical=False) or "N/A"
    cores_log = psutil.cpu_count(logical=True) or "N/A"
    cpu_usage = psutil.cpu_percent(interval=0.5)

    vm = psutil.virtual_memory()
    ram_total_gb = vm.total / (1024**3)
    ram_used_gb = vm.used / (1024**3)
    ram_avail_gb = vm.available / (1024**3)
    ram_pct = vm.percent

    # GPU
    gpu_name = "N/A"
    gpu_vram = "N/A"
    if HAS_PYNVML and pynvml:
        try:
            pynvml.nvmlInit()
            if pynvml.nvmlDeviceGetCount() > 0:
                h = pynvml.nvmlDeviceGetHandleByIndex(0)
                gpu_name = pynvml.nvmlDeviceGetName(h)
                if isinstance(gpu_name, bytes):
                    gpu_name = gpu_name.decode("utf-8", errors="ignore")
                mem = pynvml.nvmlDeviceGetMemoryInfo(h)
                gpu_vram = f"{mem.used / (1024**3):.2f} GB / {mem.total / (1024**3):.2f} GB"
        except Exception:
            pass

    # Drives
    drives = []
    try:
        for p in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(p.mountpoint)
                drives.append({
                    "mount": p.mountpoint,
                    "fstype": p.fstype,
                    "total_gb": round(u.total / (1024**3), 1),
                    "used_gb": round(u.used / (1024**3), 1),
                    "free_gb": round(u.free / (1024**3), 1),
                    "percent": u.percent,
                })
            except Exception:
                continue
    except Exception:
        pass

    # Processes Top 10
    top_processes = []
    for proc in psutil.process_iter():
        try:
            name = proc.name()
            pid = proc.pid
            mem_mb = proc.memory_info().rss / (1024 * 1024)
            cpu = proc.cpu_percent(interval=None)
            top_processes.append({"pid": pid, "name": name, "cpu": cpu, "mem_mb": round(mem_mb, 1)})
        except Exception:
            continue

    top_processes = sorted(top_processes, key=lambda x: x["mem_mb"], reverse=True)[:10]

    report_data = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hostname": hostname,
        "os": os_name,
        "cpu_model": cpu_model,
        "cores_physical": cores_phys,
        "cores_logical": cores_log,
        "cpu_usage_pct": cpu_usage,
        "ram": {
            "total_gb": round(ram_total_gb, 2),
            "used_gb": round(ram_used_gb, 2),
            "available_gb": round(ram_avail_gb, 2),
            "percent": ram_pct,
        },
        "gpu": {"name": str(gpu_name), "vram": gpu_vram},
        "drives": drives,
        "top_processes": top_processes,
    }

    # Save JSON
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    # Build HTML Report
    drives_rows = "".join([
        f"<tr><td><b>{d['mount']}</b></td><td>{d['fstype']}</td><td>{d['total_gb']} GB</td><td>{d['used_gb']} GB</td><td>{d['free_gb']} GB</td><td><b style='color:{'#e53935' if d['percent']>85 else '#55d66f'}'>{d['percent']}%</b></td></tr>"
        for d in drives
    ])

    proc_rows = "".join([
        f"<tr><td>{p['pid']}</td><td><b>{p['name']}</b></td><td>{p['cpu']}%</td><td>{p['mem_mb']} MB</td></tr>"
        for p in top_processes
    ])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>System Diagnostic Report - {hostname}</title>
    <style>
        body {{ background-color: #080808; color: #dddddd; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 30px; }}
        h1 {{ color: #ff8f00; letter-spacing: 1px; margin-bottom: 5px; }}
        .subtitle {{ color: #888888; font-size: 13px; margin-bottom: 25px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 25px; }}
        .card {{ background-color: #111111; border: 1px solid #282828; border-radius: 6px; padding: 20px; }}
        .card h3 {{ color: #ffaa00; margin-top: 0; border-bottom: 1px solid #222; padding-bottom: 8px; font-size: 14px; text-transform: uppercase; }}
        .row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #181818; font-size: 12px; }}
        .val {{ font-weight: bold; color: #ffffff; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #222222; }}
        th {{ background-color: #181818; color: #ff8f00; text-transform: uppercase; font-size: 11px; }}
        tr:hover {{ background-color: #161616; }}
        .badge {{ background: #26a69a; color: #000; padding: 3px 8px; border-radius: 3px; font-weight: bold; font-size: 11px; }}
    </style>
</head>
<body>
    <h1>SYSTEM DIAGNOSTIC & TELEMETRY REPORT</h1>
    <div class="subtitle">Generated on {report_data['timestamp']} for Host: <b>{hostname}</b> <span class="badge">STATUS: OK</span></div>

    <div class="grid">
        <div class="card">
            <h3>Hardware Overview</h3>
            <div class="row"><span>Operating System</span><span class="val">{os_name}</span></div>
            <div class="row"><span>Processor</span><span class="val">{cpu_model}</span></div>
            <div class="row"><span>Cores / Threads</span><span class="val">{cores_phys} Cores / {cores_log} Threads</span></div>
            <div class="row"><span>GPU Model</span><span class="val">{gpu_name}</span></div>
        </div>

        <div class="card">
            <h3>Live Telemetry Snapshot</h3>
            <div class="row"><span>CPU Usage</span><span class="val" style="color:{'#e53935' if cpu_usage > 85 else '#55d66f'}">{cpu_usage}%</span></div>
            <div class="row"><span>Total RAM</span><span class="val">{ram_total_gb:.2f} GB</span></div>
            <div class="row"><span>RAM Usage</span><span class="val">{ram_used_gb:.2f} GB ({ram_pct}%)</span></div>
            <div class="row"><span>GPU VRAM</span><span class="val">{gpu_vram}</span></div>
        </div>
    </div>

    <div class="card" style="margin-bottom: 25px;">
        <h3>Storage Devices & Partitions</h3>
        <table>
            <thead>
                <tr><th>Mount Point</th><th>File System</th><th>Total Capacity</th><th>Used Space</th><th>Free Space</th><th>Usage %</th></tr>
            </thead>
            <tbody>
                {drives_rows}
            </tbody>
        </table>
    </div>

    <div class="card">
        <h3>Top Memory Consuming Processes</h3>
        <table>
            <thead>
                <tr><th>PID</th><th>Process Name</th><th>CPU %</th><th>Memory (MB)</th></tr>
            </thead>
            <tbody>
                {proc_rows}
            </tbody>
        </table>
    </div>
</body>
</html>"""

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    try:
        webbrowser.open(f"file:///{os.path.abspath(html_file)}")
    except Exception:
        pass

    return html_file, json_file
