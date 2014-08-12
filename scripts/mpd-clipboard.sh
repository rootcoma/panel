# bin/sh
if [ "$(pgrep -cx mopidy)" -eq 0 ]; then
  exit
fi

fifo=$1

clipboard=$(xsel -b)

# Check for soundcloud on clipboard
selection=$(expr "$clipboard" : '\(https\?://soundcloud.com/[^ ]*/[^  ]*\)')
if [ -n "$selection" ]; then 
  echo "sc:$selection" | mpc add
  if [ "$?" -eq 0 ]; then
    echo "XAdded song" > "$fifo"
  else
    echo "XError adding song" > "$fifo"
  fi
  sleep 2
  echo "X" > "$fifo"
  exit
fi

# Check for youtube on clipboard
selection=$(expr "$clipboard" : '\(https\?://\(www\.\)\?youtube.com/watch?v=[^ ]*\)')
if [ -n "$selection" ]; then
  echo "yt:$selection" | mpc add
  if [ "$?" -eq 0 ]; then
    echo "XAdded song" > "$fifo"
  else
    echo "XError adding song" > "$fifo"
  fi
  sleep 2
  echo "X" > "$fifo"
  exit
fi

echo "XError adding song" > "$fifo"
sleep 2
echo "X" > "$fifo"
exit
