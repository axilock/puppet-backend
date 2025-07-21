#!/usr/bin/env python3
import json
import subprocess
import sys
import os
import time

def main():
    
    with open('/tmp/input/input.json', 'r') as f:
        params = json.load(f)
    
    repo_url = params.get('repo_url')
    scan_type = params.get('scan_type', 'github')

    print("??", params, repo_url, scan_type)
    
    # Run TruffleHog
    cmd = ['trufflehog', scan_type, '--repo', repo_url, '--force-skip-binaries', '--force-skip-archives'  , '--json']
    print(cmd)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse results
        findings = []
        for line in result.stdout.split('\n'):
            if line.strip():
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        # Write results
        output = {
            'status': 'success',
            'findings': findings,
            'total_findings': len(findings)
        }
        
        with open('/tmp/output/result.json', 'w') as f:
            json.dump(output, f, indent=2)
            
    except subprocess.CalledProcessError as e:
        error_output = {
            'status': 'error',
            'error': e.stderr,
            'exit_code': e.returncode
        }
        
        with open('/output/result.json', 'w') as f:
            json.dump(error_output, f, indent=2)

if __name__ == '__main__':
    main()