#!/usr/bin/env python3
"""
Merge multiple KML flight plan files into a single KML for Google Earth.
Each input KML will be placed in its own <Folder> for clarity.
"""
import os
import xml.etree.ElementTree as ET

MERGED_FILENAME = "merged_flightplans.kml"
TEMP_DIR = "temp"

# Find all KML files in the temp directory (except the merged output)
if not os.path.exists(TEMP_DIR):
    print(f"Temp directory '{TEMP_DIR}' not found. Run the extractor script first.")
    exit(1)

kml_files = [f for f in os.listdir(TEMP_DIR) if f.endswith('.kml') and f != MERGED_FILENAME]

if not kml_files:
    print(f"No KML files found in {TEMP_DIR} directory.")
    exit(1)

print(f"Merging {len(kml_files)} KML files from {TEMP_DIR}:")
for f in kml_files:
    print(f"  - {f}")

# Create the root KML structure
kml_ns = "http://www.opengis.net/kml/2.2"
ET.register_namespace('', kml_ns)
root = ET.Element("{http://www.opengis.net/kml/2.2}kml")
doc = ET.SubElement(root, "Document")
ET.SubElement(doc, "name").text = "Merged Flight Plans"
ET.SubElement(doc, "description").text = "All merged flight plans. Each original KML is in its own folder."

for kml_file in kml_files:
    kml_path = os.path.join(TEMP_DIR, kml_file)
    tree = ET.parse(kml_path)
    kml_root = tree.getroot()
    # Find the Document element
    doc_elem = kml_root.find(f".//{{{kml_ns}}}Document")
    if doc_elem is None:
        print(f"Warning: No <Document> in {kml_file}, skipping.")
        continue
    # Create a Folder for this KML
    folder = ET.SubElement(doc, "Folder")
    ET.SubElement(folder, "name").text = kml_file
    # Copy all Placemarks and Folders from this KML's Document
    for child in doc_elem:
        if child.tag.endswith('Placemark') or child.tag.endswith('Folder'):
            folder.append(child)

# Write the merged KML to main directory
ET.ElementTree(root).write(MERGED_FILENAME, encoding='utf-8', xml_declaration=True)
print(f"Merged KML written to {MERGED_FILENAME}") 