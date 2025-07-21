#!/usr/bin/env python3
"""
Example plugin for the distributed task processing system.

This plugin demonstrates how to create a plugin for the system.
It processes a domain name and returns information about it.
"""
import json
import os
import sys
import time
import socket
from typing import Dict, Any


def process_domain(domain: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a domain name and return information about it.
    
    Args:
        domain: The domain name to process
        parameters: Additional parameters for processing
    
    Returns:
        Dictionary containing information about the domain
    """
    result = {
        "domain": domain,
        "timestamp": time.time(),
        "resolved": False,
        "ip_addresses": [],
        "parameters_used": parameters
    }
    
    # Try to resolve the domain
    try:
        # Get all IP addresses
        ip_addresses = []
        for info in socket.getaddrinfo(domain, None):
            ip = info[4][0]
            if ip not in ip_addresses:
                ip_addresses.append(ip)
        
        result["resolved"] = True
        result["ip_addresses"] = ip_addresses
    except socket.gaierror:
        result["error"] = "Failed to resolve domain"
    
    return result


def main():
    """Main entry point for the plugin."""
    # Read input data and parameters
    try:
        with open('/input/input.json', 'r') as f:
            input_data = json.load(f)
        
        with open('/input/parameters.json', 'r') as f:
            parameters = json.load(f)
    except Exception as e:
        sys.stderr.write(f"Error reading input: {e}\n")
        sys.exit(1)
    
    # Process the input
    try:
        if isinstance(input_data, dict) and "domain" in input_data:
            domain = input_data["domain"]
            result = process_domain(domain, parameters)
        else:
            sys.stderr.write("Input data must contain a 'domain' field\n")
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error processing input: {e}\n")
        sys.exit(1)
    
    # Write the result
    try:
        with open('/output/result.json', 'w') as f:
            json.dump(result, f)
    except Exception as e:
        sys.stderr.write(f"Error writing output: {e}\n")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
