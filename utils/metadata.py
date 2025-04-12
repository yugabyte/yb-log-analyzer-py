import os
import re
import subprocess  # Use subprocess for security and better control

def get_node_details(log_files_metadata):
    """
    Retrieves details for each node (tserver and master) from log files metadata.

    Args:
        log_files_metadata:  (Presumed to be a data structure containing information
                              about log file locations and node types.)

    Returns:
        A dictionary where keys are node names and values are dictionaries
        containing node details (nodeDir, tserverUUID, masterUUID, placement, NumTablets).
    """

    tserver_list, master_list = get_tserver_master_list(log_files_metadata)
    node_list = set(tserver_list + master_list)
    uuid_pattern = re.compile(r'^[a-f0-9]+$', re.IGNORECASE)  # Corrected regex

    node_details = {}
    for node in node_list:
        node_details[node] = _get_single_node_details(log_files_metadata, node, uuid_pattern)

    return node_details


def _get_single_node_details(log_files_metadata, node, uuid_pattern):
    """
    Helper function to retrieve details for a single node.
    """
    node_dir = get_node_directory(log_files_metadata, node)

    if not os.path.exists(node_dir):
        return {
            "nodeDir": "-",
            "tserverUUID": "-",
            "masterUUID": "-",
            "placement": "-",
            "NumTablets": 0,
        }

    num_tablets = _get_num_tablets(node_dir, uuid_pattern)
    tserver_uuid = _get_uuid(node_dir, "tserver")
    master_uuid = _get_uuid(node_dir, "master")
    placement = _get_placement(node_dir)

    return {
        "nodeDir": node_dir,
        "tserverUUID": tserver_uuid,
        "masterUUID": master_uuid,
        "placement": placement,
        "NumTablets": num_tablets,
    }


def _get_num_tablets(node_dir, uuid_pattern):
    """
    Gets the number of tablets by counting files in the tablet-meta directory
    that match the UUID pattern.
    """
    tablet_meta_dir = os.path.join(node_dir, "tserver", "tablet-meta")
    if not os.path.exists(tablet_meta_dir):
        return 0

    try:
        return len([f for f in os.listdir(tablet_meta_dir) if uuid_pattern.match(f)])
    except OSError:
        # Handle potential errors during directory listing (e.g., permissions)
        print(f"Warning: Could not list files in {tablet_meta_dir}")
        return 0


def _get_uuid(node_dir, service_type):
    """
    Retrieves the UUID from the instance file for the given service type (tserver or master).
    """
    instance_file = os.path.join(node_dir, service_type, "instance")
    if not os.path.exists(instance_file):
        return "-"

    try:
        # Use subprocess.run for security and to capture output correctly
        result = subprocess.run(["yb-pbc-dump", instance_file], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if line.startswith("uuid:"):
                return line.split(":")[1].strip().replace('"', '')
        return "-"  # UUID not found in the file

    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        # Handle errors during subprocess execution
        print(f"Warning: Could not get UUID from {instance_file}: {e}")
        return "-"


def _get_placement(node_dir):
    """
    Retrieves placement details (cloud, region, zone) from the server.conf file.
    """
    gflags_file = os.path.join(node_dir, "tserver", "conf", "server.conf")
    if not os.path.exists(gflags_file):
        return "-"

    cloud = region = zone = "-"
    try:
        with open(gflags_file, "r") as f:
            for line in f:
                line = line.strip()  # Remove leading/trailing whitespace
                if "placement_cloud" in line:
                    cloud = line.split("=")[1].strip()
                if "placement_region" in line:
                    region = line.split("=")[1].strip()
                if "placement_zone" in line:
                    zone = line.split("=")[1].strip()
        return f"{cloud}..{region}..{zone}"  # Construct placement string
    except IOError:
        print(f"Warning: Could not read {gflags_file}")
        return "-"


# Placeholder functions - replace with your actual implementations
def get_tserver_master_list(log_files_metadata):
    """Returns lists of tserver and master nodes."""
    # Replace with your actual logic to extract these lists
    return [], []


def getNodeDirectory(log_files_metadata, node):
    """Returns the directory for a given node."""
    # Replace with your actual logic to determine the node directory
    return f"/path/to/node/{node}"