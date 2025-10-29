"""Generate demo Threat Intelligence data for the Neo4j database.

This script creates fictional TI data with nodes and relationships based on
the project's data model. It generates creative names using animals, flowers,
and other themes to make the demo data interesting.

Version 2.0 - Updated to match JSON Format Specification v1.0
"""

import json
import random
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any


# Name Generators (Creative names for demo data)

ANIMALS = [
    "Panda",
    "Tiger",
    "Eagle",
    "Wolf",
    "Bear",
    "Falcon",
    "Leopard",
    "Cobra",
    "Viper",
    "Dragon",
    "Phoenix",
    "Griffin",
    "Raven",
    "Hawk",
    "Lynx",
    "Orca",
    "Shark",
    "Mantis",
    "Spider",
    "Scorpion",
    "Wasp",
    "Hornet",
    "Panther",
    "Jaguar",
    "Cougar",
    "Cheetah",
    "Lion",
    "Rhino",
    "Buffalo",
    "Bison",
    "Moose",
    "Elk",
    "Stag",
    "Ram",
    "Bull",
    "Ox",
    "Weasel",
    "Badger",
    "Wolverine",
    "Jackal",
    "Hyena",
    "Coyote",
    "Fox",
    "Ferret",
    "Mongoose",
]

FLOWERS = [
    "Rose",
    "Orchid",
    "Lily",
    "Tulip",
    "Daisy",
    "Sunflower",
    "Iris",
    "Lotus",
    "Jasmine",
    "Lavender",
    "Peony",
    "Dahlia",
    "Carnation",
    "Daffodil",
    "Marigold",
    "Zinnia",
    "Aster",
    "Poppy",
    "Primrose",
    "Azalea",
    "Camellia",
    "Magnolia",
    "Gardenia",
    "Begonia",
    "Chrysanthemum",
    "Hibiscus",
    "Petunia",
    "Snapdragon",
    "Violet",
    "Pansy",
    "Bluebell",
    "Snowdrop",
    "Foxglove",
]

MINERALS = [
    "Diamond",
    "Ruby",
    "Sapphire",
    "Emerald",
    "Topaz",
    "Amethyst",
    "Opal",
    "Jade",
    "Obsidian",
    "Quartz",
    "Crystal",
    "Onyx",
    "Granite",
    "Marble",
    "Platinum",
    "Titanium",
    "Cobalt",
    "Tungsten",
    "Chromium",
    "Nickel",
]

WEATHER = [
    "Storm",
    "Thunder",
    "Lightning",
    "Blizzard",
    "Typhoon",
    "Hurricane",
    "Cyclone",
    "Tornado",
    "Tempest",
    "Monsoon",
    "Frost",
    "Hail",
    "Sleet",
]

COLORS = [
    "Red",
    "Blue",
    "Green",
    "Black",
    "White",
    "Silver",
    "Gold",
    "Bronze",
    "Crimson",
    "Scarlet",
    "Azure",
    "Indigo",
    "Violet",
    "Amber",
    "Emerald",
]

ADJECTIVES = [
    "Silent",
    "Dark",
    "Shadow",
    "Stealth",
    "Ghost",
    "Phantom",
    "Hidden",
    "Secret",
    "Covert",
    "Swift",
    "Rapid",
    "Quick",
    "Blazing",
    "Frozen",
    "Arctic",
    "Desert",
    "Mountain",
    "Ocean",
    "Cyber",
    "Digital",
]


def generate_threat_actor_name() -> str:
    """Generate creative threat actor names."""
    patterns = [
        lambda: f"{random.choice(ADJECTIVES)} {random.choice(ANIMALS)}",
        lambda: f"{random.choice(COLORS)} {random.choice(WEATHER)}",
        lambda: f"{random.choice(ANIMALS)} {random.choice(MINERALS)}",
        lambda: f"{random.choice(WEATHER)} {random.choice(FLOWERS)}",
    ]
    return random.choice(patterns)()


def generate_malware_name() -> str:
    """Generate creative malware names."""
    patterns = [
        lambda: f"{random.choice(FLOWERS)}Bot",
        lambda: f"{random.choice(ANIMALS)}RAT",
        lambda: f"{random.choice(MINERALS)}Locker",
        lambda: f"{random.choice(WEATHER)}Trojan",
        lambda: f"Cyber{random.choice(ANIMALS)}",
    ]
    return random.choice(patterns)()


def generate_campaign_name() -> str:
    """Generate creative campaign names."""
    patterns = [
        lambda: f"Operation {random.choice(ANIMALS)}",
        lambda: f"Operation {random.choice(FLOWERS)}",
        lambda: f"{random.choice(ADJECTIVES)} {random.choice(WEATHER)}",
        lambda: f"Project {random.choice(MINERALS)}",
    ]
    return random.choice(patterns)()


def generate_tool_name() -> str:
    """Generate creative tool names."""
    patterns = [
        lambda: f"{random.choice(ANIMALS)}Scan",
        lambda: f"{random.choice(MINERALS)}Tool",
        lambda: f"Cyber{random.choice(ANIMALS)}",
        lambda: f"{random.choice(WEATHER)}Kit",
    ]
    return random.choice(patterns)()


def generate_random_date(start_year: int = 2020, end_year: int = 2025) -> str:
    """Generate random date in ISO format."""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    random_date = start + timedelta(
        seconds=random.randint(0, int((end - start).total_seconds()))
    )
    return random_date.strftime("%Y-%m-%d")


def generate_reserved_ip() -> str:
    """Generate IP from RFC 5737 reserved ranges."""
    # Use reserved IP ranges: 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24
    ranges = [
        (192, 0, 2),
        (198, 51, 100),
        (203, 0, 113),
    ]
    a, b, c = random.choice(ranges)
    d = random.randint(1, 254)
    return f"{a}.{b}.{c}.{d}"


# Node Generators


def generate_threat_actors(count: int) -> List[Dict[str, Any]]:
    """Generate ThreatActor nodes."""
    actors = []
    types = ["Nation-State", "Cybercriminal", "Hacktivist", "Terrorist", "Insider"]
    motivations = ["Financial", "Political", "Espionage", "Ideology", "Revenge"]

    for i in range(count):
        name = generate_threat_actor_name()
        actors.append(
            {
                "label": "ThreatActor",
                "properties": {
                    "name": name,
                    "type": random.choice(types),
                    "motivation": random.choice(motivations),
                    "description": f"Fictional threat actor {name}",
                    "aliases": f"{name}-Group, {name}-Team",
                    "first_seen": generate_random_date(2015, 2020),
                    "last_seen": generate_random_date(2023, 2025),
                },
            }
        )
    return actors


def generate_malware(count: int) -> List[Dict[str, Any]]:
    """Generate Malware nodes."""
    malware_list = []
    types = ["Trojan", "Ransomware", "RAT", "Backdoor", "Worm", "Rootkit"]
    families = ["BotFamily", "CryptoFamily", "RemoteFamily", "StealthFamily"]

    for i in range(count):
        name = generate_malware_name()
        malware_list.append(
            {
                "label": "Malware",
                "properties": {
                    "name": name,
                    "family": random.choice(families),
                    "type": random.choice(types),
                    "description": f"Fictional malicious software {name}",
                    "first_seen": generate_random_date(2018, 2023),
                    "last_seen": generate_random_date(2024, 2025),
                },
            }
        )
    return malware_list


def generate_campaigns(count: int) -> List[Dict[str, Any]]:
    """Generate Campaign nodes."""
    campaigns = []

    for i in range(count):
        name = generate_campaign_name()
        start_date = generate_random_date(2020, 2024)
        campaigns.append(
            {
                "label": "Campaign",
                "properties": {
                    "name": name,
                    "description": f"Fictional coordinated attack campaign {name}",
                    "start_date": start_date,
                    "end_date": generate_random_date(2024, 2025),
                },
            }
        )
    return campaigns


def generate_attack_patterns(count: int) -> List[Dict[str, Any]]:
    """Generate AttackPattern nodes."""
    patterns = []
    techniques = [
        "Phishing",
        "Spear Phishing",
        "SQL Injection",
        "XSS",
        "DDoS",
        "Man-in-the-Middle",
        "Credential Stuffing",
        "Brute Force",
        "Privilege Escalation",
        "Lateral Movement",
        "Exfiltration",
    ]

    for i in range(count):
        technique = random.choice(techniques)
        patterns.append(
            {
                "label": "AttackPattern",
                "properties": {
                    "name": f"{technique} - {random.choice(ADJECTIVES)} Variant",
                    "description": f"Fictional attack technique using {technique}",
                },
            }
        )
    return patterns


def generate_indicators(count: int) -> List[Dict[str, Any]]:
    """Generate Indicator nodes."""
    indicators = []

    for i in range(count):
        indicators.append(
            {
                "label": "Indicator",
                "properties": {
                    "name": f"IOC-{random.randint(1000, 9999)}-{random.choice(ANIMALS)}",
                    "description": f"Fictional indicator of compromise #{i}",
                    "first_seen": generate_random_date(2023, 2024),
                    "last_seen": generate_random_date(2024, 2025),
                },
            }
        )
    return indicators


def generate_observables(count: int) -> List[Dict[str, Any]]:
    """Generate Observable container nodes."""
    observables = []

    for i in range(count):
        obs_type = random.choice(["ipv4-addr", "file", "domain-name", "url"])
        observables.append(
            {
                "label": "Observable",
                "properties": {
                    "name": f"obs-{obs_type}-{i:03d}",
                    "description": f"Fictional observation of {obs_type}",
                    "type": obs_type,
                },
            }
        )
    return observables


def generate_files(count: int) -> List[Dict[str, Any]]:
    """Generate File nodes (Observable artifacts)."""
    files = []

    for i in range(count):
        filename = f"{random.choice(ANIMALS).lower()}_{random.randint(100, 999)}.exe"
        files.append(
            {
                "label": "File",
                "properties": {
                    "name": filename,
                    "filename": filename,
                    "size": str(random.randint(1024, 10485760)),
                    "hash_md5": f"{random.randint(10**31, 10**32 - 1):032x}",
                    "hash_sha256": f"{random.randint(10**63, 10**64 - 1):064x}",
                },
            }
        )
    return files


def generate_ipv4_addresses(count: int) -> List[Dict[str, Any]]:
    """Generate IPv4Adress nodes."""
    ips = []

    for i in range(count):
        ip = generate_reserved_ip()
        ips.append(
            {
                "label": "IPv4Adress",
                "properties": {
                    "name": ip,
                    "addressurl": ip,
                },
            }
        )
    return ips


def generate_organizations(count: int) -> List[Dict[str, Any]]:
    """Generate Organization nodes."""
    orgs = []
    sectors = [
        "Finance",
        "Healthcare",
        "Energy",
        "Technology",
        "Government",
        "Education",
    ]
    regions = [
        "North America",
        "Europe",
        "Asia",
        "Middle East",
        "Africa",
        "South America",
    ]
    suffixes = ["Corp", "Industries", "Group", "Systems", "Tech", "Solutions"]

    for i in range(count):
        org_name = f"{random.choice(FLOWERS)} {random.choice(suffixes)}"
        orgs.append(
            {
                "label": "Organization",
                "properties": {
                    "name": org_name,
                    "sector": random.choice(sectors),
                    "region": random.choice(regions),
                    "description": f"Fictional organization in the {sectors[i % len(sectors)]} sector",
                },
            }
        )
    return orgs


def generate_tools(count: int) -> List[Dict[str, Any]]:
    """Generate Tool nodes."""
    tools = []

    for i in range(count):
        name = generate_tool_name()
        tools.append(
            {
                "label": "Tool",
                "properties": {
                    "name": name,
                    "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 20)}",
                    "description": f"Fictional security tool {name}",
                },
            }
        )
    return tools


def generate_vulnerabilities(count: int) -> List[Dict[str, Any]]:
    """Generate Vulnerability nodes."""
    vulns = []

    for i in range(count):
        year = random.randint(2018, 2025)
        cve_id = f"CVE-{year}-{random.randint(1000, 99999)}"
        vulns.append(
            {
                "label": "Vulnerability",
                "properties": {
                    "name": cve_id,
                    "cve_id": cve_id,
                    "cvss_score": str(round(random.uniform(4.0, 10.0), 1)),
                    "description": f"Fictional security vulnerability {cve_id}",
                },
            }
        )
    return vulns


def generate_reports(count: int) -> List[Dict[str, Any]]:
    """Generate Report nodes."""
    reports = []
    sources = [
        "Security Research Lab",
        "Threat Intelligence Center",
        "Cyber Defense Unit",
        "Analysis Team",
        "Security Operations",
        "Research Division",
    ]
    types = ["Report", "Analysis", "Brief", "Intelligence", "Assessment"]

    for i in range(count):
        report_name = f"{random.choice(ANIMALS)} {random.choice(types)}"
        reports.append(
            {
                "label": "Report",
                "properties": {
                    "name": report_name,
                    "title": report_name,
                    "description": f"Fictional threat intelligence report: {report_name}",
                    "source": random.choice(sources),
                    "published_date": generate_random_date(2020, 2025),
                },
            }
        )
    return reports


def generate_incidents(count: int) -> List[Dict[str, Any]]:
    """Generate Incident nodes."""
    incidents = []

    for i in range(count):
        detection_date = generate_random_date(2023, 2024)
        incidents.append(
            {
                "label": "Incident",
                "properties": {
                    "name": f"Incident-{random.choice(COLORS)}-{random.randint(100, 999)}",
                    "description": f"Fictional security incident #{i}",
                    "detection_date": detection_date,
                    "resolved_date": generate_random_date(2024, 2025),
                },
            }
        )
    return incidents


# Relationship Generator


def generate_relationships(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate relationships between nodes based on data model."""
    relationships = []

    # Group nodes by label for easy access
    nodes_by_label = {}
    for node in nodes:
        label = node["label"]
        if label not in nodes_by_label:
            nodes_by_label[label] = []
        nodes_by_label[label].append(node)

    def get_node_identifier(node):
        """Get the primary identifier for a node."""
        props = node["properties"]
        if "name" in props:
            return ("name", props["name"])
        elif "title" in props:
            return ("title", props["title"])
        elif "cve_id" in props:
            return ("cve_id", props["cve_id"])
        elif "filename" in props:
            return ("filename", props["filename"])
        elif "addressurl" in props:
            return ("addressurl", props["addressurl"])
        else:
            # Fallback to first property
            first_key = list(props.keys())[0]
            return (first_key, props[first_key])

    def add_relationship(from_label, to_label, rel_type, count_per_node=2):
        """Helper to add relationships between node types."""
        if from_label not in nodes_by_label or to_label not in nodes_by_label:
            return

        for from_node in nodes_by_label[from_label]:
            # Random selection of target nodes
            to_nodes = random.sample(
                nodes_by_label[to_label],
                min(count_per_node, len(nodes_by_label[to_label])),
            )

            for to_node in to_nodes:
                from_prop, from_val = get_node_identifier(from_node)
                to_prop, to_val = get_node_identifier(to_node)

                relationships.append(
                    {
                        "type": rel_type,
                        "from": {
                            "label": from_label,
                            "property": from_prop,
                            "value": from_val,
                        },
                        "to": {
                            "label": to_label,
                            "property": to_prop,
                            "value": to_val,
                        },
                        "properties": {
                            "source": "Demo Data Generator",
                            "first_seen": generate_random_date(2020, 2024),
                        },
                    }
                )

    # Generate relationships based on data model
    add_relationship("ThreatActor", "Malware", "USES", 3)
    add_relationship("ThreatActor", "Tool", "USES", 2)
    add_relationship("ThreatActor", "Campaign", "LAUNCHED", 2)
    add_relationship("Campaign", "Malware", "EMPLOYES", 3)
    add_relationship("Campaign", "AttackPattern", "EMPLOYES", 2)
    add_relationship("Campaign", "Organization", "TARGETS", 2)
    add_relationship("Malware", "AttackPattern", "USES", 2)
    add_relationship("Malware", "Indicator", "INDICATED_BY", 2)
    add_relationship("Indicator", "Observable", "BASED_ON", 1)
    add_relationship("Observable", "File", "BASED_ON", 1)
    add_relationship("Observable", "IPv4Adress", "BASED_ON", 1)
    add_relationship("Incident", "Organization", "TARGETS", 1)
    add_relationship("Incident", "Indicator", "INDICATED_BY", 2)
    add_relationship("Report", "ThreatActor", "DESCRIBES", 2)
    add_relationship("Report", "Malware", "DESCRIBES", 2)
    add_relationship("Report", "Campaign", "DESCRIBES", 1)
    add_relationship("Report", "Vulnerability", "DESCRIBES", 1)
    add_relationship("Malware", "Vulnerability", "USES", 1)

    return relationships


# Metadata Generator


def generate_metadata(
    nodes: List[Dict[str, Any]], relationships: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate metadata section for JSON output."""
    return {
        "version": "1.0",
        "created": datetime.now().isoformat() + "Z",
        "source": "Demo Data Generator",
        "description": "Fictional threat intelligence data for demonstration purposes",
        "node_count": len(nodes),
        "relationship_count": len(relationships),
        "generator_version": "2.0",
        "author": "TI Analysis System",
        "tags": ["demo", "fictional", "generated"],
    }


# Main Generator


def generate_demo_data(total_nodes: int = 500) -> Dict[str, Any]:
    """Generate complete demo dataset.

    Args:
        total_nodes: Total number of nodes to generate (distributed across types)

    Returns:
        Dictionary with metadata, nodes, and relationships
    """
    print(f"Generating {total_nodes} nodes of demo data...")

    # Distribute nodes across types
    distribution = {
        "ThreatActor": 0.08,  # 8%
        "Malware": 0.15,  # 15%
        "Campaign": 0.10,  # 10%
        "AttackPattern": 0.10,  # 10%
        "Indicator": 0.15,  # 15%
        "Observable": 0.10,  # 10%
        "File": 0.08,  # 8%
        "IPv4Adress": 0.08,  # 8%
        "Organization": 0.06,  # 6%
        "Tool": 0.04,  # 4%
        "Vulnerability": 0.03,  # 3%
        "Report": 0.02,  # 2%
        "Incident": 0.01,  # 1%
    }

    nodes = []

    # Generate nodes
    nodes.extend(generate_threat_actors(int(total_nodes * distribution["ThreatActor"])))
    nodes.extend(generate_malware(int(total_nodes * distribution["Malware"])))
    nodes.extend(generate_campaigns(int(total_nodes * distribution["Campaign"])))
    nodes.extend(
        generate_attack_patterns(int(total_nodes * distribution["AttackPattern"]))
    )
    nodes.extend(generate_indicators(int(total_nodes * distribution["Indicator"])))
    nodes.extend(generate_observables(int(total_nodes * distribution["Observable"])))
    nodes.extend(generate_files(int(total_nodes * distribution["File"])))
    nodes.extend(generate_ipv4_addresses(int(total_nodes * distribution["IPv4Adress"])))
    nodes.extend(
        generate_organizations(int(total_nodes * distribution["Organization"]))
    )
    nodes.extend(generate_tools(int(total_nodes * distribution["Tool"])))
    nodes.extend(
        generate_vulnerabilities(int(total_nodes * distribution["Vulnerability"]))
    )
    nodes.extend(generate_reports(int(total_nodes * distribution["Report"])))
    nodes.extend(generate_incidents(int(total_nodes * distribution["Incident"])))

    print(f" Generated {len(nodes)} nodes")

    # Generate relationships
    relationships = generate_relationships(nodes)
    print(f" Generated {len(relationships)} relationships")

    # Generate metadata
    metadata = generate_metadata(nodes, relationships)

    return {
        "metadata": metadata,
        "nodes": nodes,
        "relationships": relationships,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate fictional threat intelligence demo data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 500 nodes (default)
  python generate_demo_data.py

  # Generate 1000 nodes
  python generate_demo_data.py --nodes 1000

  # Specify output file
  python generate_demo_data.py --output custom_data.json

  # Set random seed for reproducibility
  python generate_demo_data.py --seed 42
        """,
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=500,
        help="Number of nodes to generate (default: 500)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="demo_threat_data.json",
        help="Output file path (default: demo_threat_data.json)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (optional)",
    )

    args = parser.parse_args()

    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    # Generate data
    print("=" * 60)
    data = generate_demo_data(args.nodes)
    print("=" * 60)

    # Write to file
    print(f"\nWriting data to {args.output}...")
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✓ Demo data written to {args.output}")
    print(f"\nSummary:")
    print(f"  Nodes: {data['metadata']['node_count']}")
    print(f"  Relationships: {data['metadata']['relationship_count']}")
    print(f"  Format Version: {data['metadata']['version']}")
    print(f"  Generated: {data['metadata']['created']}")
    print("\n✓ Done!")

