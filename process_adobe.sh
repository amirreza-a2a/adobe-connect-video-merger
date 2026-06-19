#!/bin/bash

# Target directory to save the final synchronized videos
OUTPUT_DIR="$HOME/Downloads/adobeVideo"
mkdir -p "$OUTPUT_DIR"

# Directory containing the downloaded Adobe Connect zip files
DOWNLOADS_DIR="$HOME/Downloads/adobeZip"

# Temporary directory for extracting each class archive
TMP_DIR="$DOWNLOADS_DIR/tmp_extract"

echo "🚀 Adobe Connect video merging and automation process started..."
echo "📂 Final videos will be saved to: $OUTPUT_DIR"
echo "--------------------------------------------------------"

# Change directory to the downloads folder
cd "$DOWNLOADS_DIR" || exit

counter=1

# Process zip files starting with 'p', sorted from oldest to newest by modification time
# Using process substitution to safely handle potential spaces in filenames
while read -r zip_file; do
    if [ -f "$zip_file" ]; then
        # Format counter with leading zeros (e.g., 01, 02, 03...)
        formatted_counter=$(printf "%02d" $counter)
        
        echo "📦 [$formatted_counter] Processing zip file: $zip_file"
        
        # Create temp directory and extract the zip file quietly
        mkdir -p "$TMP_DIR"
        unzip -q "$zip_file" -d "$TMP_DIR"
        
        # Move into the temp directory to execute the python merger script
        cd "$TMP_DIR" || continue
        
        # Execute the python script (checks if available in PATH, otherwise falls back)
        if command -v mergeVideoAdobe.py &> /dev/null; then
            mergeVideoAdobe.py
        else
            python3 "$HOME/Scripts/merge.py"
        fi
        
        # Verify if the synchronized output file was successfully created
        if [ -f "final_class_synced.mkv" ]; then
            mv "final_class_synced.mkv" "$OUTPUT_DIR/class_$formatted_counter.mkv"
            echo "✅ Video successfully saved as class_$formatted_counter.mkv"
        else
            echo "❌ Error: Output file was not generated for $zip_file"
        fi
        
        # Return to the downloads directory and clean up the temporary files
        cd "$DOWNLOADS_DIR" || exit
        rm -rf "$TMP_DIR"
        
        echo "--------------------------------------------------------"
        ((counter++))
    fi
done < <(ls -tr p*.zip 2>/dev/null)

echo "✨ Operation completed successfully! All classes are organized and ready."