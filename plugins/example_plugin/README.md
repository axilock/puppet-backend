# Example Domain Processing Plugin

This is an example plugin for the distributed task processing system. It demonstrates how to create a Docker-based plugin that can be used by the system.

## Functionality

This plugin processes domain names and returns information about them, including:

- Whether the domain can be resolved
- IP addresses associated with the domain
- Timestamp of the processing

## Input Format

The plugin expects input data in the following format:

```json
{
  "domain": "example.com"
}
```

## Parameters

The plugin accepts the following parameters (all optional):

```json
{
  "timeout": 10,
  "resolve_type": "A"
}
```

## Output Format

The plugin produces output in the following format:

```json
{
  "domain": "example.com",
  "timestamp": 1624276283.123456,
  "resolved": true,
  "ip_addresses": ["93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"],
  "parameters_used": {
    "timeout": 10,
    "resolve_type": "A"
  }
}
```

If the domain cannot be resolved, the output will include an error field:

```json
{
  "domain": "nonexistent-domain.example",
  "timestamp": 1624276283.123456,
  "resolved": false,
  "ip_addresses": [],
  "parameters_used": {},
  "error": "Failed to resolve domain"
}
```

## Building the Plugin

To build the plugin Docker image:

```bash
docker build -t domain-processor:1.0.0 .
```

## Registering the Plugin

To register the plugin with the central server:

```bash
curl -X POST http://central-server:8000/api/plugins \
  -H "Content-Type: application/json" \
  -d '{
    "id": "domain-processor",
    "name": "Domain Processor",
    "version": "1.0.0",
    "docker_image": "domain-processor:1.0.0",
    "description": "Processes domain names and returns information about them",
    "queue": "domain_queue",
    "parameters": [
      {
        "name": "timeout",
        "type": "number",
        "description": "Timeout in seconds",
        "required": false,
        "default": 10
      },
      {
        "name": "resolve_type",
        "type": "string",
        "description": "Type of DNS record to resolve",
        "required": false,
        "default": "A"
      }
    ]
  }'
```

## Queue Configuration

This plugin processes tasks from the following queue:

- `domain_queue`: The queue for domain processing tasks

When this plugin is registered, workers will automatically be configured to consume from this queue if they aren't already doing so. This ensures that workers can process tasks intended for this plugin without manual configuration.

## Plugin Contract

All plugins must follow these conventions:

1. Read input data from `/input/input.json`
2. Read parameters from `/input/parameters.json`
3. Write results to `/output/result.json`
4. Exit with code 0 on success, non-zero on failure
5. Write error messages to stderr

This ensures that the worker can properly interact with the plugin.
