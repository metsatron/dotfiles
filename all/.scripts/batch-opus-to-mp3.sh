find . -name '*.opus' -print0 | while read -d '' -r file; do
  ffmpeg -i "$file" -n -acodec libmp3lame -ab 192k "${file%.opus}.mp3" < /dev/null
done
