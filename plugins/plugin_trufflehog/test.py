import json
import docker
import os
import tempfile
import sys

# Ensure all prints are flushed immediately
def print_flush(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

rancher_paths = [
    os.path.expanduser('~/.rd/docker.sock'),
    os.path.expanduser('~/.lima/rancher-desktop/sock/docker.sock'),
    os.path.expanduser('~/.lima/docker/sock/docker.sock'),
    os.path.expanduser('~/.docker/run/docker.sock')
]

client = None
for socket_path in rancher_paths:
    if os.path.exists(socket_path):
        try:
            client = docker.DockerClient(base_url=f'unix://{socket_path}')
            client.ping()
            print_flush(f"✅ Docker connected via Rancher socket: {socket_path}")
            break
        except Exception as e:
            print_flush(f"❌ Socket {socket_path} failed: {e}")

if client is None:
    print_flush("❌ Could not connect to any Docker socket")
    sys.exit(1)

with tempfile.TemporaryDirectory() as temp_dir:
    input_dir = os.path.join(temp_dir, 'input')
    output_dir = os.path.join(temp_dir, 'output')
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    print_flush(f"📁 Created directories: {input_dir}, {output_dir}")

    with open(os.path.join(input_dir, 'input.json'), 'w') as f:
        json.dump({}, f)

    with open(os.path.join(input_dir, 'parameters.json'), 'w') as f:
        json.dump({"repo_url": "https://github.com/Meesho/BharatMLStack","scan_type":"github"}, f)

    print_flush("📝 Created input files")

    print_flush("🚀 Starting TruffleHog container...")

    try:
        container = client.containers.run(
            image="amanistaken/plugin:trufflehog-v1.0.1",
            detach=True,
            volumes={
                input_dir: {'bind': '/tmp/input', 'mode': 'ro'},
                output_dir: {'bind': '/tmp/output', 'mode': 'rw'}
            },
            environment={
                'PLUGIN_ID': "1234",
                'PLUGIN_VERSION': "1.0.0"
            },
            mem_limit='512m',
            cpu_count=1
        )
        
        print_flush(f"📦 Container ID: {container.short_id}")
        print_flush("⏳ Waiting for container to complete...")
        
        # Wait for container to finish
        result = container.wait()
        exit_code = result['StatusCode']
        
        print_flush(f"🏁 Container finished with exit code: {exit_code}")
        
        # Get ALL logs (both stdout and stderr)
        print_flush("\n" + "="*60)
        print_flush("📋 COMPLETE CONTAINER LOGS (STDOUT + STDERR):")
        print_flush("="*60)
        
        # Get logs with both stdout and stderr
        logs = container.logs(stdout=True, stderr=True).decode('utf-8')
        if logs.strip():
            print_flush(logs)
        else:
            print_flush("(No logs generated)")
        
        print_flush("="*60)
        
        # Check output directory
        print_flush(f"\n📁 Checking output directory: {output_dir}")
        try:
            output_files = os.listdir(output_dir)
            if output_files:
                print_flush(f"📄 Found output files: {output_files}")
                for file in output_files:
                    file_path = os.path.join(output_dir, file)
                    file_size = os.path.getsize(file_path)
                    print_flush(f"  - {file} ({file_size} bytes)")
                    
                    # Show content of small text files
                    if file_size < 10000 and (file.endswith('.json') or file.endswith('.txt') or file.endswith('.log')):
                        print_flush(f"\n📄 Contents of {file}:")
                        print_flush("-" * 40)
                        try:
                            with open(file_path, 'r') as f:
                                content = f.read()
                                if file.endswith('.json'):
                                    try:
                                        parsed = json.loads(content)
                                        print_flush(json.dumps(parsed, indent=2))
                                    except json.JSONDecodeError:
                                        print_flush("Invalid JSON, showing raw content:")
                                        print_flush(content)
                                else:
                                    print_flush(content)
                        except Exception as e:
                            print_flush(f"Error reading file: {e}")
                        print_flush("-" * 40)
            else:
                print_flush("⚠️  No output files found")
        except Exception as e:
            print_flush(f"❌ Error accessing output directory: {e}")
        
        # Clean up
        print_flush(f"\n🗑️  Removing container {container.short_id}")
        container.remove()
        
        # Final status
        if exit_code == 0:
            print_flush("✅ TruffleHog scan completed successfully!")
        else:
            print_flush(f"❌ TruffleHog scan failed with exit code {exit_code}")
            
    except Exception as e:
        print_flush(f"💥 Error during container execution: {e}")
        if 'container' in locals():
            try:
                # Get logs even if there's an error
                logs = container.logs(stdout=True, stderr=True).decode('utf-8')
                print_flush("\n📋 CONTAINER LOGS (ERROR CASE):")
                print_flush("-" * 40)
                print_flush(logs)
                print_flush("-" * 40)
                container.remove()
            except:
                pass
        raise

    print_flush("🎯 Script execution completed!")