#!/home/amirreza-a2a/Scripts/.scriptsENV/bin/python3

import os
import re
import subprocess
from datetime import datetime

def get_time_from_xml(xml_file):
    """
    Extract the exact recording date and time from the XML metadata file.
    Example format in XML: Sat May 23 10:10:59 2026
    """
    if not os.path.exists(xml_file):
        return None
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Regex to match standard timestamp format: Day Mon DD HH:MM:SS YYYY
            match = re.search(r"([A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{2}\s+\d{2}:\d{2}:\d{2}\s+\d{4})", content)
            if match:
                return datetime.strptime(match.group(1), "%a %b %d %H:%M:%S %Y")
    except Exception as e:
        print(f"⚠️ Error reading XML file {xml_file}: {e}")
    return None

def main():
    print("🔍 Parsing XML files and extracting timestamps...")
    
    # Identify all audio tracks and potential main video streams
    audio_files = sorted([f for f in os.listdir('.') if f.startswith('cameraVoip') and f.endswith('.flv')])
    video_candidates = ['screenshare_1_4.flv', 'mainstream.flv', 'ftstage2.flv']
    main_video = next((v for v in video_candidates if os.path.exists(v)), None)

    if not main_video or not audio_files:
        print("❌ Main video file or audio tracks could not be found.")
        return

    print(f"🎥 Main Video: {main_video}")
    print(f"🎵 Audio Files: {', '.join(audio_files)}")

    # Gather start times for all valid media assets
    times = {}
    v_time = get_time_from_xml(main_video.replace('.flv', '.xml'))
    if v_time:
        times[main_video] = v_time
        
    for a in audio_files:
        a_time = get_time_from_xml(a.replace('.flv', '.xml'))
        if a_time:
            times[a] = a_time

    if not times:
        print("❌ Time metadata not found in any XML files.")
        return

    # Determine the timeline baseline (the earliest starting asset)
    base_time = min(times.values())

    # Calculate the video offset delay relative to the baseline
    v_delay_sec = (times.get(main_video, base_time) - base_time).total_seconds()
    v_offset_cmd = f"-itsoffset {v_delay_sec} " if v_delay_sec > 0 else ""
    
    # Build FFmpeg input flags and complex filter graphs
    inputs = [f"{v_offset_cmd}-i {main_video}"]
    filter_complex = []
    amix_inputs = ""
    
    for idx, a in enumerate(audio_files, start=1):
        inputs.append(f"-i {a}")
        a_delay_ms = int((times.get(a, base_time) - base_time).total_seconds() * 1000)
        
        # Apply delay to both left and right audio channels
        filter_complex.append(f"[{idx}:a]adelay={a_delay_ms}|{a_delay_ms}[a{idx}]")
        amix_inputs += f"[a{idx}]"

    # Mix all processed audio tracks into a single output stream
    filter_complex.append(f"{amix_inputs}amix=inputs={len(audio_files)}:dropout_transition=0[aout]")

    filter_str = "; ".join(filter_complex)
    inputs_str = " ".join(inputs)
    output_file = "final_class_synced.mkv"
    
    # Construct the final FFmpeg command string
    cmd = f'ffmpeg -y {inputs_str} -filter_complex "{filter_str}" -map 0:v -map "[aout]" -c:v copy -c:a aac {output_file}'

    print("\n🎬 Rendering and mixing via FFmpeg (this might take a few moments)...")
    
    # Execute the FFmpeg command and check the return code
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print(f"\n✨ Processing complete! Final video generated: {output_file}")
    else:
        print("\n❌ FFmpeg execution failed.")

if __name__ == "__main__":
    main()