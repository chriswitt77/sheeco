import os
from collections import defaultdict

def generate_gallery(img_dir="assets/images", output_file="assets/images/image_gallery.md"):
    valid_exts = ('.png', '.jpg', '.jpeg')
    images = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(valid_exts)])
    
    # Group images by version (the first two digits)
    versions = defaultdict(list)
    for img in images:
        if "_" in img:
            version_prefix = img.split('_')[0]
            versions[version_prefix].append(img)

    lines = ["# Image Gallery\n"]

    # Sort versions descending (04 before 03)
    for v in sorted(versions.keys(), reverse=True):
        display_version = f"{v[0]}.{v[1]}" if len(v) == 2 else v
        lines.append(f"### Version {display_version}")
        
        img_list = versions[v]
        for i in range(0, len(img_list), 2):
            pair = img_list[i:i+2]
            lines.append('<p align="center">')
            
            for img_name in pair:
                name_part = os.path.splitext(img_name)[0]
                try:
                    # Format: 04_3rect_01 -> parts: ["04", "3rect", "01"]
                    _, desc, img_id = name_part.split('_')
                    
                    count = ''.join(filter(str.isdigit, desc))
                    if "onshape" in desc.lower():
                        alt_text = f"Onshape Export {img_id}"
                    else:
                        label = "Rectangle" if "rect" in desc.lower() else "Bend"
                        plural = "s" if (count and int(count) != 1) else ""
                        alt_text = f"{count} {label}{plural}, ID {img_id}"
                except ValueError:
                    alt_text = img_name

                lines.append(f'  <img src="{img_name}" alt="{alt_text}" width="45%"/>')
            
            lines.append('</p>')
        lines.append("") 

    with open(output_file, "w") as f:
        f.write("\n".join(lines))
    print(f"Generated {output_file}")

if __name__ == "__main__":
    generate_gallery()