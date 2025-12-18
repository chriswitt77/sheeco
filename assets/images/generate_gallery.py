import os
from collections import defaultdict

def generate_gallery(img_dir="assets/images", output_file="assets/images/image_gallery.md"):
    valid_exts = ('.png', '.jpg', '.jpeg')
    images = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(valid_exts)])
    
    # Group images by category (e.g., 'bend' or 'rect')
    categories = defaultdict(list)
    for img in images:
        cat = "Bends" if "bend" in img.lower() else "Rectangles"
        categories[cat].append(img)

    lines = ["# Image Gallery\n"]

    for cat_name, img_list in categories.items():
        lines.append(f"### {cat_name}")
        
        # Process in pairs
        for i in range(0, len(img_list), 2):
            pair = img_list[i:i+2]
            lines.append('<p align="center">')
            
            for img_name in pair:
                name_part = os.path.splitext(img_name)[0]
                try:
                    prefix, img_id = name_part.split('_')
                    count = ''.join(filter(str.isdigit, prefix))
                    label = "Bend" if "bend" in prefix.lower() else "Rectangle"
                    plural = "s" if int(count) != 1 else ""
                    alt_text = f"{count} {label}{plural}, ID {img_id}"
                except ValueError:
                    alt_text = img_name

                # src is just the filename
                lines.append(f'  <img src="{img_name}" alt="{alt_text}" width="45%"/>')
            
            lines.append('</p>')
        lines.append("") # Spacer between categories

    with open(output_file, "w") as f:
        f.write("\n".join(lines))
    print(f"Generated {output_file}")

if __name__ == "__main__":
    generate_gallery()