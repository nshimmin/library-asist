: 1789848735:0;exit
: 1789849029:0;cat << 'EOF' >> ~/.bashrc\
if [ -n "$GIT_SSH_KEY" ]; then\
  eval "$(ssh-agent -s)" > /dev/null\
  echo "$GIT_SSH_KEY" | tr -d '\r' | ssh-add - > /dev/null 2>&1\
fi\
EOF
: 1789849034:0;ls
: 1789849042:0;cd library-asist
: 1789849043:0;ls
: 1789849168:0;source ~/.bashrc
: 1789849297:0;git commit -m "first edition upload"
