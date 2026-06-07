import json
import os

log_file = '/Users/sanviraj/.gemini/antigravity/brain/3e18f141-b6ff-47b3-bbd1-e444103bac6d/.system_generated/logs/overview.txt'
output_file = 'scratch/full_roadmap.txt'

if not os.path.exists('scratch'):
    os.makedirs('scratch')

with open(log_file, 'r') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('step_index') == 617:
                with open(output_file, 'w') as out:
                    out.write(data['content'])
                print(f"Saved content of step 617 to {output_file}")
                break
        except:
            continue
