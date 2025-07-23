#!/usr/bin/env python3
"""
Fedimint log analysis tool for regression testing
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

def parse_timestamp(line: str) -> Optional[datetime]:
    """Extract timestamp from log line"""
    # Look for various timestamp formats
    patterns = [
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)',  # ISO format
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)',   # Standard format
        r'(\d{2}:\d{2}:\d{2}\.\d+)',                      # Time only
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            timestamp_str = match.group(1)
            try:
                if 'T' in timestamp_str:
                    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                elif ' ' in timestamp_str:
                    return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                else:
                    # Time only - assume today's date
                    time_part = datetime.strptime(timestamp_str, '%H:%M:%S.%f').time()
                    return datetime.combine(datetime.now().date(), time_part)
            except ValueError:
                continue
    return None

def analyze_log_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a single log file"""
    results = {
        'file': str(file_path),
        'error_count': 0,
        'warn_count': 0,
        'first_timestamp': None,
        'last_timestamp': None,
        'duration_seconds': None,
        'success': False,
        'notable_issues': []
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        results['notable_issues'].append(f"Failed to read file: {e}")
        return results
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Count errors and warnings
        if 'ERROR' in line:
            results['error_count'] += 1
        if 'WARN' in line:
            results['warn_count'] += 1
            
        # Extract timestamps
        timestamp = parse_timestamp(line)
        if timestamp:
            if results['first_timestamp'] is None:
                results['first_timestamp'] = timestamp
            results['last_timestamp'] = timestamp
            
        # Check for success indicators - JSON response with "joined" field
        if '"joined"' in line:
            results['success'] = True
            
        # Check for notable issues
        if 'disco box' in line.lower():
            results['notable_issues'].append('Disco box error')
        if 'dns.iroh.link' in line.lower():
            results['notable_issues'].append('DNS resolution failure')
        if 'pkarr publish error' in line.lower():
            results['notable_issues'].append('PKarr protocol error')
        if 'failed to open disco box' in line.lower():
            results['notable_issues'].append('Failed to open disco box')
    
    # Calculate duration
    if results['first_timestamp'] and results['last_timestamp']:
        duration = results['last_timestamp'] - results['first_timestamp']
        results['duration_seconds'] = duration.total_seconds()
    
    # Convert timestamps to strings for JSON serialization
    if results['first_timestamp']:
        results['first_timestamp'] = results['first_timestamp'].isoformat()
    if results['last_timestamp']:
        results['last_timestamp'] = results['last_timestamp'].isoformat()
    
    return results

def analyze_test_run(run_dir: Path) -> Dict[str, Any]:
    """Analyze a single test run directory"""
    results = {
        'run_dir': str(run_dir),
        'cli_analysis': None,
        'peer_analysis': None
    }
    
    # Find CLI and peer log files
    cli_files = list(run_dir.glob('*fedimint-cli*.log'))
    peer_files = list(run_dir.glob('*fedimintd-peer0*.log'))
    
    if cli_files:
        results['cli_analysis'] = analyze_log_file(cli_files[0])
    if peer_files:
        results['peer_analysis'] = analyze_log_file(peer_files[0])
    
    return results

def analyze_version_directory(version_dir: Path) -> Dict[str, Any]:
    """Analyze all test runs in a version directory"""
    results = {
        'version_dir': str(version_dir),
        'test_runs': [],
        'summary': {
            'total_runs': 0,
            'successful_runs': 0,
            'avg_duration': None,
            'median_duration': None,
            'min_duration': None,
            'max_duration': None,
            'total_errors': 0,
            'total_warnings': 0
        }
    }
    
    # Find all test run directories
    test_dirs = sorted([d for d in version_dir.iterdir() if d.is_dir() and d.name.startswith('test-run')])
    
    durations = []
    for test_dir in test_dirs:
        run_analysis = analyze_test_run(test_dir)
        results['test_runs'].append(run_analysis)
        
        # Update summary statistics
        results['summary']['total_runs'] += 1
        
        if run_analysis['cli_analysis']:
            cli = run_analysis['cli_analysis']
            if cli['success']:
                results['summary']['successful_runs'] += 1
            if cli['duration_seconds'] is not None:
                durations.append(cli['duration_seconds'])
            results['summary']['total_errors'] += cli['error_count']
            results['summary']['total_warnings'] += cli['warn_count']
        
        if run_analysis['peer_analysis']:
            peer = run_analysis['peer_analysis']
            results['summary']['total_errors'] += peer['error_count']
            results['summary']['total_warnings'] += peer['warn_count']
    
    # Calculate duration statistics
    if durations:
        sorted_durations = sorted(durations)
        results['summary']['avg_duration'] = sum(durations) / len(durations)
        results['summary']['median_duration'] = sorted_durations[len(sorted_durations) // 2]
        results['summary']['min_duration'] = sorted_durations[0]
        results['summary']['max_duration'] = sorted_durations[-1]
    
    return results

def main():
    """Main analysis function"""
    base_dir = Path('.')
    
    # Analyze each version directory
    versions = ['baseline', 'v0.8.0-beta.2', 'v0.8.0-beta.2-with-n0-infra', 'v0.8.0-beta.2-n0-only-infra']
    results = {}
    
    for version in versions:
        version_path = base_dir / version
        if version_path.exists():
            print(f"Analyzing {version}...")
            results[version] = analyze_version_directory(version_path)
        else:
            print(f"Directory {version} not found")
    
    # Save results to JSON
    with open('log_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary report
    print("\n" + "="*60)
    print("FEDIMINT LOG ANALYSIS SUMMARY")
    print("="*60)
    
    for version, data in results.items():
        print(f"\n{version.upper()}")
        print("-" * 40)
        summary = data['summary']
        print(f"Total runs: {summary['total_runs']}")
        print(f"Successful runs: {summary['successful_runs']}")
        print(f"Success rate: {summary['successful_runs']}/{summary['total_runs']} ({summary['successful_runs']/summary['total_runs']*100:.1f}%)")
        if summary['avg_duration']:
            print(f"Join duration statistics:")
            print(f"  Average: {summary['avg_duration']:.2f}s")
            print(f"  Median: {summary['median_duration']:.2f}s")
            print(f"  Min: {summary['min_duration']:.2f}s")
            print(f"  Max: {summary['max_duration']:.2f}s")
        else:
            print("Join duration: N/A")
        print(f"Total errors: {summary['total_errors']}")
        print(f"Total warnings: {summary['total_warnings']}")
    
    # Comparative analysis
    if 'baseline' in results:
        baseline = results['baseline']['summary']
        print(f"\nCOMPARATIVE ANALYSIS (vs baseline)")
        print("-" * 40)
        
        for version in ['v0.8.0-beta.2', 'v0.8.0-beta.2-with-n0-infra', 'v0.8.0-beta.2-n0-only-infra']:
            if version in results:
                test_summary = results[version]['summary']
                print(f"\n{version}:")
                
                # Duration comparison
                if baseline['avg_duration'] and test_summary['avg_duration']:
                    duration_diff = test_summary['avg_duration'] - baseline['avg_duration']
                    duration_pct = (duration_diff / baseline['avg_duration']) * 100
                    print(f"  Duration change: {duration_diff:+.2f}s ({duration_pct:+.1f}%)")
                
                # Error/warning comparison
                error_diff = test_summary['total_errors'] - baseline['total_errors']
                warn_diff = test_summary['total_warnings'] - baseline['total_warnings']
                print(f"  Error change: {error_diff:+d}")
                print(f"  Warning change: {warn_diff:+d}")
                
                # Success rate comparison
                baseline_rate = baseline['successful_runs'] / baseline['total_runs'] * 100
                test_rate = test_summary['successful_runs'] / test_summary['total_runs'] * 100
                rate_diff = test_rate - baseline_rate
                print(f"  Success rate change: {rate_diff:+.1f}%")

if __name__ == "__main__":
    main()