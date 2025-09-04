#!/bin/bash
set -euo pipefail

# go to repo root
cd /Users/bastian/viskis-for-video-retrieval

for dir in grids/*/; do
  echo "Processing $dir"
  
  # stage only this subfolder
  git add "$dir"
  
  # commit only if there are staged changes
  if git diff --cached --quiet; then
    echo "No changes in $dir"
  else
    git commit -m "higher resolution grid ($dir)"
    git push
  fi
done

