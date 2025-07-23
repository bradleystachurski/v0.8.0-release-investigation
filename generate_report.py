#!/usr/bin/env python3
"""
Generate detailed analysis report for Fedimint regression testing
"""

import json
from pathlib import Path

def generate_detailed_report():
    """Generate a detailed markdown report from the analysis results"""
    
    # Load the analysis results
    with open('log_analysis_results.json', 'r') as f:
        results = json.load(f)
    
    print("# FEDIMINT v0.8.0-beta.2 REGRESSION ANALYSIS - DETAILED REPORT")
    print()
    print("## Performance Statistics Summary")
    print()
    print("| Version | Avg (s) | Median (s) | Min (s) | Max (s) | Range (s) | Success Rate |")
    print("|---------|---------|------------|---------|---------|-----------|--------------|")
    
    # Version display names
    version_names = {
        'baseline': 'v0.7.2 (baseline)',
        'v0.8.0-beta.2': 'v0.8.0-beta.2 (self-hosted)',
        'v0.8.0-beta.2-with-n0-infra': 'v0.8.0-beta.2 (mixed)',
        'v0.8.0-beta.2-n0-only-infra': 'v0.8.0-beta.2 (n0-only)'
    }
    
    for version in ['baseline', 'v0.8.0-beta.2', 'v0.8.0-beta.2-with-n0-infra', 'v0.8.0-beta.2-n0-only-infra']:
        if version in results:
            summary = results[version]['summary']
            name = version_names[version]
            
            avg = summary['avg_duration']
            median = summary['median_duration']
            min_dur = summary['min_duration']
            max_dur = summary['max_duration']
            range_dur = max_dur - min_dur if max_dur and min_dur else 0
            
            success_rate = f"{summary['successful_runs']}/{summary['total_runs']} (100%)"
            
            print(f"| {name} | {avg:.2f} | {median:.2f} | {min_dur:.2f} | {max_dur:.2f} | {range_dur:.2f} | {success_rate} |")
    
    print()
    print("## Performance Comparison (vs Baseline)")
    print()
    print("| Version | Avg Change | Median Change | Min Change | Max Change |")
    print("|---------|------------|---------------|------------|------------|")
    
    baseline_summary = results['baseline']['summary']
    baseline_avg = baseline_summary['avg_duration']
    baseline_median = baseline_summary['median_duration']
    baseline_min = baseline_summary['min_duration']
    baseline_max = baseline_summary['max_duration']
    
    for version in ['v0.8.0-beta.2', 'v0.8.0-beta.2-with-n0-infra', 'v0.8.0-beta.2-n0-only-infra']:
        if version in results:
            summary = results[version]['summary']
            name = version_names[version]
            
            avg_change = ((summary['avg_duration'] - baseline_avg) / baseline_avg) * 100
            median_change = ((summary['median_duration'] - baseline_median) / baseline_median) * 100
            min_change = ((summary['min_duration'] - baseline_min) / baseline_min) * 100
            max_change = ((summary['max_duration'] - baseline_max) / baseline_max) * 100
            
            print(f"| {name} | +{avg_change:.1f}% | +{median_change:.1f}% | +{min_change:.1f}% | +{max_change:.1f}% |")
    
    print()
    print("## Error and Warning Analysis")
    print()
    print("| Version | CLI Errors | Total Warnings | Errors vs Baseline | Warnings vs Baseline |")
    print("|---------|------------|----------------|--------------------|--------------------|")
    
    baseline_errors = results['baseline']['summary']['total_errors']
    baseline_warnings = results['baseline']['summary']['total_warnings']
    
    for version in ['baseline', 'v0.8.0-beta.2', 'v0.8.0-beta.2-with-n0-infra', 'v0.8.0-beta.2-n0-only-infra']:
        if version in results:
            summary = results[version]['summary']
            name = version_names[version]
            
            errors = summary['total_errors']
            warnings = summary['total_warnings']
            
            if version == 'baseline':
                error_diff = "-"
                warning_diff = "-"
            else:
                error_diff = f"{errors - baseline_errors:+d}"
                warning_diff = f"{warnings - baseline_warnings:+d}"
            
            print(f"| {name} | {errors} | {warnings} | {error_diff} | {warning_diff} |")
    
    print()
    print("## Individual Test Run Details")
    print()
    
    for version in ['baseline', 'v0.8.0-beta.2', 'v0.8.0-beta.2-with-n0-infra', 'v0.8.0-beta.2-n0-only-infra']:
        if version in results:
            name = version_names[version]
            print(f"### {name}")
            print()
            print("| Run | Duration (s) | Success | CLI Errors | CLI Warnings | Notable Issues |")
            print("|-----|--------------|---------|------------|--------------|----------------|")
            
            for i, run in enumerate(results[version]['test_runs'], 1):
                cli = run['cli_analysis']
                duration = cli['duration_seconds']
                success = "✅" if cli['success'] else "❌"
                errors = cli['error_count']
                warnings = cli['warn_count']
                
                # Count unique issue types
                issue_counts = {}
                for issue in cli['notable_issues']:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1
                
                # Format issues
                if issue_counts:
                    issues = ", ".join([f"{issue} ({count})" for issue, count in issue_counts.items()])
                else:
                    issues = "None"
                
                print(f"| {i} | {duration:.2f} | {success} | {errors} | {warnings} | {issues} |")
            
            print()

if __name__ == "__main__":
    generate_detailed_report()