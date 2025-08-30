find . -name '*.m4a' -print0 | while read -d '' -r file; do
  ffmpeg -i "$file" -n -acodec libmp3lame -ab 192k "${file%.m4a}.mp3" < /dev/null
done
