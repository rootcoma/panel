#! /bin/sh
fifo=$1

clipboard=$(xsel -b)

# Check for soundcloud on clipboard
selection=$(expr "$clipboard" : '\(https\?://soundcloud.com/[^ \w]*/[^ \w]*\)')
if [ -n "$selection" ]; then 
  $(echo "sc:$selection" | mpc add)
  echo "XAdded song" > "$fifo"
  sleep 2
  echo "X" > "fifo"
  exit
fi

# Check for youtube on clipboard
selection=$(expr "$clipboard" : '\(https\?://\(www\.\)\?youtube.com/watch?v=[^ \w]*\)')
if [ -n "$selection" ]; then
  $(echo "yt:$selection" | mpc add)
  echo "XAdded song" > "$fifo"
  sleep 2
  echo "X" > "$fifo"
  exit
fi

echo "XError adding song" > "$fifo"
sleep 2
echo "X" > "$fifo"
exit
