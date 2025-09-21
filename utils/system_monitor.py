"""
System Monitor Module
Provides functions to monitor system resources like CPU, memory, and processes.
"""

import psutil
import time
import platform
import os
from datetime import datetime

def get_cpu_usage():
    """
    Get CPU usage information.
    
    Returns:
        dict: CPU usage information including percentage and per-core stats
    """
    try:
        # Get CPU usage percentage (wait a short interval for accurate measurement)
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Get per-core CPU usage
        per_cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
        
        # Get CPU frequency
        cpu_freq = psutil.cpu_freq()
        current_freq = cpu_freq.current if cpu_freq else 0
        
        # Get CPU count
        physical_cores = psutil.cpu_count(logical=False)
        total_cores = psutil.cpu_count(logical=True)
        
        return {
            'percent': cpu_percent,
            'per_cpu_percent': per_cpu_percent,
            'current_freq': current_freq,
            'physical_cores': physical_cores,
            'total_cores': total_cores
        }
    except Exception as e:
        return {
            'error': str(e),
            'percent': 0,
            'per_cpu_percent': [],
            'current_freq': 0,
            'physical_cores': 0,
            'total_cores': 0
        }

def get_memory_usage():
    """
    Get memory usage information.
    
    Returns:
        dict: Memory usage information including RAM and swap
    """
    try:
        # Get virtual memory information
        memory = psutil.virtual_memory()
        
        # Get swap memory information
        swap = psutil.swap_memory()
        
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'free': memory.free,
            'percent': memory.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_free': swap.free,
            'swap_percent': swap.percent
        }
    except Exception as e:
        return {
            'error': str(e),
            'total': 0,
            'available': 0,
            'used': 0,
            'free': 0,
            'percent': 0,
            'swap_total': 0,
            'swap_used': 0,
            'swap_free': 0,
            'swap_percent': 0
        }

def get_process_count():
    """
    Get the number of running processes.
    
    Returns:
        int: Number of running processes
    """
    try:
        return len(list(psutil.process_iter()))
    except Exception:
        return 0

def get_top_processes(limit=10):
    """
    Get information about top processes by CPU usage.
    
    Args:
        limit (int): Maximum number of processes to return
        
    Returns:
        list: List of dictionaries containing process information
    """
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time', 'status']):
            try:
                pinfo = proc.info
                
                # Update CPU usage
                proc.cpu_percent(interval=0)
                
                # Get process creation time
                create_time = datetime.fromtimestamp(pinfo['create_time']).strftime('%Y-%m-%d %H:%M:%S') if pinfo['create_time'] else 'N/A'
                
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'username': pinfo['username'],
                    'cpu_percent': pinfo['cpu_percent'],
                    'memory_percent': pinfo['memory_percent'],
                    'create_time': create_time,
                    'status': pinfo['status']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort processes by CPU usage and limit the number
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        return processes[:limit]
    except Exception as e:
        return [{'error': str(e)}]

def get_disk_usage():
    """
    Get disk usage information.
    
    Returns:
        list: List of dictionaries containing disk usage information
    """
    try:
        disk_info = []
        for partition in psutil.disk_partitions(all=False):
            if os.name == 'nt' and ('cdrom' in partition.opts or partition.fstype == ''):
                # Skip CD-ROM drives on Windows
                continue
            
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except (PermissionError, FileNotFoundError):
                # Some mountpoints may not be accessible
                pass
        
        return disk_info
    except Exception as e:
        return [{'error': str(e)}]

def get_network_info():
    """
    Get network information.
    
    Returns:
        dict: Network information including bytes sent and received
    """
    try:
        # Get network I/O statistics
        net_io = psutil.net_io_counters()
        
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errin': net_io.errin,
            'errout': net_io.errout,
            'dropin': net_io.dropin,
            'dropout': net_io.dropout
        }
    except Exception as e:
        return {'error': str(e)}

def get_system_info():
    """
    Get general system information.
    
    Returns:
        dict: System information including OS, hostname, uptime, etc.
    """
    try:
        # Get system uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        # Format uptime
        days, remainder = divmod(uptime.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        return {
            'system': platform.system(),
            'node': platform.node(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'boot_time': boot_time.strftime('%Y-%m-%d %H:%M:%S'),
            'uptime': uptime_str
        }
    except Exception as e:
        return {'error': str(e)}

def get_all_metrics():
    """
    Get all system metrics in a single call.
    
    Returns:
        dict: All system metrics
    """
    return {
        'cpu': get_cpu_usage(),
        'memory': get_memory_usage(),
        'process_count': get_process_count(),
        'top_processes': get_top_processes(),
        'disk': get_disk_usage(),
        'network': get_network_info(),
        'system': get_system_info(),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
